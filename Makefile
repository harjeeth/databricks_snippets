.EXPORT_ALL_VARIABLES:

PROJECT = databricks_snippets
define REQUIREMENTS_HEADER
#
# These requirements were autogenerated by pipenv
# To regenerate from the project's Pipfile, run:
#
#    make update-requirements
#

endef

clean: clean-app clean-data

clean-app:
	docker-compose down
	docker rmi -f "$(PROJECT)-app"

clean-data:
	docker volume rm -f "$(PROJECT)_data"

update-requirements:
	pipenv update
	echo "$$REQUIREMENTS_HEADER" > requirements.txt
	pipenv requirements >> requirements.txt
