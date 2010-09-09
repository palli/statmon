TSM Status Monitor - Reporting tool for TSM
===========================================

TSM Status Monitor
------------------
Version: 1.2 (2009-04-15)
Release type: Open source Version


What is TSM Status Monitor?
---------------------------



System Requirements
-------------------
  * Web server that can run mod_python (apache)
  * mysql 
  * mod_python
  * python-rrdtool
  * mysql-python
  * working dsmadmc client configured to connect to TSM
  * python-xml
  * dsmadmc binary installed and configured to connect to TSM


INSTALLATION
==========================================
When you begin installation you should make sure apache and mysql are already running and you have already downloaded a statmon tarball (statmon-1.2.tar.gz is assumed in this guide). This guide assumes you install statmon in /var/www/statmon/

What you need to do is the following:


1) Create a mysql database for statmon and create a user with access
------------------------------------------
  # mysqladmin -u root create statmon
  # mysql -u root -e "GRANT ALL ON statmon.* TO 'statmon'@'localhost' IDENTIFIED BY 'statmon'"
------------------------------------------
If MySQL denies you access, try adding "-p" right after "-u root" in
each command 


2) Unpack statmon on your webserver
------------------------------------------
  # cd /var/www/
  # tar -zxvf statmon-1.2.tar.gz
  # mv statmon-1.2/ statmon/
------------------------------------------


3) Initialize statmon database
------------------------------------------
  # cd /var/www/statmon/
  # mysql -u root statmon < statmon-1.2.sql
------------------------------------------


4) Make sure mod_python is loaded in Apache
If you installed mod_python rpm on a Redhat based system this should
be configured for you out of the box, usually the following line should
be in /etc/httpd/conf.d/python.conf:
-------------------------------------------
LoadModule python_module modules/mod_python.so
-------------------------------------------


5) Make sure apache is configured to use .htaccess
You need to configure apache to use /var/www/statmon/.htaccess. The easiest
way to accomplish this is to do the following:
-------------------------------------------
  # cp /var/www/statmon/statmon-apache.conf /etc/httpd/conf.d
  # /etc/init.d/httpd reload
-------------------------------------------
Please note that if you install TSM Status Monitor to a path other
then /var/www/statmon you need to change both the command above and the content of the statmon-apache.conf

Restart apache and see if everything looks ok in http://localhost/statmon/


6) Configuring TSM Status Monitor
Edit /var/www/statmon/statmonConfig.xml. You need to at least configure username/password to access your TSM and username/password to access you MySQL local database.

TSM Status Monitor uses dsmadmc internally to talk to TSM so your dsm.sys and dsm.opt must be configured correctly. Make sure to match tsm servername in statmonConfig.xml to a valid servername in dsm.sys.



7) Start collecting data from your TSM Server:
-------------------------------------------
  # cd /var/www/statmon/statmon
  # python collector.py
-------------------------------------------

If collection finished successfully, you should be able to view your results 
at http://localhost/statmon/

Remember that some graphs will not appear with any data until data has been collected
at least a couble of times.

If everything is working as expected, you can schedule data collection to run daily:
-------------------------------------------
  # echo "python /var/www/statmon/statmon/collect.py" > /etc/cron.daily/statmon.cron
  # chmod +x /etc/cron.daily/statmon.cron
-------------------------------------------

8) If you encounter any problems!
Dont hesitate to contact support@minor.is for help. Please try to be as specific as you can
and make sure to include in your email the following:
  * Your version of Linux and architecture
  * Your version of python and mod_python
  * Any logs or errors that you recieve

