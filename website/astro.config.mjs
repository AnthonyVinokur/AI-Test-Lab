import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";

export default defineConfig({
  site: "https://aitestlab.dev",

  integrations: [
    starlight({
      title: "AI Test Lab",

      description:
        "An open-source framework for testing, evaluating, and benchmarking AI and large language models.",

      social: [
        {
          icon: "github",
          label: "GitHub",
          href: "https://github.com/AnthonyVinokur/AI-Test-Lab",
        },
      ],

      sidebar: [
        {
          label: "Getting Started",
          items: [
            {
              label: "Introduction",
              slug: "getting-started/introduction",
            },
            {
              label: "Installation",
              slug: "getting-started/installation",
            },
          ],
        },
      ],
    }),
  ],
});