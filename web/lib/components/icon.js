import { EL, E, CSS } from 'lib/dom.js'


CSS.register('icon-label', `
.icon-label {
    display: inline-flex;
    gap: 0.1em;
    align-items: center;
    white-space: nowrap;
    user-select: none;
}
`)

const _shadow_css = `
:host {
    display: inline-block;
    width: var(--icon-size, 1.5em);
    height: var(--icon-size, 1.5em);
    margin: 0 var(--icon-pad-right, 0) 0 var(--icon-pad-left, 0);
    fill: currentColor;
}
`

export const ICONS = {
    // make the keys strings so that closure compiler doesn't rename them
    'REPLAY': "M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z",
    'ARROW_LEFT': "M14 7l-5 5 5 5V7z",
    'ARROW_RIGHT': "M10 17l5-5-5-5v10z",
    'KBD_LEFT': "M15.41 16.59L10.83 12l4.58-4.59L14 6l-6 6 6 6 1.41-1.41z",
    'IOS_BACK': "M11.67 3.87L9.9 2.1 0 12l9.9 9.9 1.77-1.77L3.54 12z",
    'MENU': "M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z",
    'ADD_CIRCLE_OUTLINE': "M13 7h-2v4H7v2h4v4h2v-4h4v-2h-4V7zm-1-5C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z",
    'ADD_CIRCLE': "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm5 11h-4v4h-2v-4H7v-2h4V7h2v4h4v2z",
    'ADD': "M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z",
    'CLOSE': "M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z",
    'HOME': "M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z",
    'LOGIN': "M11,7L9.6,8.4l2.6,2.6H2v2h10.2l-2.6,2.6L11,17l5-5L11,7z M20,19h-8v2h8c1.1,0,2-0.9,2-2V5c0-1.1-0.9-2-2-2h-8v2h8V19z",
    'LOGOUT': "M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z",
    'EDIT': "M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z",
    'BOX_SELECT': "M12 5.5L10 8H14L12 5.5M18 10V14L20.5 12L18 10M6 10L3.5 12L6 14V10M14 16H10L12 18.5L14 16M21 3H3C1.9 3 1 3.9 1 5V19C1 20.1 1.9 21 3 21H21C22.1 21 23 20.1 23 19V5C23 3.9 22.1 3 21 3M21 19H3V5H21V19Z",
    'HAND': "M21 7C21 5.62 19.88 4.5 18.5 4.5C18.33 4.5 18.16 4.5 18 4.55V4C18 2.62 16.88 1.5 15.5 1.5C15.27 1.5 15.04 1.53 14.83 1.59C14.46 .66 13.56 0 12.5 0C11.27 0 10.25 .89 10.04 2.06C9.87 2 9.69 2 9.5 2C8.12 2 7 3.12 7 4.5V10.39C6.66 10.08 6.24 9.85 5.78 9.73L5 9.5C4.18 9.29 3.31 9.61 2.82 10.35C2.44 10.92 2.42 11.66 2.67 12.3L5.23 18.73C6.5 21.91 9.57 24 13 24C17.42 24 21 20.42 21 16V7M19 16C19 19.31 16.31 22 13 22C10.39 22 8.05 20.41 7.09 18L4.5 11.45L5 11.59C5.5 11.71 5.85 12.05 6 12.5L7 15H9V4.5C9 4.22 9.22 4 9.5 4S10 4.22 10 4.5V12H12V2.5C12 2.22 12.22 2 12.5 2S13 2.22 13 2.5V12H15V4C15 3.72 15.22 3.5 15.5 3.5S16 3.72 16 4V12H18V7C18 6.72 18.22 6.5 18.5 6.5S19 6.72 19 7V16Z",
    'TRASH': "M9,3V4H4V6H5V19A2,2 0 0,0 7,21H17A2,2 0 0,0 19,19V6H20V4H15V3H9M7,6H17V19H7V6M9,8V17H11V8H9M13,8V17H15V8H13Z",
    'PANORAMA_FISHEYE': "M12 2C6.47 2 2 6.47 2 12s4.47 10 10 10 10-4.47 10-10S17.53 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z",
    'DRAW_POLYGON': "M12 3L4.5 8.5L7 17L17 17L19.5 8.5ZM10.5 3a1.5 1.5 0 1 0 3 0a1.5 1.5 0 1 0-3 0M3 8.5a1.5 1.5 0 1 0 3 0a1.5 1.5 0 1 0-3 0M5.5 17a1.5 1.5 0 1 0 3 0a1.5 1.5 0 1 0-3 0M15.5 17a1.5 1.5 0 1 0 3 0a1.5 1.5 0 1 0-3 0M18 8.5a1.5 1.5 0 1 0 3 0a1.5 1.5 0 1 0-3 0",
    'CAPTURE_VIEW': "M5 15H3v4c0 1.1.9 2 2 2h4v-2H5v-4zM5 5h4V3H5C3.9 3 3 3.9 3 5v4h2V5zm14-2h-4v2h4v4h2V5c0-1.1-.9-2-2-2zm0 16h-4v2h4c1.1 0 2-.9 2-2v-4h-2v4zM12 9c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z",
}


export class Icon extends HTMLElement {
    static get observedAttributes() {
        return ['value']
    }
    
    constructor() {
        super();
        const shadow = this.attachShadow({ mode: 'open' })
        CSS.el(_shadow_css, shadow)
        this.path = document.createElementNS("http://www.w3.org/2000/svg", 'path')
        this.attributeChangedCallback()
        shadow.appendChild(E('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"></svg>', this.path))
    }

    attributeChangedCallback() {
        this.path.setAttribute('d', ICONS[this.getAttribute('value')] || ICONS['ADD'])
    }
}

EL(Icon, null, 'i-i')
