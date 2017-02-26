pdf-full:
	python resumeGenerator.py pdf --outline outlines/everything.json --template latex

pdf-example1:
	python resumeGenerator.py pdf --outline outlines/example1.json --template latex

pdf-example2:
	python resumeGenerator.py pdf --outline outlines/example2.json --template latex

html:
	python resumeGenerator.py html --outline outlines/example2.json --template materialSite

html-old:
	python resumeGenerator.py html --outline outlines/example2.json --template oldSite