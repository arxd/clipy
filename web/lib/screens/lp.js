import { html } from 'htm/preact'
import { useEffect } from 'preact/hooks'
import { CSS } from 'lib/dom.js'
import { A } from 'components/router.js'

CSS.register('screen-lp', `
a {
    font-size: 3em;
}
a:hover {
    background-color: var(--accent);
}
`)

export const LP = () => {
    useEffect(() => CSS.use('screen-lp'))
    return html`
        <h1>Landing page<//>
        <${A} href="/demo">Demo Components<//>
    `
}
