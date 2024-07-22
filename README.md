# Documents preprocessing Applications

## Introduction

This repo contains applications of pipeline nodes for preprocess document data in dataloop platform.
It also include integration between [Unstructured io](https://unstructured-io.github.io/unstructured/index.html#)
functions and [Dataloop](https://dataloop.ai/). The Unstructured library is crafted to facilitate the preprocessing and
structuring of unstructured text documents,
enabling their utilization in subsequent machine learning endeavors. It supports various document formats such as PDFs,
XML, and HTML.

## Description

The Applications provide preprocessing methods for dealing with textual datasets in order to visualize in Dataloop
platform and prepare the items to be used as an input to ML model for variety of
tasks.

The available pipeline nodes:

* ```PDF to Images``` - This app serves as pipeline node. Can be used if the user want to convert PDF data
  to images. by that it can be visualized in the platform and also can be appropriate for using computer vision models.


* ```PDF to Text``` - This app serves as pipeline node. Can be used if the user want to convert PDF data
  to text files. By that it can be visualized in the platform and also can be appropriate for using several LLM/NLP
  models.


* ```Text Preprocessing``` - This app serves as pipeline node. This app preprocess
  PDFs dataset to create clean text files. This files can be an input for nlp model or to be converted to prompt input.


* ```PPT Sanitization``` - This app serves as pipeline node. This app takes a slide presentation and sanitizes it by 
removing any visual identity or.



*** In the future, similar applications will be available for different types of textual files such as: HTML, eml (
email), jsons and so on.

