"""
Gemini AI Service for RAG pipeline
"""
import json
import re
import logging
from datetime import datetime
from typing import Optional, List

from app.config.settings import settings
from app.models.query import QueryResult, VALID_REPORT_TYPES, VALID_TIMEFRAMES

logger = logging.getLogger(__name__)


class GeminiService:
    """Service for interacting with Google Gemini AI."""

    def __init__(self):
        self._model = None
        self._api_key = settings.GEMINI_API_KEY

        if self._api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self._api_key)
                self._model = genai.GenerativeModel('gemini-2.0-flash')
                logger.info("GeminiService initialized successfully with gemini-2.0-flash")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self._model = None
        else:
            logger.warning("GeminiService: No API key provided, AI features disabled")

    @property
    def is_available(self) -> bool:
        return self._model is not None

    def _extract_json(self, text: str) -> Optional[dict]:
        """Extract JSON from Gemini response, handling markdown code blocks."""
        # Try to find JSON in code blocks first
        code_block_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if code_block_match:
            text = code_block_match.group(1).strip()

        # Try to find JSON object directly
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # Last resort: try the whole text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"Failed to extract JSON from Gemini response: {text[:200]}")
            return None

    async def parse_query_intent(
        self,
        user_query: str,
        capster_list: List[str],
        branch_list: List[str]
    ) -> Optional[QueryResult]:
        """
        PARSE step: Send user query to Gemini to extract structured intent.
        Returns QueryResult or None if parsing fails.
        """
        if not self.is_available:
            return None

        prompt = f"""Kamu adalah parser query untuk aplikasi barbershop. Analisis pertanyaan user dan ekstrak informasi terstruktur.

Pertanyaan user: "{user_query}"

Data yang tersedia:
- Capster (tukang cukur): {json.dumps(capster_list)}
- Cabang: {json.dumps(branch_list)}

Kembalikan HANYA JSON (tanpa teks lain) dengan format:
{{
    "report_type": "<salah satu dari: {', '.join(VALID_REPORT_TYPES)}>",
    "metrics": ["revenue", "transaction_count"],
    "timeframe": "<salah satu dari: {', '.join(VALID_TIMEFRAMES)}> atau null",
    "specific_date": "YYYY-MM-DD atau null (tanggal spesifik / awal range)",
    "date_end": "YYYY-MM-DD atau null (akhir range, jika user menyebut rentang tanggal)",
    "specific_dates": ["YYYY-MM-DD", ...] atau [] (beberapa tanggal terpisah, non-range),
    "specific_month": <nomor bulan 1-12 atau null (jika user menyebut bulan spesifik tanpa tanggal)>,
    "specific_year": <tahun 4 digit atau null>,
    "capsters": ["nama capster yang disebut"] atau [],
    "branches": ["nama cabang yang disebut"] atau [],
    "sort_by": "revenue atau transaction_count atau null",
    "limit": <angka, default 10>
}}

Aturan:
- Jika user menyebut beberapa tanggal terpisah (misal "15 jan, 18 jan, 2 feb 2026") → set specific_dates sebagai array, specific_date/date_end null
- Jika user menyebut rentang tanggal (misal "15 jan sampai 17 jan 2026") → set specific_date (awal) dan date_end (akhir), specific_dates kosong
- Jika user menyebut satu tanggal spesifik (misal "tanggal 1 januari 2026", "1 feb") → set specific_date, date_end/specific_dates null/kosong
- Jika user menyebut bulan spesifik tanpa tanggal (misal "januari 2026", "bulan maret") → set specific_month dan specific_year, timeframe null
- Jika user pakai istilah relatif (hari ini, kemarin, minggu ini, bulan ini, bulan lalu) → set timeframe, specific_date dan specific_month null
- Jika tidak ada timeframe disebut → timeframe: "bulan ini"
- Jika user bertanya tentang pendapatan/omzet/revenue → report_type: "revenue", metrics: ["revenue"]
- Jika user bertanya siapa capster terbaik/ranking → report_type: "capster_ranking"
- Jika user bertanya perbandingan cabang → report_type: "branch_comparison"
- Jika user bertanya layanan terpopuler → report_type: "service_popularity"
- Jika user bertanya laba/rugi/profit → report_type: "profit"
- Jika user bertanya ringkasan/laporan harian → report_type: "daily_summary"
- Jika user bertanya ringkasan/laporan mingguan → report_type: "weekly_summary"
- Jika user bertanya ringkasan/laporan bulanan → report_type: "monthly_summary"
- Jika tidak jelas → report_type: "general", metrics: ["revenue", "transaction_count"]
- Cocokkan nama capster dan cabang dengan fuzzy matching dari daftar yang tersedia
- Untuk cabang, terima alias: "denailla"/"mojosari" = "Cabang Denailla", "sumput" = "Cabang Sumput"
"""

        try:
            response = await self._generate_content(prompt)
            if not response:
                return None

            data = self._extract_json(response)
            if not data:
                return None

            # Build QueryResult from parsed JSON
            result = QueryResult(original_query=user_query)

            report_type = data.get('report_type', 'general')
            if report_type in VALID_REPORT_TYPES:
                result.report_type = report_type
            else:
                result.report_type = 'general'

            result.metrics = data.get('metrics', ['revenue', 'transaction_count'])

            # Handle multiple discrete dates first
            specific_dates_list = data.get('specific_dates', [])
            if specific_dates_list and len(specific_dates_list) >= 2:
                parsed_dates = []
                for ds in specific_dates_list:
                    try:
                        parsed_dates.append(datetime.strptime(ds, '%Y-%m-%d'))
                    except (ValueError, TypeError):
                        pass
                if len(parsed_dates) >= 2:
                    result.specific_dates = sorted(parsed_dates)
                    dates_display = ', '.join(d.strftime('%d %B %Y') for d in result.specific_dates)
                    result.timeframe_str = f"tanggal {dates_display}"

            # Handle specific date (and optional date range)
            specific_date_str = data.get('specific_date')
            date_end_str = data.get('date_end')
            if specific_date_str and not result.specific_dates:
                try:
                    result.specific_date = datetime.strptime(specific_date_str, '%Y-%m-%d')
                    if date_end_str:
                        result.date_end = datetime.strptime(date_end_str, '%Y-%m-%d')
                        result.timeframe_str = (
                            f"{result.specific_date.strftime('%d %B %Y')} - "
                            f"{result.date_end.strftime('%d %B %Y')}"
                        )
                    else:
                        result.timeframe_str = f"tanggal {result.specific_date.strftime('%d %B %Y')}"
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid date from Gemini: {specific_date_str} / {date_end_str}: {e}")

            # Handle specific month
            specific_month = data.get('specific_month')
            specific_year = data.get('specific_year')
            if specific_month and not result.specific_date and not result.specific_dates:
                result.specific_month = int(specific_month)
                result.specific_year = int(specific_year) if specific_year else datetime.now().year
                result.timeframe_str = f"bulan {result.specific_month}/{result.specific_year}"

            # Handle relative timeframe (only if no specific date/month/dates)
            if not result.specific_date and not result.specific_month and not result.specific_dates:
                timeframe = data.get('timeframe')
                if timeframe and timeframe in VALID_TIMEFRAMES:
                    result.timeframe_str = timeframe
                elif timeframe:
                    for valid_tf in VALID_TIMEFRAMES:
                        if valid_tf in timeframe or timeframe in valid_tf:
                            result.timeframe_str = valid_tf
                            break
                    if not result.timeframe_str:
                        result.timeframe_str = 'bulan ini'
                else:
                    result.timeframe_str = 'bulan ini'

            result.capsters = data.get('capsters', [])
            result.branches = data.get('branches', [])
            result.sort_by = data.get('sort_by')
            result.limit = data.get('limit', 10)

            # Set metric from first metric in list for backward compatibility
            if result.metrics:
                if 'revenue' in result.metrics:
                    result.metric = 'pendapatan'
                elif 'transaction_count' in result.metrics:
                    result.metric = 'transaksi'

            logger.info(f"Gemini parsed query: {result}")
            return result

        except Exception as e:
            logger.error(f"Gemini parse_query_intent failed: {e}", exc_info=True)
            return None

    async def generate_natural_response(
        self,
        user_query: str,
        data_context: str,
        report_type: str = 'general'
    ) -> Optional[str]:
        """
        GENERATE step: Send data context + user query to Gemini for natural response.
        Returns formatted response string or None if generation fails.
        """
        if not self.is_available:
            return None

        prompt = f"""Kamu adalah asisten barbershop yang ramah dan membantu. Jawab pertanyaan user berdasarkan data yang diberikan.

Pertanyaan user: "{user_query}"
Tipe laporan: {report_type}

Data:
{data_context}

Aturan:
- Jawab dalam bahasa Indonesia yang natural dan ramah
- Gunakan emoji yang relevan (tapi jangan berlebihan)
- Format angka uang dengan "Rp" dan separator ribuan (contoh: Rp 1.500.000)
- Jika data menunjukkan ranking, gunakan format berurut (1, 2, 3...)
- Ringkas dan to-the-point, maksimal 500 kata
- Jangan mengarang data yang tidak ada
- Jika data kosong atau tidak tersedia, sampaikan dengan sopan
- Gunakan bold (**text**) untuk angka penting
- Akhiri dengan insight singkat jika memungkinkan (tren, saran)
"""

        try:
            response = await self._generate_content(prompt)
            if response:
                return response.strip()
            return None

        except Exception as e:
            logger.error(f"Gemini generate_natural_response failed: {e}", exc_info=True)
            return None

    async def _generate_content(self, prompt: str) -> Optional[str]:
        """Internal method to call Gemini API."""
        if not self._model:
            return None

        try:
            # google-generativeai supports async via generate_content_async
            response = await self._model.generate_content_async(prompt)

            if response and response.text:
                return response.text
            return None

        except Exception as e:
            logger.error(f"Gemini API call failed: {e}", exc_info=True)
            return None
