# AWS_Flowlog_Graph
simple script that reads AWS VPC Flowlogs and generate a connection graph representing TCP traffic flow.

Discription
-------------

Data can be downloaded or read direcly from cloudwatch

Tagging and other identifing  infomation is queried directly from AWS 

By default inbound connection to ELBs are ignored, as are unlabled outbound connection
(this can be changed in settings)

To reduce clutter, Hosts in the same scaling group are consolidated,
optionaly, similar named posts are also consolidated
eg:  "rabbitmq01.domain" "rabbitmq02.domain" "rabbitmq03.domain" becomes just "rabbitmq"


Output Examples
-------------

A Directed Graph

<img src='https://raw.githubusercontent.com/evilpete/AWS_Flowlog_Graph/master/Example_Output/xvlog-dot.png' width=700 title='Directed Graph'>

As an Undirected Graph

<img src='https://raw.githubusercontent.com/evilpete/AWS_Flowlog_Graph/master/Example_Output/xvlog-fdp.png' width=700 title='Undirected Graph'>

Undirected Graph (Alt)

<img src='https://raw.githubusercontent.com/evilpete/AWS_Flowlog_Graph/master/Example_Output/xvlog-neato.png' width=600 title='Undirected Graph'>
