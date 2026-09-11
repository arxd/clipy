import { CSS, EL, E } from 'lib/dom.js'


export class FillSpace extends HTMLElement {
    constructor() {
        super()
        const shadow = this.attachShadow({ mode: 'open' })
        CSS.el(':host {display: inline-block; flex-grow: 1;}', shadow)
    }
}
EL(FillSpace)


const _shadow_css = `
:host {
    display: flex;
    width: 100%;
    position: relative;
    justify-content: space-between;
    align-items: center;
}
.center {
    display: flex;
    justify-content: center;
    align-items: center;
    position: absolute;
    inset: 0;
    pointer-events: none;
}
.center > div {
    pointer-events: all;
}
`

export class ToolBar extends HTMLElement {
    constructor() {
        super()
        const shadow = this.attachShadow({ mode: 'open' })
        CSS.el(_shadow_css, shadow)
        E(shadow, {tag:'div', class:'center', children:[{tag:'slot', name:'center'}]}, {tag:'slot'})
    }
}
EL(ToolBar)
