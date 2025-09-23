---
title: "Analysis of the Gen2 Addressable RGB LED Protocol"
date: 2024-01-21T01:34:46Z
lastmod: 2024-01-21T01:54:12Z
slug: analysis-of-the-gen2-addressable-rgb-led-protocol
draft: true
url: /2024/01/21/analysis-of-the-gen2-addressable-rgb-led-protocol/
aliases:
  # - /?p=1576
categories:
  - LED
  - Reverse Engineering
  # - Hardware
  # - Intelligent LED
  # - Reverse engineering
tags:
  - Addressable RGB
  # - LED > Addressable RGB
  # - LED
  # - Reverse Engineering
  # - Gen2 ARGB
  # - RGB LED
  # - WS2812
summary: "Summarizes the research into the PC-focused Gen2 addressable RGB extension to the WS2812 protocol, covering the motivation for parallel string drive, basic signaling additions, and the diagnostic readback channel. The post introduces the newly available SK6112 LEDs, links to the full GitHub write-up, and includes a topology diagram that shows how Gen2 controllers fan out power, data, and return lines to multiple fixtures."
showTableOfContents: false



---
The WS2812 has been around for a decade and remains highly popular, alongside its numerous clones. The protocol and fundamental features of the device have only undergone minimal changes during that time.

However, during the last few years a new technology dubbed “Gen2 ARGB” emerged for use in RGB-Illumination for PC, which is backed by the biggest motherboard manufacturers in Taiwan. This extension to the WS2812 protocol allows connecting multiple strings in parallel to the same controller in addition to diagnostic read out of the LED string.

Not too much is known about the protocol and the supporting LED. However, recently some LEDs that support a subset of the Gen2 functionality became available as “SK6112”.

I finally got around summarizing the information I compiled during the last two years. You can find the full documentation on Github linked [here](https://github.com/cpldcpu/Gen2-Addressable-RGB/blob/main/docs/Gen2_ARGB_protocol_analysis.md).

{{< gallery >}}
  <img src="gen2_topology.png" alt="" />
{{< /gallery >}}
