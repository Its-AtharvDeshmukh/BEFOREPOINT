import {afterEach} from 'vitest';
import {cleanup} from '@testing-library/react';
afterEach(()=>{cleanup();localStorage.clear();sessionStorage.clear()});
class ResizeObserverStub{observe(){}unobserve(){}disconnect(){}}
globalThis.ResizeObserver=ResizeObserverStub;
