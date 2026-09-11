import { cloneElement } from 'preact'
import { useRef, useEffect } from 'preact/hooks'

/// Make the child element auto-hide
///
/// <div style="overflow-y:scroll">    
///     <${HideTop}>
///         <div>Auto-hiding menu</div>
///     <//>
///     <p> The rest of the scolling content </p>
/// </div>
export const HideTop = ({children}) => {
    const ref = useRef()
    useEffect(() => {
        const child = ref.current
        const parent = child.parentElement
        child.style.position = 'relative'
        let prev_scrollTop = parent.scrollTop
        const scroll = () => {
            const child_top = child.getBoundingClientRect().top
            const parent_top = parent.getBoundingClientRect().top
            const content_top = child_top - parent_top + parent.scrollTop
            const position = (prev_scrollTop > parent.scrollTop)?'sticky':'relative'
            prev_scrollTop = parent.scrollTop
            if (position === child.style.position) return
            child.style.position = position
            child.style.top = `${position==='sticky'?0:content_top}px`
            const child_rect = child.getBoundingClientRect()
            const dy = Math.max(child_top - child_rect.top, -child_rect.height)
            if (position === 'sticky') {
                child.style.transform = `translateY(${dy}px)`
                child.offsetHeight  // Force the browser to commit the transform.
                child.style.transition = 'transform 200ms ease'
                child.style.transform = 'translateY(0)'
                child.addEventListener('transitionend', () => {
                    child.style.transition = ''
                    child.style.transform = 'translateY(0)'
                }, { once: true })
            } else {
                child.style.transition = ''
                child.style.transform = 'translateY(0)'
            }
        }
        parent.addEventListener('scroll', scroll)
        return () => {
            parent.removeEventListener('scroll', scroll)
        }
    }, [])
    return cloneElement(children, {ref})
}
