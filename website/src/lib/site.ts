import catalogue from '../../public/generated/catalogue.json';
import type { MarkdownInstance } from 'astro';

export { catalogue };
export const locales = ['zh', 'en'] as const;
export type Locale = typeof locales[number];
export const base = import.meta.env.BASE_URL.replace(/\/$/, '');
export const url = (path = '') => `${base}/${path.replace(/^\//, '')}`;
export const media = (name: string) => url(`generated/media/${name}`);
export const repository = 'https://github.com/hza2002/agent-bloom';
export const documents = Object.entries(import.meta.glob<MarkdownInstance<{title: string; order: number}>>(
  '../../../docs/user/**/*.md', { eager: true },
)).map(([path, module]) => {
  const [, locale, slug] = path.match(/\/user\/(zh|en)\/(.+)\.md$/)!;
  return { locale, slug, module, title: module.frontmatter.title, order: module.frontmatter.order };
}).sort((a, b) => a.order - b.order);

export const copy = {
  zh: {
    themes: '主题', reference: '命令参考', animation: '开场动画', default: '默认',
    description: '为 Claude Code 和 Codex CLI 换上你喜欢的主题。',
    preview: '主题预览', use: '使用这个主题', copied: '已复制',
    copyError: '无法复制，请手动选择文本。', agent: '交给 agent 安装',
    raw: '读取 Markdown', source: '在 GitHub 查看源文件', docs: '文档', skip: '跳到正文',
  },
  en: {
    themes: 'Themes', reference: 'Command reference', animation: 'Entrance', default: 'Default',
    description: 'Find your theme for Claude Code and Codex CLI.',
    preview: 'Theme preview', use: 'Use this theme', copied: 'Copied',
    copyError: 'Copy failed. Select the text manually.', agent: 'Ask your agent to install',
    raw: 'Read Markdown', source: 'View source on GitHub', docs: 'Documentation', skip: 'Skip to content',
  },
};
