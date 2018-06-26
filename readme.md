# MitziCom OpenShift CI/CD Pipeline POC

## Goals

Demonstrate setting up fully CI/CD application pipeline inside of an existing OpenShift Container Platform (OCP).
This POC is to include the three main topics outlined below:

1. [CI/CD Infrastructure setup](#section1) (leveraging templates in OCP)
	1. [Jenkins](https://www.jenkins.io) - Continous Integration Tool
	2. [SonarQube](https://www.sonarqube.org) - Static Code Analysis
	3. [Gogs](https://gogs.io/) - Source Control Management
2. [Application Project Setup in OCP](#section2), one each for:
	1. dev/test
		* build validation, code coverage, AUT and Integration testing will be handled in this project.
	2. production
		* Demonstrate replicated MongoDB environment leveraging `StatefulSets`
		* Blue/Green deployment model will be used, with the _non-prod_ environment to be used for UAT before toggling the blue/green swap.
3. [Deployment Pipeline(s)](#section3):
	1. Dev/Build
		* Triggered on SCM merge to master branch.
    	* Build Validation
    	* Code Coverage
    	* Trigger `Test` Pipeline upon successful completion.
  	2. Test
    	* Unit Tests
    	* Integration Tests
    	* Trigger `Production Deploy` Pipeline upon successful completion.
  	3. Production Deploy
    	* Blue / Green
    	* Notify at blue/green stage for UAT team to test current "non-prod" environment

---
## Sample Application:  Stores REST Api

Sample REST API for Stores and Inventories.

#### Built with:

* Python3
* Flask
* Flask-RESTful
* Flask-JWT
* Flask-SQLAlchemy

---

## Prerequisites:

1. Set your local environment vars to ensure we prefix all of our projects and applications/services.
	```
	export __OCP_CLUSTER='https://sample.cluster.domain.com' # Ensure you replace this with your cluster's URL.
	export __OCP_PREFIX='mmm'                                # Ensure you set this to something like your deployment GUID or Initials
	```
2. Login to OCP with `oc` utility (installation instructions can be found [here](https://docs.openshift.com/container-platform/3.4/cli_reference/get_started_cli.html) )
	```
	oc login ${__OCP_CLUSTER}
	```
3. Open a browser and login to the Web Console for your OCP cluster using the URL defined above.
   We will use this for watching and observing our builds and deployments.


---

## Section 1: <a name="section1">CI/CD Infrastructure Setup</a>


#### Creating Project(s)

To support our application deployments 

---

## Section 2: <a name="section2">Application Project Setup in OCP</a>

To support our application builds and deployments, we need to ensure appropriate projects exist in OpenShift.  We will create two projects, one for each `dev/test` and `production`.


1. Create `dev/test` project.
	* build validation, code coverage, AUT and Integration testing will be handled in this project.
	```
	oc new-project ${__OCP_PREFIX}-stores-dev --display-name "Stores REST API - Development"
	```
2. Create `production` project.
	* Demonstrate replicated MongoDB environment leveraging `StatefulSets`
	* Blue/Green deployment model will be used, with the _non-prod_ environment to be used for UAT before toggling the blue/green swap.
	```
	oc new-project ${__OCP_PREFIX}-stores-prod --display-name "Stores REST API - Production"
	```
3. Demonstrate Replicated MongoDB cluster leveraging `StatefulSets` in `OCP`
	* For the purpose of demonstration, we are going to leverage the `production` project for the following steps.  As such, let's ensure we are bound to that project.
	```
	oc project ${__OCP_PREFIX}-stores-prod
	```
	* We are going to leverage pre-generated resource files to create the MongoDB services accordingly.
	* First we need to setup the internal services that the cluster will communicate with.
	```
	oc create -f ocp_helpers/2_3-00_mongodb-internal-service.yaml
	```
	* Next we will create the external service for applications to communicate with.
	```
	oc create -f ocp_helpers/2_3-01_mongodb-service.yaml
	```
	* Next we will create the `StatefulSet` for teh MongoDB Cluster
	```
	oc create -f ocp_helpers/2_3-02_mongodb-statefulset.yaml
	```


---

## Section 3: <a name="section3">Deployment Pipeline(s)</a>


--- 

## Authors

* **Mike McMurray** - *Initial work* - [mmcmurray](https://github.com/mmcmurray)