# Działdowo Waste Pickup AI

Home Assistant custom integration for annual waste pickup schedules used in Gmina Działdowo, Poland.

The integration scans one schedule image with OpenAI, lets the user verify and correct the interpreted table, then creates local calendar and sensor entities plus reminders for all waste categories except ash (`Popiol` / `Popiół`).
