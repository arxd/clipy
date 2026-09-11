import { custom_element } from './uiux.js'

function heading(el) {
    const m = /^[hH](\d+)$/.exec(el?.tagName)
    return m?parseInt(m[1]):0
}

export class ScrollHeadings extends HTMLElement {
    constructor() {
        super()
        this.addEventListener('scroll', this.scroll)
    }

    connectedCallback() {
        let h_before = null
        let i = 1
        for (let child of this.children) {
            const level = heading(child)      
            if (!level) continue
            child.style.zIndex = i
            i += 1
            child.h_before = h_before
            while (heading(h_before) >= level) h_before = h_before.h_before
            child.style.top = h_before?(parseInt(h_before.style.top) + h_before.offsetHeight) +'px': '0px'
            h_before = child
        }
    }

    scroll({currentTarget:el}) { 
    }
}

custom_element(ScrollHeadings, `
scroll-headings {
    display:block;
    height:100%;
    position:relative;
    overflow-y:scroll;
    overflow-x:hidden;
}
scroll-headings h1, scroll-headings h2, scroll-headings h3, scroll-headings h4, scroll-headings h5, scroll-headings h6 {
    position: sticky;
}
`)