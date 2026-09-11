import { useCallback, useState, useRef, useEffect } from 'preact/hooks'
import { html } from 'htm/preact'
import { ICONS } from 'components/icon.js'
import { LayoutMenu } from 'components/layout_menu.js'
import { HideTop } from 'components/hide_top.js'
//import { Popup, usePopup } from 'components/popup.js'
import { useRoute, Router, A, match_re } from 'components/router.js'
import { CSS } from 'lib/dom.js'

const DemoIcons = () => {
    useEffect(() => CSS.use('icon-label'))
    return html`
        <h1>Icons</h1>
        <div style="display:flex; gap:1em; flex-wrap:wrap;">
            ${Object.keys(ICONS).map((i) => html`
                <span key=${i} class="icon-label"><i-i value=${i} />${i}</span>
            `)}
        </div>
    `
}



const DemoHideTop = (props) => {
    return html`
        ${ipsum[1]}
        <div style="position:relative; height:200px; overflow-y:scroll; overflow-x:hidden; border:1px solid black;">
            <${HideTop}>
                <div style="background-color:red; color:white">HideTop</div>
            <//>
            ${ipsum[0]}
        </div>
        ${ipsum[2]}
    `
}

/*
const long_list = html`<menu>${Array.from({length:11}, (_,i)=>html`<li>Item ${i}</li>`)}<//>`

const DemoPopup = () => {
    const target = useRef()
    const center = useRef()
    const left = useRef()
    const right = useRef()
    const small = usePopup(()=>target.current, html`<div>Popup</div>`, {class:'simple'})
    const center_popup = usePopup(()=>center.current, ipsum[2], {class:'large'})
    const left_popup = usePopup(()=>left.current, long_list)
    const right_popup = usePopup(()=>right.current, long_list)

    return html`
        <h1>Popup</h1>
        <div style="position:relative; margin-left:100px; width:200px; height:200px; overflow-y:scroll; z-index:1; overflow-x:hidden; border:1px solid black;">
            <h1> Hello</h1>
            <p>The quick <span ref=${target} onClick=${small} style="cursor:pointer">brown</span> fox</p>
            ${ipsum[0]}
        </div>
        
        <hr />
        ${ipsum[2]}
        <div style="display:flex;justify-content:space-between">
            <span ref=${left} onClick=${left_popup}>Left</span>
            <span ref=${center} onClick=${center_popup}>Center</span>
            <span ref=${right} onClick=${right_popup}>Right</span>
        </div>
        ${ipsum[2]}
    `
}

  
const Bob = ({x, children}) => html`<nav style="width:100px; height:100px" id="mainbar">${x} - ${children}</nav>`

const dummy = () => html`<div class="menu-layout small">
    <${Bob} x='hi'>world<//>
    <h1 class="closed"> The quick brown fox</h1>
</div>`

*/
CSS.register('demo-top', '.top { font-size: 3em; height: fit-content; color: var(--accent); }')
const DemoTop = () => {
    useEffect(() => CSS.use('demo-top'))
    return html`
        <h1>Demo-Top</h1>
        <p>This is a set pages to demonstrate all the different components</p>
        ${ipsum[0]}
        ${ipsum[1]}
        ${ipsum[2]}
    `
}


const routes = [
    {match:match_re(/^\/?$/), html:()=>html`<${DemoTop} />`},
    {match:match_re(/^\/icons$/), html:()=>html`<${DemoIcons} />`},
    {match:match_re(/^\/hide-top$/), html:()=>html`<${DemoHideTop} />`},
    //{match:match_re(/^\/popup$/), html:()=>html`<${DemoPopup} />`},
    //{match:() => true, html:() => dummy()},//html`<div>Unknown</div>`},
]


export const Demo = (props) => {
    return html`<${LayoutMenu}
        nav=${html`
            <${A} href="/demo/icons">Icons<//>
            <${A} href="/demo/hide-top">HideTop<//>
            <${A} href="/demo/popup">Popup<//>
            `}
        top_center=${html`<${A} href="/demo">Demo<//>`}
        >
            <${Router} routes=${routes} />
        <//>
    `
}


export const ipsum = [html`
    <h1>Main Topic</h1>
    <p>This is an introduction paragraph to the main topic.</p>

    <h2>Subtopic 1</h2>
    <p>This paragraph provides information about Subtopic 1.</p>

    <ul>
        <li>
            <h3>Point 2.1</h3>
            <p>Details about Point 2.1.</p>
        </li>
    </ul>
`,html`
    <h1>The Whimsical World of Animals</h1>
    <p>Welcome to the enchanting journey through the animal kingdom, where each creature has a story to tell!</p>

    <h2>The Adventures of Sir Whiskers</h2>
    <p>Sir Whiskers is a noble cat who embarks on daring adventures across the backyard realm.</p>
`,html`
    <ul>
        <li>
            <h3>The Great Garden Quest</h3>
            <p>Sir Whiskers sets out to find the mythical Catnip Stone hidden somewhere in the garden.</p>
        </li>
        <li>
            <h3>The Encounter with the Squirrel Knight</h3>
            <p>During his quest, Sir Whiskers faces off against the valiant Squirrel Knight, who guards the ancient oak tree.</p>
            <ul>
                <li>
                    <h4>The Duel at Dawn</h4>
                    <p>As the sun rises, the two engage in a friendly duel of agility and wit.</p>
                </li>
                <li>
                    <h4>The Feast of Friendship</h4>
                    <p>After the duel, they share a feast of acorns and fish, forging an unlikely friendship.</p>
                </li>
            </ul>
        </li>
    </ul>

    <h2>Lady Fluffington's Tea Party</h2>
    <p>Lady Fluffington, the esteemed rabbit of the meadow, hosts the most delightful tea parties.</p>

    <ul>
        <li>
            <h3>The Guest List</h3>
            <p>A collection of the finest forest creatures are invited, each with a unique flair.</p>
        </li>
        <li>
            <h3>The Mushroom Table</h3>
            <p>Lady Fluffington's tea table is made of the largest mushroom in the meadow, adorned with flowers and leaves.</p>
            <ul>
                <li>
                    <h4>The Bluebird's Serenade</h4>
                    <p>The bluebird sings a melodious tune, setting the perfect ambiance for the gathering.</p>
                </li>
                <li>
                    <h4>The Hedgehog's Delight</h4>
                    <p>A hedgehog arrives with a basket of the sweetest berries, much to everyone's delight.</p>
                </li>
            </ul>
        </li>
    </ul>
`]