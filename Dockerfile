FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends iverilog yosys libcairo2 && rm -rf /var/lib/apt/lists/*
WORKDIR /project
COPY . .
RUN python -m pip install --no-cache-dir -e .
CMD ["python", "scripts/run_project.py", "--profile", "offline"]
