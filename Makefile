.PHONY: all data marts analysis diagnostic chargeback forecast risk triage test clean
all: data marts analysis diagnostic chargeback forecast risk triage
data:
	python src/generate_data.py
marts:
	python src/run_marts.py
analysis:
	python analysis/descriptive.py
diagnostic:
	python analysis/diagnostic.py
chargeback:
	python src/chargeback.py
forecast:
	python analysis/forecast.py
risk:
	python analysis/sla_risk.py
triage:
	python src/ai_triage/triage.py
test:
	pytest -q
clean:
	rm -rf data/raw/*.csv data/processed/*.csv assets/*.png
