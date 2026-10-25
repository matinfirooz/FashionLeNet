PYTHON ?= python3
export PYTHONPATH := $(CURDIR)/src
.PHONY: install demo test rtl full-rtl verify train28 train32 figures hardware-figures synthesis package clean
install:
	$(PYTHON) -m pip install -e .
demo:
	$(PYTHON) -m fashionlenet.cli demo
test:
	$(PYTHON) -m unittest discover -s tests -v
rtl:
	$(PYTHON) scripts/run_rtl.py
full-rtl:
	$(PYTHON) scripts/run_rtl.py --full --bundle examples/trained32
verify:
	$(PYTHON) scripts/run_project.py --profile verify
train28:
	$(PYTHON) -m fashionlenet.cli train --input-size 28 --output results/trained28 --epochs 15
train32:
	$(PYTHON) -m fashionlenet.cli train --input-size 32 --output results/trained32 --epochs 12
figures:
	$(PYTHON) scripts/make_figures.py
hardware-figures:
	$(PYTHON) scripts/hardware_figures.py --package
synthesis:
	$(PYTHON) scripts/synth_yosys.py
package:
	$(PYTHON) scripts/package_release.py
clean:
	$(PYTHON) -c "import shutil; shutil.rmtree('build', ignore_errors=True)"
