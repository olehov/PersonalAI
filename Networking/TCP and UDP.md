# TCP and UDP
=====================

TCP (Transmission Control Protocol) and UDP (User Datagram Protocol) are two fundamental protocols in computer networking. Both are transport-layer protocols, but they have distinct characteristics that set them apart.

**Connection Model**
-------------------

* **TCP**: Establishes a connection between sender and receiver before transmitting data. This connection is maintained throughout the duration of the communication session.
* **UDP**: Does not establish a connection prior to transmission. It sends datagrams without connection setup and relies on IP for addressing and routing.

**Reliability**
--------------

* **TCP**: Ensures reliable data transfer by ensuring that packets are delivered in the correct order and retransmitting lost or corrupted packets.
* **UDP**: Provides no guarantees about packet delivery or order. It is best-effort, meaning it may not deliver all packets or guarantee their integrity.

**Ordering**
------------

* **TCP**: Guarantees the order of received packets to maintain data integrity.
* **UDP**: Does not guarantee packet ordering; packets can arrive out of order or be lost.

**Overhead**
------------

* **TCP**: Incurs additional overhead due to connection establishment, packet header sizes, and retransmission mechanisms.
* **UDP**: Has lower overhead since it does not establish a connection or perform retransmissions.

**Latency Tradeoffs**
-------------------

* **TCP**: To ensure reliability, TCP introduces latency through the three-way handshake (connection establishment) and potential retransmissions. This can lead to increased delay in data transmission.
* **UDP**: With no connection establishment or retransmission mechanisms, UDP typically has lower latency than TCP.

**Common Protocol Examples**
---------------------------

* **TCP**: SSH, HTTPS, SMTP, database connections
* **UDP**: [[DNS]], DHCP, VoIP, online gaming, streaming

Open Questions:
----------------

When should an application prefer reliability and ordering over lower latency and lower overhead?

## Related Notes

- [[DNS]]
- [[HTTP]]
- [[Sockets]]
