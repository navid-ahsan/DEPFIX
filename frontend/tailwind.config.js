/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#0070f3',
        secondary: '#373737',
        depfix: {
          err:   '#ff3c3c',
          fix:   '#00ff88',
          cyan:  '#00d4ff',
          amber: '#ffb700',
          vec:   '#a78bfa',
          bg:    '#060810',
          bg2:   '#0b0f1e',
          dim:   '#304060',
          text:  '#b0c8e8',
        },
      },
      fontFamily: {
        orbitron:    ['Orbitron', 'monospace'],
        'share-tech': ['Share Tech Mono', 'monospace'],
        exo2:        ['Exo 2', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
