# services/booking_service.py
"""Booking service for MagicLine API integration."""

from typing import Any, Optional

import requests

from config import (
	MAGICLINE_API_KEY,
	MAGICLINE_BASE_URL,
	MAGICLINE_BOOKABLE_ID_TRIAL_OFFER,
	MAGICLINE_TRIAL_OFFER_CONFIG_ID,
)
from constants import BotMessages


class BookingService:
	"""Handles appointment booking through MagicLine API."""

	def __init__(self):
		self.base_url = MAGICLINE_BASE_URL
		self.api_key = MAGICLINE_API_KEY
		self.bookable_id = MAGICLINE_BOOKABLE_ID_TRIAL_OFFER
		self.trial_offer_config_id = MAGICLINE_TRIAL_OFFER_CONFIG_ID
		self.headers = {
			"X-API-KEY": self.api_key,
			"Content-Type": "application/json",
		}

	def validate_slot(
		self, customer_id: int, start_datetime: str, duration_minutes: int = 30
	) -> dict[str, Any]:
		"""
		Validate if appointment slot is available.

		Args:
			customer_id: MagicLine customer ID
			start_datetime: Start time in ISO format
			duration_minutes: Appointment duration (default 30 min for Probetraining)

		Returns:
			Validation response dictionary
		"""
		end_datetime = self._calculate_end_time(start_datetime, duration_minutes)

		payload = {
			"customerId": customer_id,
			"bookableAppointmentId": self.bookable_id,
			"startDateTime": start_datetime,
			"endDateTime": end_datetime,
		}

		url = f"{self.base_url}/appointments/bookable/validate"
		print(f"🔍 VALIDATE REQUEST:")
		print(f"   URL: {url}")
		print(f"   Payload: {payload}")

		try:
			response = requests.post(
				url,
				json=payload,
				headers=self.headers,
				timeout=10,
			)
			print(f"   Status: {response.status_code}")
			print(f"   Response: {response.text}")
			return response.json()
		except requests.RequestException as e:
			print(f"   ❌ Error: {e}")
			return {"error": str(e), "validationStatus": "ERROR"}

	def book_appointment(
		self, customer_id: int, start_datetime: str, duration_minutes: int = 30
	) -> dict[str, Any]:
		"""
		Book an appointment slot.

		Args:
			customer_id: MagicLine customer ID
			start_datetime: Start time in ISO format
			duration_minutes: Appointment duration (default 30 min for Probetraining)

		Returns:
			Booking response dictionary with bookingId or error
		"""
		end_datetime = self._calculate_end_time(start_datetime, duration_minutes)

		payload = {
			"customerId": customer_id,
			"bookableAppointmentId": self.bookable_id,
			"startDateTime": start_datetime,
			"endDateTime": end_datetime,
		}

		try:
			response = requests.post(
				f"{self.base_url}/appointments/booking/book",
				json=payload,
				headers=self.headers,
				timeout=10,
			)

			if response.status_code == 200:
				return {"success": True, **response.json()}
			else:
				return {"success": False, "error": response.text}

		except requests.RequestException as e:
			return {"success": False, "error": str(e)}

	def try_book(
		self,
		customer_id: int,
		start_datetime: str,
		duration_minutes: int = 30,
	) -> tuple[bool, str, Optional[str]]:
		"""
		Validate and book appointment in one call.

		Args:
			customer_id: MagicLine customer ID
			start_datetime: Start time in ISO format
			duration_minutes: Appointment duration

		Returns:
			Tuple of (success, message, booking_id)
		"""
		# First validate
		validation = self.validate_slot(customer_id, start_datetime, duration_minutes)

		if validation.get("validationStatus") != "AVAILABLE":
			return False, BotMessages.BOOKING_SLOT_UNAVAILABLE, None

		# Then book
		booking = self.book_appointment(customer_id, start_datetime, duration_minutes)

		if booking.get("success"):
			booking_id = booking.get("bookingId")
			return True, BotMessages.BOOKING_SUCCESS, booking_id
		else:
			return False, BotMessages.BOOKING_GENERIC_ERROR, None

	# ==================== SLOT AVAILABILITY METHODS ====================

	def get_available_slots(
		self, date: str, duration_minutes: int = 30
	) -> dict[str, Any]:
		"""
		Get available slots for trial offers on a specific date.

		Uses the trial-offers bookable appointments slots endpoint to fetch available slots.

		IMPORTANT: The correct endpoint path is:
		/v1/trial-offers/bookable-trial-offers/appointments/bookable/{bookableAppointmentId}/slots
		NOT: /v1/trial-offers/appointments/{id}/slots (this returns 404!)

		Args:
			date: Date in YYYY-MM-DD format
			duration_minutes: Appointment duration (default 30 min for Probetraining)

		Returns:
			Response dictionary with:
			- success: bool
			- slots: list of available slot dictionaries (each with startDateTime, endDateTime)
			- error: error message if failed
		"""
		# FIXED: Correct endpoint path for trial-offers slots
		url = f"{self.base_url}/trial-offers/bookable-trial-offers/appointments/bookable/{self.bookable_id}/slots"
		params = {
			"date": date,
			"duration": duration_minutes,
		}

		print(f"🔍 GET AVAILABLE SLOTS REQUEST:")
		print(f"   URL: {url}")
		print(f"   Params: {params}")

		try:
			response = requests.get(
				url,
				params=params,
				headers=self.headers,
				timeout=10,
			)
			print(f"   Status: {response.status_code}")
			print(f"   Response: {response.text[:500] if response.text else 'empty'}")

			if response.status_code == 200:
				data = response.json()
				# Handle different response formats from API
				# API might return {"slots": [...]} or directly [...]
				if isinstance(data, list):
					slots = data
				elif isinstance(data, dict):
					slots = data.get("slots", data.get("items", []))
				else:
					slots = []

				return {"success": True, "slots": slots}
			else:
				return {
					"success": False,
					"slots": [],
					"error": response.text,
					"status_code": response.status_code,
				}
		except requests.RequestException as e:
			print(f"   ❌ Error: {e}")
			return {
				"success": False,
				"slots": [],
				"error": str(e),
				"is_network_error": True,
			}

	def check_slot_availability(
		self, start_datetime: str, duration_minutes: int = 30
	) -> dict[str, Any]:
		"""
		Check if a specific slot is available for booking.

		This is a pre-check BEFORE creating a lead to avoid creating leads
		for slots that are already booked.

		Args:
			start_datetime: Desired start time in ISO format (YYYY-MM-DDTHH:MM:SS+TZ)
			duration_minutes: Appointment duration

		Returns:
			Dictionary with:
			- available: bool - True if slot is available
			- alternatives: list[str] - Alternative time slots if not available
			- error: str - Error message if API call failed
			- api_error: bool - True if there was an API error (should fallback)
		"""
		# Extract date from ISO datetime
		date = self._extract_date_from_datetime(start_datetime)
		if not date:
			return {
				"available": False,
				"alternatives": [],
				"error": "Invalid datetime format",
				"api_error": True,
			}

		# Fetch available slots for the day
		slots_response = self.get_available_slots(date, duration_minutes)

		if not slots_response.get("success"):
			# API error - return api_error=True to signal fallback
			return {
				"available": False,
				"alternatives": [],
				"error": slots_response.get("error", "Unknown error"),
				"api_error": True,
			}

		slots = slots_response.get("slots", [])

		if not slots:
			# No slots available for the entire day
			return {
				"available": False,
				"alternatives": [],
				"error": "No slots available on this day",
				"api_error": False,
			}

		# Check if requested slot is in the list
		is_available = self._is_slot_in_list(start_datetime, slots)

		if is_available:
			return {
				"available": True,
				"alternatives": [],
				"error": None,
				"api_error": False,
			}

		# Slot not available - find alternatives
		alternatives = self._get_alternative_slots(start_datetime, slots, max_alternatives=3)

		return {
			"available": False,
			"alternatives": alternatives,
			"error": None,
			"api_error": False,
		}

	def _extract_date_from_datetime(self, iso_datetime: str) -> Optional[str]:
		"""
		Extract date (YYYY-MM-DD) from ISO datetime string.

		Args:
			iso_datetime: ISO format datetime (e.g., 2026-01-15T14:00:00+01:00)

		Returns:
			Date string in YYYY-MM-DD format, or None if parsing fails
		"""
		if not iso_datetime:
			return None

		try:
			# ISO datetime starts with YYYY-MM-DD
			return iso_datetime[:10]
		except (TypeError, IndexError):
			return None

	def _is_slot_in_list(self, target_datetime: str, slots: list[dict]) -> bool:
		"""
		Check if target datetime matches any slot in the list.

		Args:
			target_datetime: ISO datetime to find
			slots: List of slot dictionaries from API

		Returns:
			True if slot is found in list
		"""
		if not target_datetime or not slots:
			return False

		# Extract time portion for comparison (HH:MM)
		target_time = self._extract_time_from_datetime(target_datetime)
		if not target_time:
			return False

		for slot in slots:
			# API might use different field names
			slot_start = slot.get("startDateTime") or slot.get("start") or slot.get("startTime")
			if not slot_start:
				continue

			slot_time = self._extract_time_from_datetime(slot_start)
			if slot_time == target_time:
				return True

		return False

	def _extract_time_from_datetime(self, iso_datetime: str) -> Optional[str]:
		"""
		Extract time (HH:MM) from ISO datetime string.

		Args:
			iso_datetime: ISO format datetime (e.g., 2026-01-15T14:00:00+01:00)

		Returns:
			Time string in HH:MM format, or None if parsing fails
		"""
		if not iso_datetime:
			return None

		try:
			# ISO datetime has T separator, time starts after T
			if "T" in iso_datetime:
				time_part = iso_datetime.split("T")[1]
				return time_part[:5]  # HH:MM
			return None
		except (TypeError, IndexError):
			return None

	def _get_alternative_slots(
		self, target_datetime: str, slots: list[dict], max_alternatives: int = 3
	) -> list[str]:
		"""
		Find alternative slots closest to the target time.

		Args:
			target_datetime: Original requested datetime
			slots: Available slots from API
			max_alternatives: Maximum number of alternatives to return

		Returns:
			List of alternative times in HH:MM format, sorted by closeness to target
		"""
		if not slots:
			return []

		target_time = self._extract_time_from_datetime(target_datetime)
		if not target_time:
			# Can't compare, just return first available slots
			alternatives = []
			for slot in slots[:max_alternatives]:
				slot_start = slot.get("startDateTime") or slot.get("start") or slot.get("startTime")
				if slot_start:
					time_str = self._extract_time_from_datetime(slot_start)
					if time_str:
						alternatives.append(time_str)
			return alternatives

		# Parse target time to minutes for comparison
		target_minutes = self._time_to_minutes(target_time)
		if target_minutes is None:
			return []

		# Calculate distance from target for each slot
		slot_distances = []
		for slot in slots:
			slot_start = slot.get("startDateTime") or slot.get("start") or slot.get("startTime")
			if not slot_start:
				continue

			slot_time = self._extract_time_from_datetime(slot_start)
			if not slot_time:
				continue

			slot_minutes = self._time_to_minutes(slot_time)
			if slot_minutes is None:
				continue

			distance = abs(slot_minutes - target_minutes)
			slot_distances.append((slot_time, distance))

		# Sort by distance and return top N
		slot_distances.sort(key=lambda x: x[1])
		return [time for time, _ in slot_distances[:max_alternatives]]

	def _time_to_minutes(self, time_str: str) -> Optional[int]:
		"""
		Convert HH:MM time string to minutes since midnight.

		Args:
			time_str: Time in HH:MM format

		Returns:
			Minutes since midnight, or None if parsing fails
		"""
		if not time_str or ":" not in time_str:
			return None

		try:
			hours, minutes = time_str.split(":")[:2]
			return int(hours) * 60 + int(minutes)
		except (ValueError, TypeError):
			return None

	# ==================== TRIAL OFFER METHODS (für nicht-registrierte Leads) ====================

	def validate_lead(
		self, first_name: str, last_name: str, email: str
	) -> dict[str, Any]:
		"""
		Validate lead data before creating.

		Args:
			first_name: Lead's first name
			last_name: Lead's last name
			email: Lead's email address

		Returns:
			Validation response dictionary with 'success', 'status_code', and optionally 'error'
		"""
		payload = {
			"leadCustomerData": {
				"firstname": first_name,
				"lastname": last_name,
				"email": email,
				"address": {
					"street": None,
					"houseNumber": None,
					"zipCode": None,
					"city": None,
					}
			},
			"trialOfferConfigId": self.trial_offer_config_id,
		}

		url = f"{self.base_url}/trial-offers/lead/validate"
		print(f"🔍 VALIDATE LEAD REQUEST:")
		print(f"   URL: {url}")
		print(f"   Payload: {payload}")

		try:
			response = requests.post(
				url,
				json=payload,
				headers=self.headers,
				timeout=10,
			)
			print(f"   Status: {response.status_code}")
			print(f"   Response: {response.text}")

			if response.status_code == 200:
				return {"success": True, "status_code": 200, **response.json()}
			else:
				return {
					"success": False,
					"status_code": response.status_code,
					"error": response.text,
				}
		except requests.RequestException as e:
			print(f"   ❌ Error: {e}")
			return {"success": False, "status_code": 0, "error": str(e), "is_network_error": True}

	def create_lead(
		self, first_name: str, last_name: str, email: str
	) -> dict[str, Any]:
		"""
		Create a new lead in MagicLine.

		Args:
			first_name: Lead's first name
			last_name: Lead's last name
			email: Lead's email address

		Returns:
			Response dictionary with leadCustomerId, status_code, or error
		"""
		payload = {
			"leadCustomerData": {
				"firstname": first_name,
				"lastname": last_name,
				"email": email,
				"address": {
					"street": None,
					"houseNumber": None,
					"zipCode": None,
					"city": None,
					}
			},
			"trialOfferConfigId": self.trial_offer_config_id,
		}

		url = f"{self.base_url}/trial-offers/lead/create"
		print(f"📝 CREATE LEAD REQUEST:")
		print(f"   URL: {url}")
		print(f"   Payload: {payload}")

		try:
			response = requests.post(
				url,
				json=payload,
				headers=self.headers,
				timeout=10,
			)
			print(f"   Status: {response.status_code}")
			print(f"   Response: {response.text}")

			if response.status_code == 200:
				return {"success": True, "status_code": 200, **response.json()}
			else:
				return {
					"success": False,
					"status_code": response.status_code,
					"error": response.text,
				}
		except requests.RequestException as e:
			print(f"   ❌ Error: {e}")
			return {"success": False, "status_code": 0, "error": str(e), "is_network_error": True}

	def validate_appointment_for_lead(
		self,
		lead_customer_id: int,
		start_datetime: str,
		duration_minutes: int = 30,
	) -> dict[str, Any]:
		"""
		Validate appointment slot for a lead customer (trial offer).

		IMPORTANT: Uses the trial-offer specific validation endpoint:
		/v1/trial-offers/appointments/booking/validate
		NOT: /v1/appointments/bookable/validate (this doesn't check for conflicts!)

		Args:
			lead_customer_id: Lead customer ID from create_lead
			start_datetime: Start time in ISO format
			duration_minutes: Appointment duration

		Returns:
			Validation response dictionary
		"""
		end_datetime = self._calculate_end_time(start_datetime, duration_minutes)

		payload = {
			"customerId": lead_customer_id,
			"bookableAppointmentId": self.bookable_id,
			"startDateTime": start_datetime,
			"endDateTime": end_datetime,
		}

		# FIXED: Use trial-offer specific validation endpoint
		url = f"{self.base_url}/trial-offers/appointments/booking/validate"
		print(f"🔍 VALIDATE APPOINTMENT FOR LEAD REQUEST:")
		print(f"   URL: {url}")
		print(f"   Payload: {payload}")

		try:
			response = requests.post(
				url,
				json=payload,
				headers=self.headers,
				timeout=10,
			)
			print(f"   Status: {response.status_code}")
			print(f"   Response: {response.text}")

			if response.status_code == 200:
				return {"success": True, **response.json()}
			else:
				return {"success": False, "error": response.text}
		except requests.RequestException as e:
			print(f"   ❌ Error: {e}")
			return {"success": False, "error": str(e)}

	def book_appointment_for_lead(
		self,
		lead_customer_id: int,
		start_datetime: str,
		duration_minutes: int = 30,
	) -> dict[str, Any]:
		"""
		Book an appointment for a lead customer (trial offer).

		IMPORTANT: Uses the trial-offer specific booking endpoint:
		/v1/trial-offers/appointments/booking/book
		NOT: /v1/appointments/booking/book (allows double-booking!)

		Args:
			lead_customer_id: Lead customer ID from create_lead
			start_datetime: Start time in ISO format
			duration_minutes: Appointment duration

		Returns:
			Booking response dictionary with bookingId or error
		"""
		end_datetime = self._calculate_end_time(start_datetime, duration_minutes)

		payload = {
			"customerId": lead_customer_id,
			"bookableAppointmentId": self.bookable_id,
			"startDateTime": start_datetime,
			"endDateTime": end_datetime,
		}

		# FIXED: Use trial-offer specific booking endpoint
		url = f"{self.base_url}/trial-offers/appointments/booking/book"
		print(f"📅 BOOK APPOINTMENT FOR LEAD REQUEST:")
		print(f"   URL: {url}")
		print(f"   Payload: {payload}")

		try:
			response = requests.post(
				url,
				json=payload,
				headers=self.headers,
				timeout=10,
			)
			print(f"   Status: {response.status_code}")
			print(f"   Response: {response.text}")

			if response.status_code == 200:
				return {"success": True, **response.json()}
			else:
				return {"success": False, "error": response.text}
		except requests.RequestException as e:
			print(f"   ❌ Error: {e}")
			return {"success": False, "error": str(e)}

	def try_book_trial_offer(
		self,
		first_name: str,
		last_name: str,
		email: str,
		start_datetime: str,
		duration_minutes: int = 30,
	) -> tuple[bool, str, Optional[str]]:
		"""
		Complete trial offer booking flow for unregistered leads.

		Steps:
		0. PRE-CHECK: Check slot availability BEFORE creating lead (prevents lead garbage)
		1. Validate lead data
		2. Create lead in MagicLine → get leadCustomerId
		3. Validate booking slot with leadCustomerId
		4. Book the appointment with leadCustomerId

		If pre-check fails with alternatives, returns early without creating lead.
		If pre-check has API error, falls back to old flow (create lead first).

		Args:
			first_name: Lead's first name
			last_name: Lead's last name
			email: Lead's email address
			start_datetime: Start time in ISO format
			duration_minutes: Appointment duration

		Returns:
			Tuple of (success, message, booking_id)
		"""
		print(f"🎯 TRIAL OFFER BOOKING FLOW START")
		print(f"   Name: {first_name} {last_name}")
		print(f"   Email: {email}")
		print(f"   DateTime: {start_datetime}")

		# Step 0: PRE-CHECK slot availability BEFORE creating lead
		# This prevents creating leads for slots that are already booked
		slot_check = self.check_slot_availability(start_datetime, duration_minutes)

		if not slot_check.get("api_error"):
			# API call succeeded - we can trust the result
			if not slot_check.get("available"):
				alternatives = slot_check.get("alternatives", [])
				if alternatives:
					print(f"   ❌ Slot nicht verfügbar - Alternativen: {alternatives}")
					return False, BotMessages.slot_unavailable_with_alternatives(alternatives), None
				else:
					print(f"   ❌ Slot nicht verfügbar - keine Alternativen")
					return False, BotMessages.BOOKING_SLOT_UNAVAILABLE, None
			print(f"   ✅ Slot verfügbar (Pre-Check)")
		else:
			# API error during pre-check - continue with old flow as fallback
			print(f"   ⚠️ Pre-Check fehlgeschlagen (API-Fehler) - fahre mit altem Flow fort")

		# Step 1: Validate lead
		lead_validation = self.validate_lead(first_name, last_name, email)
		if not lead_validation.get("success"):
			error = lead_validation.get("error", "Unbekannter Fehler")
			status_code = lead_validation.get("status_code", 0)
			print(f"   ❌ Lead-Validierung fehlgeschlagen (Status {status_code}): {error}")

			# Return appropriate error message based on status code
			if lead_validation.get("is_network_error"):
				return False, BotMessages.BOOKING_NETWORK_ERROR, None
			elif status_code >= 500:
				# Server error (500, 502, 503, etc.) - not user's fault
				return False, BotMessages.BOOKING_SERVER_ERROR, None
			else:
				# Client error (400, 401, 403, 404, etc.) - likely data issue
				return False, BotMessages.BOOKING_VALIDATION_FAILED, None

		# Step 2: Create lead → get leadCustomerId
		lead_creation = self.create_lead(first_name, last_name, email)
		if not lead_creation.get("success"):
			error = lead_creation.get("error", "Unbekannter Fehler")
			status_code = lead_creation.get("status_code", 0)
			print(f"   ❌ Lead-Erstellung fehlgeschlagen (Status {status_code}): {error}")

			# Return appropriate error message based on status code
			if lead_creation.get("is_network_error"):
				return False, BotMessages.BOOKING_NETWORK_ERROR, None
			elif status_code >= 500:
				return False, BotMessages.BOOKING_SERVER_ERROR, None
			else:
				return False, BotMessages.BOOKING_LEAD_CREATION_FAILED, None

		lead_customer_id = lead_creation.get("leadCustomerId")
		if not lead_customer_id:
			print(f"   ❌ Keine leadCustomerId erhalten")
			return False, BotMessages.BOOKING_LEAD_CREATION_FAILED, None

		print(f"   ✅ Lead erstellt mit ID: {lead_customer_id}")

		# Step 3: Validate booking slot with leadCustomerId
		booking_validation = self.validate_appointment_for_lead(
			lead_customer_id, start_datetime, duration_minutes
		)
		if not booking_validation.get("success"):
			error = booking_validation.get("error", "Unbekannter Fehler")
			print(f"   ❌ Slot-Validierung fehlgeschlagen: {error}")
			return False, BotMessages.BOOKING_SLOT_UNAVAILABLE, None

		# Check validation status
		validation_status = booking_validation.get("validationStatus")
		if validation_status != "AVAILABLE":
			print(f"   ❌ Slot nicht verfügbar: {validation_status}")
			return False, BotMessages.BOOKING_SLOT_UNAVAILABLE, None

		# Step 4: Book appointment with leadCustomerId
		booking = self.book_appointment_for_lead(
			lead_customer_id, start_datetime, duration_minutes
		)
		if booking.get("success"):
			booking_id = booking.get("bookingId")
			print(f"   ✅ Buchung erfolgreich! Booking-ID: {booking_id}")
			return True, BotMessages.BOOKING_SUCCESS, booking_id
		else:
			error = booking.get("error", "Unbekannter Fehler")
			print(f"   ❌ Buchung fehlgeschlagen: {error}")
			return False, BotMessages.BOOKING_GENERIC_ERROR, None

	def _calculate_end_time(self, start_datetime: str, duration_minutes: int) -> str:
		"""
		Calculate end time from start time and duration.

		Args:
			start_datetime: Start time in ISO format (e.g., 2025-12-26T18:00:00+01:00)
			duration_minutes: Duration in minutes

		Returns:
			End time string in ISO format
		"""
		from datetime import datetime, timedelta
		import re

		# Extract the datetime part and timezone
		# Format: 2025-12-26T18:00:00+01:00
		match = re.match(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})([+-]\d{2}:\d{2})?', start_datetime)
		if not match:
			# Fallback: just return start + duration as simple string
			return start_datetime

		dt_str = match.group(1)
		tz_str = match.group(2) or "+01:00"

		# Parse datetime
		dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")

		# Add duration
		end_dt = dt + timedelta(minutes=duration_minutes)

		# Format back
		return f"{end_dt.strftime('%Y-%m-%dT%H:%M:%S')}{tz_str}"
