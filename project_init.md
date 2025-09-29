Analyze the following instructions on making an application and WITHOUT MAKING ANY CHANGES YET tell me if it is enough and it is clear what needs to be done and you have everything you need to orchestrate creation of the app.

Goal:
Application where through a GUI I will be able to via chat talk to a model that will have RAG access to ElasticSearch database to store details about what I already know, how well I understand it, what I do not know, what I still need to learn about a given topic.

Initial phase: application (or model) will first ask what I want to learn for example I reply:
'I want to learn how to be an Elasticsearch Relevance Engine (ESRE) Engineer'
then the model will ask me to describe what I already know and I answer for example:
'I am a 15 years worth of experience PHP and Javascript developer and have beginner knowledge abut Elasticsearch'
then the model needs to search the internet for resources - courses, documentation and work out a training program that will get me from zero to hero.
Once that is done and stored in database model will start PHASE 1 - CALIBRATION - asking questions that narrow down exactly what I know because I just do not know what is relevant. For example 'do you know what is an index', 'do you know what is a vector' - and I will reply explaining what I know. This should continue until the starting point of my learning is clear and everything needed for me to learn to be 'Elasticsearch Relevance Engine (ESRE) Engineer' is mapped.
Then the model will trigger TUNING PROGRAM where it will generate a list of dependencies with concepts that I need to learn first that unlock further concepts until reaching the end.
Now PHASE 2 starts - LEARNING - model will give me theory and links to resources to read and understand and also excercises to perform and I will have to return correct answers to proceed.
Exercise validation: the system auto-grade via analisys of user answers and determining if they signify that the user has grasped the whole context. Create something experimental, perhaps a config file with instruction how model should treat the answers. Keyword checks, user self-assesment migh be useful as weighs to determine if user understand the concept.
If I will need to make excercises say on kibana or just plain via elasticsearch API then model also needs to give me a primer on how to set it up - preferably as a VSCODE dev container that has everything I need.
This phase carries on until user types '/no more' where the model makes a summary of what I learned and stores it for later.

The key is that the model should not overload it's context window but per each prompt enrich itself via stored details in RAG database and use semantic search. Meaning it should be sort of stateless when it comes to it's context window and rely instead on the Elasticsearch infused context. Proper model for storing vectors into the database must also be therefore picked.

The model should be able to access internet obviously - any publicly available API and website scraping (curl?), suggest anything else you might need. If you need an account (token) then ask me to set it up, but pick only free sources.
No changes can be made to the host machine, only in this project and in containers related to this project. If you need to chnage something else you have to ask first.

I have no idea about embeddings, pick best option. I would lean towards anything that is able to perform approximate k-Nearest neighbour search, dense_vector. Only english language is needed.

No security is required but any credentials must be put into gitignored .env with .env.dist having defaults only. This is a public repository that anyone can download from github.

Tech stack:
- has UI based on Javascript SPA - best based on Vuex
- backend in PHP and Laravel 12
- you may use python client as intermediary between php and elasticsearch if php client is lacking
- Elasticsearch database - newest stable version. At least 8 but I think image for 9.1.4 is available.
- RAG application
- proper model(s). Models must run locally, no paid API's. So the RX 6600 is the limit.

MUST run comfortably on my PC, pick best model that fits:
- CPU AMD Ryzen 5 7600
- Motherboard MSI MAG B650 TOMAHAWK (NUVOTON NCT6687D-R Controller Chip)
- GPU ASRock Challenger D Radeon RX 6600
- Fast System Storage SAMSUNG 990 Pro 1TB SSD PCI Express 4.0 x4 NVMe
- Slow Data Storage SAMSUNG 990 Pro 1TB SSD
- RAM CORSAIR Vengeance DDR5 32GB (2x16GB) 6000MHz CL36

Include a makefile for ease to running commands both by user and AI:
- make build - downloads and builds images
- make up - brings up containers
- make test - run tests that check if the stack works - you should use it for testing if everything is properly orchestrated
- other commands

The project should run via docker compose - meaning everything lives in containers and no host configuration is needed other than maybe exposing in 'hosts' to connect to the GUI

Dev container primer - only provision the application as defined here. Any further LABs for excercises should instead be a separate recipe (just a docker-compose.yml with makefile or few zipped starting files) that the user can copy paste to a separate directory and create LAB there. The user will then copy-paste results from LAB environment to this application chat window.

Create a readme.md outlining how to use.

Divide the creation of this application into steps and document in rollout.md - these should be small and conscise steps that are easy for you to understand. You will then proceed and implement step by step - at completion of each step mark the step as completed and specify briefly what has been done - in case the creation got interrupted - so it is easy for you to pick up and als serve as a reference point later should there be a need to expand the project.

Create AGENTS.md file where you add important details to prevent you from hallucinating and loosing context and also leave instructions for yourself how to handle rollout.md as specified above.

Testing expectations:
- validate containers are up and configured
- validate api endpoints with wiremock stubs so that database is not used
- perhaps spin up a temporary ES cluster and test all flows - ingestion and retrieval with the use of model
- UI e2e are desirable but also should base on stubs and not call the backend directly