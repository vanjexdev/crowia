import { defineConfig } from 'vite';

export default defineConfig({
    base: '/crowia/',
    build: {
        outDir: '../docs',
        emptyOutDir: true,
    },
});
