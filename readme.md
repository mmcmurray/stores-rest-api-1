# MitziCom OpenShift CI/CD Pipeline POC

## Goals

Demonstrate setting up fully CI/CD application pipeline inside of an existing OpenShift Container Platform (OCP).
This POC is to include the three main topics outlined below:

1. [CI/CD Infrastructure setup](#section1) (leveraging templates in OCP)
	1. [Jenkins](https://www.jenkins.io) - Continous Integration Tool
	2. [SonarQube](https://www.sonarqube.org) - Static Code Analysis
	3. [Gogs](https://gogs.io/) - Source Control Management
	4. [Nexus]() - Artifactory / Container Registry
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
	export __OCP_CLUSTER='https://master.na39.openshift.opentlc.com/' # Ensure you replace this with your cluster's URL.
	export __OCP_PREFIX='mmm'                                         # Ensure you set this to something like your deployment GUID or Initials
	```
2. Login to OCP with `oc` utility (installation instructions can be found [here](https://docs.openshift.com/container-platform/3.4/cli_reference/get_started_cli.html) )
	```
	oc login ${__OCP_CLUSTER}
	```
3. Open a browser and login to the Web Console for your OCP cluster using the URL defined above.
   We will use this for watching and observing our builds and deployments.


---

## Section 1: <a name="section1">CI/CD Infrastructure Setup</a>

To support our CI/CD pipelines, we need to have the appropriate infrastructure resources in place.  As such, we will create a new `${__OCP_PREFIX}-devops` project, and deploy the following services in it.

* Jenkins
* SonarQube
* Gogs
* Nexus

1. Create the `${__OCP_PREFIX}-devops` project:
```
oc new-project ${__OCP_PREFIX}-devops --display-name "DevOps Resources"

```
2. Create and configure persistent Jenkins service:
```
oc new-app jenkins-persistent -p ENABLE_OAUTH=true -p MEMORY_LIMIT=2.0Gi -n ${__OCP_PREFIX}-devops -l name='jenkins' 
```
	1. Login to jenkins UI and install a few plugins that we will require:
	**Note:** The following will get the URL for your Jenkins Web UI.
	```
	 oc get route | grep jenkins | gawk '{print $2}' | sed -e 's/\(.*\)/https:\/\/\1/g'
	```
3. Setup SonarQube service for static code analysis in the pipeline:
	1. Setup the PostgresDB service.
	```
	oc new-app postgresql-persistent -p POSTGRESQL_USER=sonar -p POSTGRESQL_PASSWORD=sonar -p POSTGRESQL_DATABASE=sonar -p VOLUME_CAPACITY=4Gi -l name='postgresql'
	```
	2. Setup the SonarQube App / Service.
	```
	oc new-app --docker-image=wkulhanek/sonarqube:6.7.3 -e SONARQUBE_JDBC_USERNAME=sonar -e SONARQUBE_JDBC_PASSWORD=sonar -e SONARQUBE_JDBC_URL=jdbc:postgresql://postgresql/sonar -l name=sonarqube
	oc expose svc/sonarqube
	oc set volume dc/sonarqube --add --overwrite --name=sonarqube-volume-1 --mount-path=/opt/sonarqube/data/ --type persistentVolumeClaim --claim-name=sonarqube-pvc
	oc set resources dc/sonarqube --limits=memory=3Gi,cpu=2 --requests=memory=2Gi,cpu=1
	oc patch dc sonarqube --patch='{ "spec": { "strategy": { "type": "Recreate" }}}'
	oc set probe dc/sonarqube --liveness --failure-threshold 3 --initial-delay-seconds 40 -- echo ok
	oc set probe dc/sonarqube --readiness --failure-threshold 3 --initial-delay-seconds 20 --get-url=http://:9000/about
	```
	3. **Note:** You will need to wait until SonarQube comes online before you can validate the service or use it.  As such, you can execute the following to tail the container logs and look for the
	   `SonarQube is up` string.
    ```
    oc logs -f $(oc get pods | grep sonar | grep -v deploy | grep -i running | awk '{print $1}')
    ```
4. Create and configure Gogs service for Source Control Management (SCM)
	1. We will re-use the `postgresql` service that we used for SonarQube as the backend for Gogs.  We do, however, need to create the postgres db for this.
	```
	oc exec $(oc get pods | grep postgresql | grep -v deploy | gawk '{print $1}') -- bash -c 'createdb gogs -O sonar'
	```
	2. Launch the Gogs service:
	```
	oc new-app wkulhanek/gogs:11.34 -l name=gogs
	```
	3. Configure a PVC (Persistent Volume Claim) for the Gogs service to use.

	```
	oc create -f ocp_helpers/1_4-03-gogs_pvc-yaml
	oc set volume dc/gogs --add --overwrite --name=gogs-volume-1 --mount-path=/data/ --type persistentVolumeClaim --claim-name=gogs-data
	```
	4. Create a `ConfigMap` so that we can set Gogs to talk to the `postresql` persistent database.
	```
	oc create configmap gogs --from-file=ocp_helpers/gogs/app.ini
	oc set volume dc/gogs --add --overwrite --name=config-volume -m /opt/gogs/custom/conf/ -t configmap --configmap-name=gogs
	```
	5. Expose route to Gogs server:
	```
	oc expose svc/gogs
	```
	6. Navigate to the Gogs UI (can be found via the following:)
	7. Register a new user in Gogs UI so we can create an Organization and Repo.
	8. Add this project as a remote target to the Git repo.


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
	* To demonstrate, open your browser and navigate to:
		* `OCP Cluster Console URL` --> `My Projects` --> `Stores REST API - Production`
		* Under the `Overview` section, expand the `mongodb` StatefulSet and observe it scaling to 3 pods.
	* To demonstrate the StatefulSet data replication, we will do the following:
		1. Connect to primary MongoDB node via `oc rsh`.
		```
		oc rsh $(oc get pods | grep mongodb-0 | head -1 | awk '{print $1}')
		mongo -u admin -p $MONGODB_ADMIN_PASSWORD admin
		```
		2. Insert a record into the MongoDB Cluster
		```javascript
		db.inventory.insertOne(
   			{ item: "canvas", qty: 100, tags: ["cotton"], size: { h: 28, w: 35.5, uom: "cm" } }
		)
 		```
 		3. Disconnect from the `mongo` client by issuing `ctrl+d` (or type `exit`)
 		4. Disconnect from the `pod` by issuing `ctrl+d` (or type `exit`)
 		5. We will scale down the number of replicas to 2 and verify the status of the cluster
 		```
 		oc scale statefulset mongodb --replicas=2
 		```
 		6. Connect to a secondary MongoDB cluster node via `oc rsh`
 		```
 		oc rsh $(oc get pods | grep mongodb-1 | head -1 | awk '{print $1}')
		mongo -u admin -p $MONGODB_ADMIN_PASSWORD admin
		```
		7.  Observe the state of the MongoDB cluster
			* **Note**: In the output of `rs.status()`, you should observe `3` nodes, two of which represent `"health": 1,` and one with `"health": 2,`.
		```javascript
		rs.slaveOk()
		rs.status()
		db.inventory.find( { item: "canvas" } ).pretty()
		```
		* **Note:** The final command above will prove that you can select the record from the cluster that was added to the primary cluster node earlier.
		8. Scale the statefulset back to 3 replicas
		```
		oc scale statefulset mongodb --replicas=3
		```
		9. Observe via the OCP Web Console that the `StatefulSet` is scaled fully to 3 nodes, and repeat steps `6:` and `7:` above using the `mongodb-2` pod.

---

## Section 3: <a name="section3">Deployment Pipeline(s)</a>


--- 

## Authors

* **Mike McMurray** - *Initial work* - [mmcmurray](https://github.com/mmcmurray)