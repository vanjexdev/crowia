import { createApp } from './vendor/courvux.js';
import NavBar from './components/NavBar.js';
import Hero from './components/Hero.js';
import Features from './components/Features.js';
import HowTo from './components/HowTo.js';
import Footer from './components/Footer.js';
import './style.css';
import './layout.css';

createApp({
    components: {
        'site-navbar': NavBar,
        'site-hero': Hero,
        'site-features': Features,
        'site-howto': HowTo,
        'site-footer': Footer,
    },
}).mount('#app');
