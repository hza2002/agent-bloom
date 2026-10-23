import { defineConfig } from 'astro/config';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { satteri } from '@astrojs/markdown-satteri';

const base = '/agent-bloom';
const root = fileURLToPath(new URL('../', import.meta.url));

// Source Markdown links work on GitHub. Transform their destinations only for HTML.
const documentationLinks = {
  name: 'documentation-links',
  link(node, context) {
      if (!/^(?:[a-z]+:|#|\/)/i.test(node.url)) {
        const [relative, hash = ''] = node.url.split('#');
        const target = path.relative(root, path.resolve(path.dirname(fileURLToPath(context.fileURL)), relative));
        const match = target.match(/^docs\/user\/(zh|en)\/(.+)\.md$/);
        const destination = match
          ? `${base}/${match[1]}/docs/${match[2]}/${hash ? '#' + hash : ''}`
          : `https://github.com/hza2002/agent-bloom/blob/main/${target}${hash ? '#' + hash : ''}`;
        context.setProperty(node, 'url', destination);
      }
  },
};

export default defineConfig({
  site: 'https://hza2002.github.io',
  base,
  trailingSlash: 'always',
  markdown: {
    shikiConfig: { themes: {light: 'github-light', dark: 'github-dark'}, defaultColor: false },
    processor: satteri({ features: {smartPunctuation: false}, mdastPlugins: [documentationLinks] }),
  },
});
