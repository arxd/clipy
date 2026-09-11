import { useRef, useCallback, useState, useEffect } from 'preact/hooks'
import { html } from 'htm/preact'
import { HideTop } from './hide_top.js'
import { } from './icon.js'
import { } from './toolbar.js' // using tool-bar
import { CSS, LSN } from 'lib/dom.js'
import { signal, effect, computed, batch } from '@preact/signals'

export const windowWidth = signal(window.innerWidth)
LSN(window, 'resize', () => {windowWidth.value = window.innerWidth}, {throttle:500})
export const isSP = computed(() => windowWidth.value < 760)

CSS.register('layout-menu', `
.layout-menu > main {
    padding: 0 1rem;
}
.layout-menu tool-bar:first-of-type {
    background-color: var(--accent);
    color: var(--accent-fg);
}
.layout-menu > nav {
    background-color:var(--card);
    color:var(--muted);
}
.layout-menu > nav a {
    display: block;
    box-sizing: border-box;
    width:100%;
    padding: 1em;
}
.layout-menu > nav > a:hover {
    background-color: var(--accent);
    color: var(--accent-fg);
}
`)


CSS.register('layout-menu-small', `
.layout-menu {
    overflow-y: scroll;
}
.layout-menu > .open {
    /*display:flow-root;*/
}
.layout-menu > .closed {
    display:none;
}
`)

CSS.register('layout-menu-large', `
.layout-menu {
    display:flex;
    align-items: stretch;
}
.layout-menu > nav {
    width:300px;
    flex-grow:0;
    flex-shrink:0;
    overflow-y: scroll;
}
.layout-menu > main {
    flex-grow:1;
    padding: 0 1em;
    overflow-y: scroll;
}
`)

CSS.register('menu-item', `
menu {
    list-style-type: none;
    margin:0;
    padding:0;
}
menu button, menu a {
    width:100%;
}
menu button:hover, menu a:hover {
    background-color: var(--c1);
    color: var(--c1f1);
}
`)


export const Menu = ({children}) => html`
    <menu>${children}</menu>
`


export const LayoutMenuBase = ({isSP, ...props}) => {
    const nav_ref = useRef()
    console.log('layout menu base', isSP, props)
    useEffect(() => {
        //const size = isSP? 'small': 'large'
        const el = nav_ref.current.parentElement
        el.classList.add('layout-menu')
        return () => el.classList.remove('layout-menu')
    }, [])
    
    return isSP? LayoutMenuSmall({nav_ref, ...props}): LayoutMenuLarge({nav_ref, ...props})
}



export const LayoutMenuSmall = ({nav_ref, nav, top_left, top_center, top_right, children}) => {
    const [open, set_open] = useState(false)
    const clicked = useCallback(() => set_open(!open), [open])
    useEffect(() => CSS.use('layout-menu-small', 'layout-menu'))

    return html`
        <${HideTop}>
            <tool-bar>
                <div slot="center">${top_center}</div>
                <i-i value=${'MENU'} onClick=${clicked} />
                ${top_left}
                <fill-space />  
                ${top_right}
            <//>
        <//>
        <nav class=${open?'open':'closed'} ref=${nav_ref}>
            ${nav}
        <//>
        <main class=${open?'closed':'open'}>
            ${children}
        </main>
    `
}



export const LayoutMenuLarge = ({nav_ref, nav, top_left, top_right, top_center, children}) => {
    useEffect(() => CSS.use('layout-menu-large', 'layout-menu'))
    return html`
        <nav ref=${nav_ref}>
            <tool-bar>
                <div slot="center">${top_center}</div>
                ${top_left}         
                <fill-space />  
                ${top_right}
            <//>
            ${nav}
        <//>
        <main>
            ${children}
        <//>
    `
}


export const LayoutMenu = (props) => {
    return html`<${LayoutMenuBase} isSP=${isSP.value} ...${props} />`
}

