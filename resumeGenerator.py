from jinja2 import Template
from jinja2 import Environment, FileSystemLoader
import json
import sys
import os
import os.path
import subprocess

from datetime import datetime
import dateutil.parser

import click

from BeautifulSoup import BeautifulSoup as bs

jsonResume = "resume.json"
outline = "outline"

title = "Curriculum Vitae"
shortTitle = "CV"
templateDirBase = "templates"
outputDirBase = "output"

latexFileName = "cv.tex"
htmlFileName = "index.html"

fullName = ""
position = ""
uname = ""

latexBuildSystem = "xelatex"

def latexSanitizer(value):
	cleanedValue = value
	cleanedValue = cleanedValue.replace("$", "\\$")
	cleanedValue = cleanedValue.replace("~", "$\sim$")
	cleanedValue = cleanedValue.replace(" -- ", " - ")
	cleanedValue = cleanedValue.replace("&", "\&")

	return cleanedValue

def htmlSanitizer(value):
	cleanedValue = value
	cleanedValue = cleanedValue.replace("``", "\"")
	cleanedValue = cleanedValue.replace("''", "\"")
	
	return cleanedValue

def getPdfName():
	return uname + "-" + shortTitle + ".pdf"

def buildLatex(outputdir, outfileName):
	curPath = os.getcwd()
	os.chdir(outputdir)

	try:
		tmpFName = outfileName + ".tmp"
		with open(tmpFName, "w+") as f:
			res = subprocess.call(["latexindent", tmpFName], stdout=f)

		if res == 0:
			os.rename(tmpFName, outfileName)
		else:
			print "LatexIndent failed. Skipping"
	except OSError:
		print "LatexIndent not found. Skipping"


	res = subprocess.call([latexBuildSystem, outfileName])
	if res == 0:
		res = subprocess.call([latexBuildSystem, outfileName])

	os.chdir(curPath)

	pdf = outputdir + "/" + outfileName
	pdf = pdf.replace(".tex", ".pdf")
	cmd = ["cp", pdf, getPdfName()]
	subprocess.call(cmd)

def buildHTML(outputdir, outfileName):
	pass

def loadJSON(fname):
	with open(fname) as f:
		data = json.load(f)

	return data

def writeFile(fname, data):
	with open(fname, 'w+') as f:
		if isinstance(data, unicode):
			f.write(data.encode("utf8"))
		else:
			f.write(data)

def htmlPrettify(html):
	soup = bs(html)

	return soup.prettify()

def latexPrettify(latex):
	return latex

def genInfo(resume, j2Env, sanitizer):
	infoTemplate = j2Env.get_template("info.template")
	
	info = {}
	for i in resume["info"]:
		info[i] = sanitizer(resume["info"][i])

	if "site" in resume["info"]:
		info["siteURL"] = resume["info"]["site"]
		info["siteName"] = sanitizer(resume["info"]["site"])

	return infoTemplate.render(info=info)

def bold(generated, targetText, j2Env):
	boldTemplate = j2Env.get_template("bold.template")
	return generated.replace(targetText, boldTemplate.render(text=targetText))

def insertLinks(generated, j2Env):
	linkInfo = loadJSON("links.json")
	linkTemplate = j2Env.get_template("url.template")

	for l in linkInfo:
		text = l["text"]
		link = l["link"]
		generated = generated.replace(text, linkTemplate.render(link=link, text=text))

	return generated


def genSections(resume, j2Env, sanitizer, sectionsList):
	generated = []

	for section in sectionsList:
		title = section[0]
		templateName = section[1]

		content = [resume[title][item] for item in resume[title]]
		if "date" in content[0]:
			content.sort(key=lambda x: parseDate(x["date"]), reverse=True)

		template = j2Env.get_template(templateName)

		for item in content:
			if isinstance(item, list):
				for i in range(len(item)):
					item[i] = sanitizer(item[i])
			elif isinstance(item, dict):
				for key in item:
					if key == "links":
						for i in range(len(item[key])):
							item[key][i]["text"] = sanitizer(item[key][i]["text"])
					elif isinstance(item[key], dict):
						for i in range(len(item[key])):
							item[key][i] = sanitizer(item[key][i])
					elif isinstance(item[key], basestring):
						item[key] = sanitizer(item[key])

		genSection = template.render(title=title, content=content)
		genSection = bold(genSection, fullName, j2Env)
		
		generated.append({"title": title, "content": genSection})

	return generated

def genResume(resume, j2Env, sanitizer, sectionsList):
	generated = j2Env.get_template("resume.template")
	info = genInfo(resume, j2Env, sanitizer)

	sections = genSections(resume, j2Env, sanitizer, sectionsList)

	return generated.render(info=info, sections=sections)

def applyTemplate(genType, resume, sectionsList, templateName, shouldInsertLinks):
	global uname, fullName

	templateDir = os.path.join(templateDirBase, templateName)
	outputDir = os.path.join(outputDirBase, templateName)

	j2Env = Environment(loader=FileSystemLoader(templateDir))

	fullName = resume["info"]["firstName"] + " " + resume["info"]["lastName"];
	uname = resume["info"]["firstName"][0] + resume["info"]["lastName"];
	position = resume["info"]["position"]

	j2Env.globals['fullName'] = fullName
	j2Env.globals['position'] = position
	j2Env.globals['pdfName'] = getPdfName()
	
	if genType == "latex":
		sanitizer = latexSanitizer
		outfileName = latexFileName
		build = buildLatex
		prettifyer = latexPrettify
	elif "html" in genType:
		sanitizer = htmlSanitizer
		outfileName = htmlFileName
		build = buildHTML
		prettifyer = htmlPrettify
	else:
		return

	generated = genResume(resume, j2Env, sanitizer, sectionsList)

	if shouldInsertLinks:
		generated = insertLinks(generated, j2Env)

	generated = prettifyer(generated)

	outfile = os.path.join(outputDir, outfileName)
	writeFile(outfile, generated)

	build(outputDir, outfileName)

def parseDate(dateString):
	if "present" in dateString.lower():
		return datetime.now()

	if "-" in dateString:
		endDate = dateString.split("-")[1]
		return dateutil.parser.parse(endDate)

	return dateutil.parser.parse(dateString) 

def applyOutline(outline, resume):
	filteredResume = {}

	for section in outline:
		sectionTitle = section["title"]	
		sectionItems = section["include"]

		if sectionItems != "*" and len(sectionItems) == 0:
			print """Invalid include for section %s. Must be "*" or list""" % (sectionTitle)
			exit()

		if sectionItems == "*":
			filteredResume[sectionTitle] = resume[section["key"]]
		else:
			filteredResume[sectionTitle] = {}

			for item in sectionItems:
				filteredResume[sectionTitle][item] = resume[section["key"]][item]

	return filteredResume

def main(genType, outline, resume, template, insertLinks):
	outline = loadJSON(outline)
	sectionsOrder = outline["order"]
	sectionsContent = outline["content"]

	resume = loadJSON(resume)

	filteredResume = applyOutline(sectionsContent, resume)

	sectionsList = []
	for section in sectionsOrder:
		for content in sectionsContent:
			if content["key"] == section:
				sectionsList.append((content["title"], content["template"]))
				break

	applyTemplate(genType, filteredResume, sectionsList, template, insertLinks)

@click.group()
def generate():
	pass

@generate.command()
@click.option('--outline', default="htmlOutline.json", help='Outline file to use when generating html')
@click.option('--resume', default="resume.json", help='Resume file')
@click.option('--template', default="material", help='Template File to use')
@click.option('--links', default=True, help='Insert links', is_flag=True)
def html(outline, resume, template, links):
	main("html", outline, resume, template, links)

@generate.command()
@click.option('--outline', default="pdfOutline.json", help='Outline file to use when generating pdf')
@click.option('--resume', default="resume.json", help='Resume file')
@click.option('--template', default="latex", help='Template File to use')
@click.option('--links', default=False, help='Insert links', is_flag=True)
def pdf(outline, resume, template, links):
	main("latex", outline, resume, template, links)
	

cli = click.CommandCollection(sources=[generate])

if __name__ == '__main__':
	cli()