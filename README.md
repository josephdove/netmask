<a name="readme-top"></a>


[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]



<!-- PROJECT LOGO -->
<br />
<div align="center">
<h3 align="center">Netmask</h3>

  <p align="center">
    A TCP/UDP self-hostable network tunneling solution that supports IPv4 and IPv6
    <br />
    <a href="https://github.com/josephdove/netmask/issues/new?labels=bug&template=bug-report---.md">Report Bug</a>
    ·
    <a href="https://github.com/josephdove/netmask/issues/new?labels=enhancement&template=feature-request---.md">Request Feature</a>
  </p>
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>

## About The Project

Netmask is a robust tool designed to facilitate secure and seamless network tunneling, similar to Ngrok, but with the added advantage of supporting TCP/UDP protocols and being entirely self-hostable. This makes it an excellent choice for users who need more control over their tunneling solutions, especially in environments where they require flexibility and security.

## Getting Started

This is an example of how you may give instructions on setting up your project locally.
To get a local copy up and running follow these simple example steps.

### Prerequisites

Netmask is built with semplicity in mind, it only requires a base installation of python 3.6 or above.

### Installation

Method 1 (PIP):
1. Install netmask from PIP
   ```sh
   pip install netmask
   ```

Method 2 (GIT):

1. Clone the repo
   ```sh
   git clone https://github.com/josephdove/netmask
   ```
2. Build and install
   ```sh
   python3 setup.py install
   ```

## Usage

Netmask is subdivided into two main components: the client (netmaskc) and the server (netmasks). The client and the server communicate on an encrypted stream with the key being based on the communication key, meaning that the client will only be able to communicate to the server while having the same key as the server. The default communication key is 0.

<br>

Netmask Server (netmasks):
The server component, netmasks, is responsible for listening to incoming connections from clients and managing the tunnels.

Key Arguments for netmasks:

--port \<port>: Specifies the port on which the server will listen for incoming connections. (DEFAULT: 1024)<br>
--key \<key>: Sets the communication key that the server and client will use. (DEFAULT: 0)<br>
--verbose: Prints debug information.<br>
listener4: This is the IPv4 address to bind to, if none, specify "-". (EXAMPLE: 0.0.0.0)<br>
listener6: This is the IPv6 address to bind to, if none, specify "-". (EXAMPLE: ::)<br>

<br><br>

Netmask Client (netmaskc):
The client component, netmaskc, is used to establish a connection to the netmasks server and create tunnels. It forwards traffic from the local machine to the server, which then handles the routing to the intended destination.

Key Arguments for netmaskc:

--key \<key>: Sets the communication key that the server and client will use. (DEFAULT: 0)<br>
--verbose: Prints debug information (REQUIRES --nogui).<br>
--nogui: Removes the GUI interface.<br>
protocol: Can either be "tcp" or "udp", this specifies the protocol used while binding.<br>
port: This is the port on the current host that we want to forward. (EXAMPLE: 443)<br>
ipVersion: This is the IP version we want to use, must be either 4 or 6.<br>
server: This is the server we want to connect to (EXAMPLE: 127.0.0.1:1024)<br>

## Roadmap

- [x] UDP Support
- [ ] Automatic TLS
- [ ] Kill connections from client (From GUI)
- [ ] Control panel for server (HTTP)


See the [open issues](https://github.com/josephdove/netmask/issues) for a full list of proposed features (and known issues).

## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE.txt` for more information.

## Contact

Your Name - josephdove@proton.me

Project Link: [https://github.com/josephdove/netmask](https://github.com/josephdove/netmask)


[contributors-shield]: https://img.shields.io/github/contributors/josephdove/netmask.svg?style=for-the-badge
[contributors-url]: https://github.com/josephdove/netmask/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/josephdove/netmask.svg?style=for-the-badge
[forks-url]: https://github.com/josephdove/netmask/network/members
[stars-shield]: https://img.shields.io/github/stars/josephdove/netmask.svg?style=for-the-badge
[stars-url]: https://github.com/josephdove/netmask/stargazers
[issues-shield]: https://img.shields.io/github/issues/josephdove/netmask.svg?style=for-the-badge
[issues-url]: https://github.com/josephdove/netmask/issues
[license-shield]: https://img.shields.io/github/license/josephdove/netmask.svg?style=for-the-badge
[license-url]: https://github.com/josephdove/netmask/blob/master/LICENSE.txt