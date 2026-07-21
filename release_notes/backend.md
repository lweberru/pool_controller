Stabilisiert Chemie-Empfehlungen mit historienbasierter Median-Logik statt Einzelmessungen
Optimiert die dynamische Zieltemperatur für lokale Pool-Außentemperatur in Sonne: offizielles Wetter bleibt Kontext, neutralisiert den lokalen Sensor aber nicht mehr
Erweitert `tools/ha_api_read.py` um `pool --focus dynamic-target` sowie exakte Entity-, Friendly-Name- und numerische Range-Filter für `states`
Verbessert den Config-/Options-Flow für direkte BlueRiiot-Nutzung, Sensor-Erreichbarkeit und Desinfektionsmittel-Auswahl
Verschiebt Heizleistungswerte in den Bereich Schalter & Leistung und entfernt das Pflichtfeld für klassische Wasserqualitätssensoren bei BlueRiiot-Setups
Entfernt alte Alkalinität-plus/minus-Entities und redundante PV-Band-Sensoren
Blockiert Alkalinitäts-Aktionen während/kurz nach Baden, Chloren, Boost, Pause und bei Messsprung-Cooldown
Persistiert Chemie-Historie und Cooldown über Home-Assistant-Neustarts via entry options
Erweitert Config- und Options-Flow um einfache Chemistry-Tuning-Parameter (TDS, Alkalinität, Cooldown, Lookback, Min-Samples)
Aktualisiert Entitäten/Service-Dokumentation und ergänzt klare Hinweise: Schätzung ist kein Laborwert
Ergänzt/überarbeitet Übersetzungen (de/en/es/fr) für neue Chemistry-Flow-Felder
Verschärft Wasserqualitäts-Alarmierung mit kombiniertem pH-/ORP-Wasser-kippt-Risiko, Status-/Grund-Sensoren und Entwarnungsbenachrichtigungen
