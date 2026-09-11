import { useRef, useEffect } from 'preact/hooks'
import { render } from 'preact'
import { custom_element } from './uiux.js'


export class Popup extends HTMLElement {
    constructor(target, vdom, attrs={}) {
        super()
        this.vdom = vdom
        for (let kv of Object.entries(attrs)) this.setAttribute(kv[0], kv[1])
        this.target = target
        this.click = (e) => {
            if (!this.contains(e.target)) this.close()
            if (target.contains(e.target)) e.stopPropagation() // re-clicking the target closes instead of re-opening
        }
        this.scroll = (e) => {
            if (!this.contains(e.target)) {
                e.stopPropagation()
                e.preventDefault()
            }
        }
    }

    connectedCallback() {
        const margin = 10
    // handlers
        document.addEventListener('click', this.click, {capture:true})
        document.addEventListener('wheel', this.scroll, {capture:true, passive:false})
        window.addEventListener('resize', () => this.close({force:true}), {once:true})
    // Reset
        this.style.width = null
        this.style.height = null
        this.style.left = '0px'
        this.style.top = '0px'
    // Render and calculate environment
        render(this.vdom, this)
        const target = this.target.getBoundingClientRect()
        let body_w = document.documentElement.clientWidth
        let pop_w = this.offsetWidth
        if (pop_w > body_w - 2*margin) {
            pop_w = body_w - 2*margin
            this.style.width = pop_w + 'px'
        }
        let body_h = document.documentElement.clientHeight
        let pop_h = this.offsetHeight
    // bottom or top?
        const space_below = body_h - target.bottom - margin
        if (space_below >= pop_h) {
            this.style.top = target.bottom + 'px'
        } else {
            const space_above = target.top - margin
            if (space_above >= pop_h) {
                this.style.top = target.top - pop_h + 'px'
            } else if (space_above > space_below) {
                this.style.top = target.top - space_above + 'px'
                this.style.height = space_above + 'px'
            } else {
                this.style.top = target.bottom + 'px'
                this.style.height = space_below + 'px'
            }
        }
    // horizontal: always center on screen
        this.style.left = (body_w - pop_w) / 2 + 'px'
    }

    disconnectedCallback() {
        document.removeEventListener('click', this.click, {capture:true})
        document.removeEventListener('wheel', this.scroll, {capture:true, passive:false})
    }


    close({force}={}) {
        if (force) return this.remove()
        if (this.classList.contains('closing')) return
        this.classList.add('closing')
        this.addEventListener('transitionend', () => {
            this.classList.remove('closing')
            this.remove()
        }, {once:true})
    }
}

custom_element(Popup, `
pop-up {
    display: block;
    position: fixed;
    box-shadow: 0px 0px 20px rgba(0, 0, 0, 0.5), 0px 0px 5px rgba(0, 0, 0, 0.9);
    background-color: var(--c2);
    color: var(--c2f1);
    border-radius: 0.3em;
    z-index:999;
    opacity: 1;
    transition: opacity 0.2s ease-out;
    overflow-y: scroll;
    box-sizing: border-box;
}
    
pop-up.closing {
    opacity: 0;
}
`, 'pop-up')



export class GlassPane extends HTMLElement {
    constructor() {
        super()
    }
}
custom_element(GlassPane,`
glass-pane {
    display: block;
    position: fixed;
    inset: 0;
    opacity: 0.2;
    background-color: white;
`)



export const usePopup = (target, vdom, attrs={}) => {
    const popup = useRef()
    useEffect(() => () => popup.current?.close(), [])
    return () => {
        popup.current = new Popup(target(), vdom, attrs)
        document.body.append(popup.current)
    }
}
