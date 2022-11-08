# Instructions for deploying a TESK local instance

###### More information about TESK can be found on the official [github page](https://github.com/elixir-cloud-aai/TESK). You can find the official deployment instructions [here](https://github.com/elixir-cloud-aai/TESK/blob/master/documentation/deployment_new.md) and the helm chart used [here](https://github.com/elixir-cloud-aai/TESK/tree/master/charts/tesk).
###### The instructions are tested on Ubuntu 20.04 LTS with minikube, docker driver and Nodeport to expose the service.
###### If you have a Mac (especially M1 Mac) your best option for deploying TESK is to use an Ubuntu VM (see instructions for UTM)

## Requirements
- A Kubernetes cluster version 1.9 or later (like minikube). 
- A default storage class with RWO permissions (if you use minikube you don't have to change the default storage class).
- A storage backend (ftp or s3).

## VM set up for Mac
If you are using Mac you can easily create an Ubuntu VM with [UTM](https://mac.getutm.app). To set up the VM you can follow the instructions described on the following [video](https://www.youtube.com/watch?v=MVLbb1aMk24).

## FTP server setup
Instructions are based on [TESK documentation](https://github.com/elixir-cloud-aai/TESK/blob/master/documentation/local_ftp.md)
- Create a new user. The password should not contain numbers. We will use that user to connect to the ftp server
```
sudo adduser tesk
```
- Install vsftpd
```
sudo apt install vsftpd
```
- Change the configuration file and make it writable. The vsftpd.conf file can be found on  ``` /etc/vsftpd.conf ```. Open the vsftpd configuration file as root ```sudo pico /etc/vsftpd.conf``` and add the following line:
```
write_enable=YES
```
- Add TLS certificate to vsftpd to configure TLS with vsftpd
```
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/ssl/private/vsftpd.pem -out /etc/ssl/private/vsftpd.pem
```
- Once again open the configuration file as root and specify the location of the certificate, key files and other configurations to the end of the file. Add the following lines:
```
rsa_cert_file=/etc/ssl/private/vsftpd.pem
rsa_private_key_file=/etc/ssl/private/vsftpd.pem
ssl_enable=YES
allow_anon_ssl=NO
force_local_data_ssl=NO
force_local_logins_ssl=NO
ssl_tlsv1=YES
ssl_sslv2=NO
ssl_sslv3=NO
require_ssl_reuse=NO
ssl_ciphers=HIGH

```
- Restart vsftpd to enable the changes
```
sudo /etc/init.d/vsftpd restart
```
- Run ```systemctl status vsftpd.service``` to check if the server is running. If the status is failed then start the server manually
```
sudo vsftpd
```
- You can also test your set up by trying to connect to the server with ```ftp ftp_id``` and enter the credentials of your user. You can find the ip of the ftp server with ```ip addr```.

# Minikube set up
You can download the suitable version of minikube for your laptop [here](https://minikube.sigs.k8s.io/docs/start/). You should also download a driver such as docker. You can set up docker on ubuntu by following the instructions [here](https://docs.docker.com/engine/install/ubuntu/). By default only the root can use the Unix socket that the Docker deamon uses, thus to be able to run docker without ```sudo``` you should also follow the [post-installation steps](https://docs.docker.com/engine/install/linux-postinstall/). Then you should be able to use minikube.
- Create a new minikube cluster
```
minikube start --driver=docker
```
# Deploy TESK
- Clone the [repository](https://github.com/elixir-cloud-aai/TESK) with the deployment files
```
git clone https://github.com/elixir-cloud-aai/TESK.git
```
- The next step is to create a new ```secrets.yaml``` file on ```TESK/charts/tesk``` to add the ftp credentials. You should add the following lines:
```
ftp:
  username: <username>
  password: <password>

```
- Add the ftp address of your ftp server on ```values.yaml``` file on ```ftp.hostip```
- You should also expose the TESK service, so it can be accessible outside the minikube cluster. There are different options to do that (Nodeport, LoadBalancer, etc). To expose the service using Nodeport you should modify the ```values.yaml```. Add or uncomment the following lines:
```
service.type: NodePort
service.node_port: 31567
``` 
- To deploy the service we will use helm. To install helm you can follow the instructions described [here](https://helm.sh/docs/intro/install/). Once helm is installed we are ready to deploy TESK. TESK can be deployed either on the default namespace or to a new, dedicated namespace. To deploy TESK on the default namespace, execute the following:
```
helm upgrade --install tesk-release . -f secrets.yaml -f values.yaml
```
- To check the deployment
```
helm list
```
You should be able to see something like this:
```
NAME        	NAMESPACE	REVISION	UPDATED                                	STATUS  	CHART     	APP VERSION
tesk-release	default  	1       	2022-11-07 15:24:28.996673492 +0000 UTC	deployed	tesk-0.1.0	dev  
```
- You can also check the logs of the pod with the following command:
```
kubectl logs -f <pod_name>
```
- You can open the Swagger UI of TESK directly to your browser with ```minikube service tesk-api```, or get the external IP of your cluster with ```minikube ip``` and the service is accessible on ```http://external_IP_of_a_node:31567/v1/tasks```.

