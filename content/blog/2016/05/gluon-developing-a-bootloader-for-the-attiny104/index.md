---
title: "Gluon - developing a bootloader for the ATtiny104"
date: 2016-05-21T17:41:40Z
lastmod: 2016-05-21T18:01:15Z
slug: gluon-developing-a-bootloader-for-the-attiny104
draft: true
url: /2016/05/21/gluon-developing-a-bootloader-for-the-attiny104/
aliases:
  # - /?p=547
categories:
  - Microcontroller
  # - Uncategorized
summary: "Introducing the gluon bootloader work-in-progress for ATtiny104 parts, reusing Tiny Program Loader building blocks."
showTableOfContents: false
tags:
  - AVR
  # - Microcontroller > AVR
  # - Microcontroller
---

The ATtiny102 and ATtiny104 are Atmels newest addition to the AVR ATtiny family. They are a bit different to most of the other devices in that family, since they are based on the AVRTINY CPU core, which was so far only used in the ATtiny4/5/9/10/20/40. I have previously done [several](https://cpldcpu.wordpress.com/2014/03/19/%c2%b5-wire-usb-on-an-attiny-10/)[projects](https://github.com/cpldcpu/TinyTouchButton) on the ATtiny10, so I was naturally excited to see another addition to this family. Both new devices are clearly targeted at the lower end, with only 1kb of flash.

Two interesting new features compared to the ATtiny10 are self-programming capability and an integrated UART. Naturally, this asks for a serial bootloader. Since no bootloader is available for this device I set out to work to work on one.

The current state can be found at the Github repository linked below.

[**Gloun Github repository**](https://github.com/cpldcpu/Gluon)

Right now it is able to upload and execute user programs on ATtiny104 and ATtiny85, but it is far from being optimized. I stopped working in Gluon for various reasons, but may be picking it up again at some point.
