---
title: "The terrible 3 cent MCU"
date: 2019-08-12T21:07:54Z
lastmod: 2019-09-14T06:31:27Z
slug: the-terrible-3-cent-mcu
url: /2019/08/12/the-terrible-3-cent-mcu/
aliases:
  # - /?p=632
categories:
  - Hardware
  - Padauk
  - PFS154
summary: "Review of the sub $0.10 Microcontroller segment." 
tags:
  - 3 cent mcu
  - MCU
  - microcontroller
  - PFS154
  - PFS173
  - PMC150
showTableOfContents: true
---

Like many others, I was quite amazed to learn about a microcontroller sold for only 0.03 USD [via the EEVblog](https://www.eevblog.com/forum/blog/eevblog-1132-the-3-cent-microcontroller!/) last year. How was this possible? Many assumed this was a fire sale of an old product. Digging a bit further, it became apparent that there is an entire market segment of ultra-low-cost microcontrollers. Almost all of them are products of rather unknown companies from China or Taiwan. This write up summarizes my findings in this rather peculiar niche.

We already learned that there is a large variety of very powerful [$1.00 microcontrollers](https://jaycarlson.net/microcontrollers), but what about the $0.10 MCU? Are they indeed all "terrible", [as suggested elsewhere](https://hackaday.com/2019/04/26/making-a-three-cent-microcontroller-useful)?

## Methodology

How to define a $0.10 microcontroller? Any way you put it; it will be a somewhat arbitrary choice. I took a straightforward approach and used the price of the 100pc bracket at LCSC. Six vendors where identified that had one or multiple devices below $0.10, all from Asia. If different packages types of the same MCU were available, I picked the SOP8 version. Some manufacturers had more than one candidate, so I had to limit myself to representative devices for a final candidate list of eight.

I was not able to find any sub $0.10 MCU at the large distributors like
Digikey or Mouser. Just to state the obvious: This does not necessarily mean
that it is impossible to find sub $0.10 MCUs from western manufacturers with
the right order size. Two factors seem to come into play here: First, LCSC
seems to operate on much smaller margins than the established distributors.
Secondly, the established MCU manufacturers are not as reliant on smaller
customers and can therefore command a premium on low volume orders.

Due to lack of programming tools and evaluation boards I was only able to review most devices by datasheet, with the exception of the Padauk MCUs.

## Overview

In total, eight candidates from six different manufacturers where identified. A summary of the devices can be found in the table below.

There are some obvious commonalities: All devices are designed around an accumulator based architecture, undeniably inspired from the Microchip PIC12 series. Interestingly, with only MDT as an exception, all vendors extended and modified their designs from the original. The reason for this is probably twofold: First, they want to avoid any legal issues with Microchip and secondly, the PIC12 itself is severely limited. Some of the major shortcomings are being addressed, such as lack of interrupts, addressable space of JMP/CALL, banking of memory/IO and severe lack of periphery.

Unfortunately, none of the vendors openly share details like instruction encoding or memory algorithms. Development for all device has to commence via vendor-provided IDEs.  With exception of Holtek, all devices rely on high voltage programming interface and are not easily programming in-circuit. Only Padauk and Holtek offer devices that can be programmed more than once.

{{< figure src="3-cent-mcu-1.png" alt="Summary table of sub $0.10 microcontrollers" caption="Summary of my findings. PDF version [here](10cent-mcu-overview-1.pdf)." >}}

## Individual Findings

### Bojuxing Industrial

The BJ8P509F, priced at $0.0466, is a slightly enhanced version of the PIC12C509. The instruction set is extended from 12 bit to 13 bit. This allows for jmp instructions that can address the entire memory. In addition, interrupt capabilities and an extended HW stack were added.

An English datasheet is available and looks comprehensive enough to work with the device. Unfortunately, the vendor website and IDE documentation is only available in Chinese.

### Eastsoft Micro

Eastsoft Micro has an extensive portfolio of PIC-derived microcontrollers. They call their flavor of the architecture "HR7P RISC". It is a comprehensive accumulator based architecture with interrupt capability, 8 level stack and non-bankswitched access to memory and I/O.

There is one device in the sub $0.10 space
available, the HR7P153P45SA. Notable features are the availability of a 12 Bit
ADC, a low speed oscillator for lower power operation and the addition of two
timers with PWM capability.

Unfortunately, both website and datasheets only seem to be available in Chinese.

### Holtek

Holtek is a well-established
microcontroller vendor from Taiwan. Their entry into this category, the HT68F001,
is somewhat of an oddity: It's a rather limited device with only 512 words of
program flash and 16 bytes of RAM. The architecture is very similar to the
PIC12 and can only be clocked from an internal 32 kHz oscillator. Since each
instruction takes 4 cycles to execute, this results in only 8000 instructions
per second! It appears that this device is targeting ultra-low power
applications that have very low complexity requirements.

This MCU comes with excellent documentation. This includes their website, datasheets, application notes and IDE. It is also the only device to offer low voltage flash programming. Both of this sets Holtek somewhat apart from the rest of the field.

Given the limited functionality of their entry, however, it appears that the ultra-low-cost segment is not a priority for Holtek.

### Padauk

It is very clear that the sub $0.10 MCU
market is Padauks home turf. They have dozens of products in this price range,
with a wide variety of features and package types.

All devices are based on Padauks MCU architecture, which is significantly extended over that of the PIC12: It uses separated I/O and SRAM memory regions and allows to address the full range without banking. In contrast to all other devices, the stack is memory mapped. Most instructions execute in a single cycle.

 One interesting and very unique aspect is that Padauks architecture is geared toward synchronous multithreading, allowing to execute more than one program in parallel on the same MCU core using a time-slicing scheme. They call this concept "Field Programmable Processor Array" (FPPA). A similar concept is used in the [XCore Architecture](https://en.wikipedia.org/wiki/XCore_Architecture) by XMOS. One useful application of multithreading in small MCUs is to create virtual periphery, e.g. UART, I^2C, that is operated in parallel with the main program.

I picked three representative products in
an SOP8 package: The PMS150C, the PFS154 and the PFS173. All of these only have
single FPPA unit and therefore do not support multithreading.

The PMS150C is their lowest cost offer at $0.033, the original "3 cent MCU". This device comes with 1 kiloword of one-time programmable memory and 64 bytes of RAM. The periphery is notably extended over many of the competing parts, offering a 16 Bit timer, an 8 Bit timer with PWM, LF oscillator and an analog comparator with 4 Bit reference voltage DAC that can be used to implement simple ADC functionality. All of this is sufficient to implement simple sensing and controlling functions.

The PFS154 comes at almost twice the cost. However, in contrast to the PMS150 it offers 2kW flash memory and can be programmed multiple times, which is much more convenient for actual development. The periphery has been extended with 3x11 bit PWM units, which look well suited to control RGB LEDs.

Finally, the PFS173 is an incremental
improvement over the PFS154, adding an 8-bit ADC and extending flash to 3
kilowords and RAM to 256 bytes.

Padauk provides an IDE supporting
development in Assembler and a somewhat cryptic dialect of C ("Mini-C"). They
provide excellent datasheets in both English and Chinese as well as a bilingual
website. Programming of the devices is accomplished by a 5 or 6 wire high
voltage protocol, which makes in-circuit programming challenging.

###### Open source toolchain

Following the discussion on EEVblog, a small community has formed around the Padauk MCU with the goal of creating an open source toolchain for the device. Most of the activities are covered in [this thread](https://www.eevblog.com/forum/blog/eevblog-1144-padauk-programmer-reverse-engineering/).

As of today (August 2019), reverse engineering the[instruction encoding](https://free-pdk.github.io/) was completed, the [programming protocol was documented](https://github.com/cpldcpu/SimPad/tree/master/Protocol), an [open hardware programmer was developed](https://github.com/free-pdk/easy-pdk-programmer-hardware) and support for several flavors of the PDK architecture was integrated into [SDCC](https://sourceforge.net/projects/sdcc/). Development for all of the previously mentioned Padauk MCUs is now possible using a fully open toolchain.

### Puolop

Puolop is a Shenzhen based Chinese provider
of microcontrollers and various mixed signal circuits. They seem to offer a
wide range of relabeled Padauk MCUs, specifically the older OTP version.

For example, the Puolop PTB150CSE appears to be identical to the Padauk PMS150C. Their pricing is slightly lower than the original ($0.0315 vs $0.334). It is not clear what the relation between Puolop and Padauk is, but it appears that Padauk is acting as a supplier to Puolop.

The company website and all documentation
are only available in Chinese.

There does not seem to be any specific reason to consider Puolop MCUs over Padauks, other than saving fractions of cents on pricing.

### Yspring Tech / MDT

Yspring Tech is a China based company that offers a wide range of devices that are functionally compatible to counterparts from Microchip. It appears that most of the product portfolio originated at [MDT tech](http://www.mdtmcu.com/), which is a Taiwanese company and may have either been acquired or is on cooperation with Yspring. [Microchip has taken issue](http://ww1.microchip.com/downloads/pr_archive/en/en013345.pdf) with their business model in the past.

Ysprings addition to this review is the MDT10P509 which sells for $0.0795. This device seems to be an exact clone of the PIC12C509. While this could be useful as a low-cost replacement of the original product, it is clearly inferior to the other products in this category from a functional standpoint.

The MDT10P509 offers 1KW of OTP memory, 41 bytes of RAM and only a single 8 Bit timer as periphery. Like the PIC12C509 it offers no interrupts, only a 2 level HW stack and takes 4 clocks per instruction

## Conclusions

Are these microcontrollers indeed "terrible"? That surely is a question of perspective. They address a specific category of low-cost, high volume, non-serviceable products with limited functionality. You need to wait for the push of a button and then let an LED flash exactly five times? You need to control a battery-operated night light? The sub $0.10 MCU is your friend to reduce BOM and shorten development time.

A caveat is that development for most of these devices is quite inconvenient due to limited availability of flash variants and lack of in-service programming. Debugging is usually only offered via in circuit emulators.

If you like working with low-end microcontrollers, the Padauk line-up is, without any doubt, the best choice. They offer the most powerful architecture, a wide range of devices including flash variants, good documentation, and are the only line-up with an open source toolchain.
