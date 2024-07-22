# PPT Sanitization

This app creates a pipeline node that takes as input an item containing a pptx file and outputs a new presentation with 
the same general content as the original, but with no visual identity (white backgrounds and black Arial font for text),
 and the following substitutions will happen:

* **Companies, organization, non-profit institutions** will be replaced with the tag **[Org]**
* **Countries, cities, villages, streets, sites** will be replaced with the tag **[Location]**
* **Personal names** will be replaced with the tag **[Person]**
* **Project names** will be replaced with the tag **[Project]**
* **Currency names and symbols** will be replaced with the tag **[Currency]**
* **Numerical financial data** will be replaced with the tag **[xx]**
* **Stock tickers** will be replaced with the tag **[Stock]**
* **Visual identifiers** like logos and company-related themes will be replaced by **black rectangles**, indicating 
that previously an identifier was there

In order to use this app, you will need to include a [secret](https://docs.dataloop.ai/docs/manage-secrets) for an 
[OpenAI API key](https://help.openai.com/en/articles/4936850-where-do-i-find-my-openai-api-key) in the [Dataloop 
platform](https://console.dataloop.ai). In the [service configuration](https://docs.dataloop.ai/docs/service-runtime),
add the name of the created secret as the init input ```open_ai_key``` so the service will be able to use it:

![Service config](../assets/init_inputs.png)