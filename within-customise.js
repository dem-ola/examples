'use strict'

// glob
var glob = {
    'base href': '',
    'current page': '',
    'current page index': 0,
    'pages': [],
    'consoles': [],
    'current console': '',
    'animating': false,
    'threshold catch': false,
    'console animating': false,
    'wheels': 0,
    'consoles on': true,
    'window height': window.innerHeight,
    'window width': window.innerWidth,
    'orientation': 'landscape',
    'desktop like': true,
    'tablet like': false,
    'mobile like': false,
    'mobile limit': 400, // portrait-ish
    'swipe profile': [],
    'is projects' : false,
    'is gallery': false,
    'london': '',
    'new york': '',
    'hong kong': '',
    'clients': '',
    'team page done': false,
    'clients page done': false,
    'clocks done': false,
    'pages': '',
    'pages with videos': '',
    'last scroll': '',
    'scroll direction': 'down',
    'default team console': {},
    'animating id': [],
    'last scroll time': 0,
    'is locked': false,
    'landing': false,  // to avoid probono/privacy errors
    'member selected': null,
    'orientation change': null,
}

var reOrient = {
    'mobile to p' : 'p to l',
    'mobile to l' : 'l to p',
    'tablet to p' : 'p to l',
    'tablet to l' : 'l to p', 
}

// left: 37, up: 38, right: 39, down: 40,
// spacebar: 32, pageup: 33, pagedown: 34, end: 35, home: 36
var keys = {37: 1, 38: 1, 39: 1, 40: 1};

function preventDefault(e) {
  e = e || window.event;
  if (e.preventDefault)
      e.preventDefault();
  e.returnValue = false;  
}

function preventDefaultForScrollKeys(e) {
    if (keys[e.keyCode]) {
        preventDefault(e);
        return false;
    }
}

function disableScroll() {
    if (window.addEventListener) // older FF
        window.addEventListener('DOMMouseScroll', preventDefault, false);
    document.addEventListener('wheel', preventDefault, {passive: false}); // Disable scrolling in Chrome
    window.onwheel = preventDefault; // modern standard
    window.addEventListener('mousewheel', preventDefault, {passive: false});
    window.onmousewheel = document.onmousewheel = preventDefault; // older browsers, IE
    window.ontouchmove  = preventDefault; // mobile
    document.onkeydown  = preventDefaultForScrollKeys;
}

function enableScroll() {
    if (window.removeEventListener)
        window.removeEventListener('DOMMouseScroll', preventDefault, false);
    document.removeEventListener('wheel', preventDefault, {passive: false}); // Enable scrolling in Chrome
    window.removeEventListener('mousewheel', preventDefault, {passive: false});
    window.onmousewheel = document.onmousewheel = null; 
    window.onwheel = null; 
    window.ontouchmove = null;  
    document.onkeydown = null;  
}

/* disable and enable scrolling */
function gainLock() {
    document.addEventListener('mousewheel', preventDefault, {passive: false});
    document.body.style.overflow = 'hidden';
    disableScroll();
    glob['is locked'] = true;
}
function releaseLock() {
    enableScroll();
    document.body.style.overflow = '';
    document.removeEventListener('mousewheel', preventDefault, {passive: false});
    glob['is locked'] = false;
}

/* get object containing pages with associated consoles */
function gatherPagesConsoles() {

    let pages = [];
    let consoles = [];
    // we'll pair pages and their consoles to ensure
    // we pick the right consoles - id naming convention is crucial
    let bigElems = {};
    let getPages = document.querySelectorAll("div[id^='page-']");
    let getConsoles = document.querySelectorAll('.console-wrap');
 
    let lenPages = getPages.length;
    let lenCons = getConsoles.length;
    // get pages
    for (let p = 0; p < lenPages; p++) {
        let theId = getPages[p].id;
        let key = theId.slice(5); // take out leading 'page-'
        bigElems[key] = {'page': getPages[p],
                        'cons': null }            
    }
    // get consoles
    for (let c = 0; c < lenCons; c++) {
        let theId = getConsoles[c].id;
        let toMatch = theId.slice(0,-8); // take out trailing '-console'
        if (bigElems.hasOwnProperty(toMatch)) {
            bigElems[toMatch]['cons'] = getConsoles[c]
        }
    }

    // we'll put all the consoles in an array
    // using this instead of querySelectorAll calling .console-wrap as latter
    // will have an index that won't match pages[index] if any Show Console is false 
    // but now we'll have to test if console exists
    for (let p in bigElems) {
        if (bigElems.hasOwnProperty(p)) {
            pages.push(bigElems[p]['page'])
            consoles.push(bigElems[p]['cons'])
        }
    }

    glob['pages'] = pages;
    glob['consoles'] = consoles;
}

function getVideos() {
    glob['videos'] = document.querySelectorAll('video'); 
}

function getPagesWithVideos() {
    let pages = glob['pages'];
    let pageVideos = [];
    for (let p = 0; p < glob['pages'].length; p++) {
        let thePage = pages[p];
        let check = thePage.querySelectorAll('video');
        if (check.length > 0) {
            pageVideos.push(thePage);
        }
    }
    glob['pages with videos'] = pageVideos;
}

function getPagesWithVimeos() {
    let pages = glob['pages'];
    let pageVideos = [];
    for (let p = 0; p < glob['pages'].length; p++) {
        let thePage = pages[p];
        let check = thePage.querySelectorAll('iframe');
        if (check.length > 0) {
            pageVideos.push(thePage);
        }
    }
    glob['pages with vimeos'] = pageVideos;
}

/* what page are we on */
function isOnPageProjects() {
    let curPage = 0;
    let thresh = 0.5; // default for scrolling down 
    let pages = glob['pages'];
    let winHeight = glob['window height'];
    let inView = [];
    let direction = glob['scroll direction'];
    if (sessionStorage.scrollTop <= 0) {
        curPage = 0; // no scrolling yet
    } else {
        for (let p = 0; p < pages.length; p++) {
            let yPos = pages[p].getBoundingClientRect().y;
            if (direction == 'down' && yPos < winHeight * thresh) {
                    inView.push(p);
                } 
            else if (direction == 'up' && yPos < winHeight * thresh) {
                inView.push(p);
            }
        }
    }
    if (inView.length > 0) {
        curPage = inView[inView.length-1];
    }
    return curPage;
}

function isOnPage() {
    let isOn = 0;
    let href = window.location.href;
    let hash = href.indexOf('#');
    let pageId = href.slice(hash);
   
    if ((hash == -1 && href.indexOf('projects') == -1) || pageId == '' || pageId == '/') {
        isOn = 0;
        glob['current page index'] = isOn;
    } else if (href.indexOf('projects') != -1) {
        isOn = isOnPageProjects();
        glob['current page index'] = isOn;
    } else {
        let page = document.querySelector(pageId);
        isOn = glob['pages'].indexOf(page);
    }
    return isOn
}

/* pause video on page on slide away */
function pauseVideo(thePage) {
    let videos = thePage.querySelectorAll('video');
    for (let v = 0; v < videos.length; v++) {
        videos[v].pause();
    }
}

/* play video on page on slide into */
function playVideo(thePage) {
    let videos = thePage.querySelectorAll('video');
    for (let v = 0; v < videos.length; v++) {
        videos[v].play();
    }
}

/* keeps menu attached to left if window being resized while menu is open */
function resizeMenuPage() {
    let menuPage = document.querySelector("#menu-page");
    if (menuPage.style.display == 'block') {
        let w = parseFloat(window.getComputedStyle(menuPage).width)
        menuPage.style.transform = 'translateX('+w+'px'
        menuPage.style.transition = 'transform 0s'
    }
}


function resetPageZ_(direction, index, prevIndex) {
    let pages = glob['pages'];
    if (direction == 'down') {
    for (let p = 0; p < index + 1; p++) {
        pages[p].style.zIndex =  p;
    }
    for (let p = Math.min(pages.length - 1, index + 1); p < pages.length; p++) {
        pages[p].style.zIndex =  '';
    }
    } else {
        pages[index].style.zIndex =  index;
        for (let p = 0; p < pages.length; p++) {
            if (p != index) {
            pages[p].style.zIndex =  -p;
            }
        }
    }
}

function resetPageZ(direction, index, prevIndex) {
    let pages = glob['pages'];
    if (!glob['landing']) return false;

    pages[index].style.zIndex =  1;
    pages[prevIndex].style.zIndex =  0;
    for (let p = 0; p < pages.length; p++) {
        if (p != index && p != prevIndex)
        pages[p].style.zIndex =  -1;
    }
}


function resetPageTransforms(reload, direction, index, prevIndex, orientationChange=false) {
    var pages = glob['pages'];
    let theWidth, theHeight;
    theHeight = window.innerHeight; // default
    let timeout = (orientationChange) ? 500 : 0;

    // set a timeout to get the current window dimensions after orientation change
    // without timeout the old pre-orientation values for w and h are what we get
    // whereas the new w and h should take care of the realigned browser navigation/address bars
    if (orientationChange) {
        setTimeout(function() {
    
            setMobileDimensions();

            let longEnd = glob['mobile long end'];
            let shortEnd = glob['mobile short end'];
        
            let orient = getOrientation(); // this is the old one

            if (orient == 'landscape') {

                if (orient != glob['orientation'] ) { 
                    theHeight = longEnd; // portrait height
                } else { // probably from a reload after orientation change so keeping it landscape
                    theHeight = shortEnd; // portrait height
                }  
            } else {
    
                if (orient != glob['orientation'] ) {
                    theHeight = shortEnd;
                } else {
                    theHeight = longEnd;
                }
            }
        
            if (reload) {
                index += 1;  // we also want to reset current page
            }

            for (let p = 0; p < index; p++) {       
                pages[p].style.transform =  "translate3d(" + 0 + ", -" + theHeight * p + "px, 0)";
                pages[p].style.transition = 'transform 0s'
            }

        }, timeout);

    } else {       
        for (let p = 0; p < pages.length; p++) {                        
            if (direction == 'down') {
                pages[index].style.transform =  "translate3d(0, -" + window.innerHeight + "px, 0)";
                if (p != index) {
                    pages[p].style.transform =  '';
                }
            }
        }
    }
}

/* create navigation bar using titles garnered from header */
function navIndicator() {
    let navWrap = document.querySelector('#nav-indicator');
    for (let p = 0; p < pageTitles.length; p++) {
        let navCol = document.createElement('div');
        editClass(navCol, 'indicator-col', '', 'add');
        navWrap.appendChild(navCol);
        navCol.textContent = pageTitles[p];
        navCol.addEventListener('click', function() {
            loadPage(false, p + 1, null, null, true); // +1 because landing page excluded from titles
        }, {passive: true})
        navCol.addEventListener('touchstart', function() {
            loadPage(false, p + 1, null, null, true); // +1 because landing page excluded from titles
        }, {passive: true})
    }
}

/* load page from menu or navigation bar */
function loadPage(reload, index, href=null, fromLoad=false, fromNavBar=false) {

    let pages, consoles, direction
    let onPage = Math.max(0, isOnPage());

    // get full url
    if (glob['landing']) {  
        consoles = glob['consoles'];
        pages = glob['pages'];
        direction = 'down'
        if (onPage > index) {direction = 'up'}


        if (!href) { //use index to get ID if no href provided
            if (!fromLoad) {
                href = glob['base href'] + '/#' + pages[onPage].id;
            } else { //eg from menu or navbar in projects
                href = glob['base href'] + '/#' + pages[index].id;
            }
        }
    } else if (glob['is projects']) {
        // open landing hash page
        window.open(glob['base href']+'/#nav-'+index, '_self');
        return false
        
    } else { // open landing section
        href = glob['base href']
    }
    
    // get console
    let pageName = pages[index].id.slice(5);
    window.open(href, '_self');
    toggleNameImage(onPage);   
    let showingConsole, currentConsole;
    document.querySelector('#console-button-wrap').style.display = 'block'
    for (let c = 0; c < consoles.length; c++) {
        if (consoles[c]) {
            if (consoles[c].style.zIndex > 0) showingConsole = consoles[c];
            if (consoles[c].id.indexOf(pageName) != -1) {
                currentConsole = consoles[c];
                setConsoleButton(currentConsole);
                setConsoles(currentConsole);
            }
        } 
    }
    if (showingConsole && (showingConsole != currentConsole)) hideConsole(showingConsole);

    // reloads
    if (!reload) {
        if (fromNavBar) {
            if (!glob['animating']) {
                swipePage(false, index, direction, true, onPage)
            }
        }
    } 
}

/* open and close menu using menu icon or menu close button */
function openCloseMenu() {
    // initialise
    let menu = document.querySelector("#menu-icon");
    let menuitems = document.querySelectorAll(".menu-item");
    let menuClose = document.querySelector("#menu-close");
    let menuPage = document.querySelector("#menu-page");
    let moveDuration = 1000;
    let pages = glob['pages'];
    let onPage = isOnPage();

    function moveMenu() {
        // calc width based on current window width as window may have been resized
        if (menuPage.style.display != 'block') {
            menuPage.style.display = 'block';
            setTimeout(function() { // timeout allows multiple clicks to work
                menuPage.style.transform = 'translateX('+menuPage.clientWidth+'px)';
                menuPage.style.transition = "transform "+moveDuration+"ms";
            }, 1)
        } else {
            menuPage.style.transform = 'translateX(0px)';
            menuPage.style.transition = "transform "+moveDuration+"ms";
            setTimeout(function() {
                menuPage.style.display = 'none'; // after move     
            }, moveDuration)
        } 
    }

    menu.addEventListener('touchstart', function(e) {
        moveMenu();
    }, {passive: true});
    menuClose.addEventListener('touchstart', function(e) {
        moveMenu();
    }, {passive: true});
    menu.addEventListener('click', function(e) { // because maybe iOS
        moveMenu();
    }, {passive: true});
    menuClose.addEventListener('click', function(e) { // because maybe iOS
        moveMenu();
    }, {passive: true});

    function itemClick(e, i) {

        e.preventDefault(); // we'll handle it below
        moveMenu();
        
        // get name of page and match to correct console
        let pageName = menuitems[i].querySelector('a').getAttribute('href');
        pageName = pageName.slice(pageName.indexOf("#page-"));

        let index = pages.indexOf(document.querySelector(pageName))
        loadPage(false, index, menuitems[i].querySelector('a').getAttribute('href'), null, true );
    }
 
    for (let i = 0; i < menuitems.length; i++) {
        menuitems[i].addEventListener('touchstart', function(e) {
            itemClick(e, i)
        }, {passive: true});
    }
}

/* check if to collapse console on load */
function isCollapseConsoleOnLoad(theConsole) {
    let collapse = false;
    if (theConsole) {
        if (theConsole.className.indexOf("console-collapse-load") != -1) {
            collapse = true;
        }
    }
    return collapse
} 

/* don't display the console button */
function removeConsoleButton(btnDuration=500) {
    let theButton = document.querySelector('#console-button');
    let theButtonWrap = document.querySelector('#console-button-wrap');
    theButton.style.opacity = 0;
    theButton.style.transition = 'opacity 1s';
}

/* display expand button where consoles are collapsed */
function displayExpandButton(btnDuration=500) {
    let theButton = document.querySelector('#console-button');
    if (theButton.getAttribute('src') != glob['expand button']) {
        removeConsoleButton(btnDuration=btnDuration*0.5)
    }    
    theButton.setAttribute('src', glob['expand button']);
    editClass(theButton, 'console-button-expand', 'console-button', 'add'); 
    theButton.style.opacity = 1;
    theButton.style.transition = 'opacity 1s';
} 

/* display collapse buttons where consoles are visible */
function displayCollapseButton(btnDuration=500) {
    let theButton = document.querySelector('#console-button');
    if (theButton.getAttribute('src') != glob['collapse button']) {
        removeConsoleButton(btnDuration=btnDuration*0.5);
    }
    theButton.setAttribute('src', glob['collapse button']);
    theButton.style.opacity = 1;
    theButton.style.transition = 'opacity 1s';
    editClass(theButton, 'console-button-expand', '', 'remove');  
}

function setConsoleButton(currentConsole, fromToggle=false) {
    let consolesOn = glob['consoles on'];
    let theButton = document.querySelector('#console-button');
    let theButtonWrap = document.querySelector('#console-button-wrap');
    if (currentConsole) {
        if (!consolesOn) {
            displayExpandButton();
        } else {         
            (!isCollapseConsoleOnLoad(currentConsole)) ? displayCollapseButton() : displayExpandButton();
        }
        // contact page console in mobile portrait is 100% height so no need for button
        if (currentConsole.id == "contact-console" && glob['is mobile'] && glob['orientation'] == 'portrait') {
                theButton.style.display = 'none';
                theButtonWrap.style.display = 'none';
        } else {
            theButton.style.display = 'block';
            theButtonWrap.style.display = 'block';
        } 
     } else {
        removeConsoleButton();
    }
}

/* don't show console */
function hideConsole(theConsole, forAll=false) {
    let consoles = glob['consoles'];
    function hideThis(thisConsole) {
        let timeout = 1500;
        if (thisConsole != null) {
            setTimeout(function() {
                thisConsole.style.opacity = 0;
                thisConsole.style.transition = 'opacity '+timeout+'ms'
            },1);
            setTimeout(function() { // do separately
                thisConsole.style.zIndex = -20
            }, timeout);
        } 
    }
    if (!forAll) {
         hideThis(theConsole)   
    } else {
        for (let c = 0; c < consoles.length; c++) {
            hideThis(consoles[c])
        }
    }
}

/* upload console on page load or reload */
function showConsole(theConsole, fromToggle=false) {

    var consoles = glob['consoles'];
    var consolesOn = glob['consoles on'];
    var conLen = consoles.length;

    if (fromToggle & consolesOn) {
        for (let c = 0; c < conLen; c++) {
            if (consoles[c]) {
                if(isCollapseConsoleOnLoad(consoles[c])) {
                    editClass(consoles[c], 'console-collapse-load', '', 'remove');
                }
            }
        }
    } 
    
    // load current console and display correct button
    if (!theConsole) return false;
    if (consolesOn && !isCollapseConsoleOnLoad(theConsole)) {
        if ( Math.floor(theConsole.style.opacity) == 0 || theConsole.style.zIndex < 0) { 
            theConsole.style.zIndex = 30;
            theConsole.style.opacity = 1;
            theConsole.style.transition = 'opacity 600ms'
        }
    } else if (consolesOn && isCollapseConsoleOnLoad(theConsole)) {
        hideConsole(theConsole);   
    } 
}

function setConsoles(theConsole) {
    if (theConsole) {
        if(!isCollapseConsoleOnLoad(theConsole)) {
            showConsole(theConsole);
        } else {
            hideConsole(theConsole);
        }
    }
}

function editClass(elem, theName, curName, action) {
    if (action == 'add') {
        if (elem.className.indexOf(theName) == -1) {
            elem.className += ' ' + theName;
        }  
    } else if (action == 'remove') {
        elem.className =  elem.className.replace(theName, '');
    } else if (action == 'swap') {
        elem.className =  elem.className.replace(curName, theName);
    }
    elem.className =  elem.className.trim();
}

/* console buttons */
function toggleConsole() {
    var theButton = document.querySelector('#console-button');
    var theButtonWrap = document.querySelector('#console-button-wrap');
    let consoles = glob['consoles'];

    function toggleIt() {
        let expandBtnUrl = glob['expand button'];
        let collapseBtnUrl = glob['collapse button'];
        let toggleDuration = 500;
        let onPage = isOnPage();
        let currentConsole = consoles[onPage];
        let previousConsole = null;

        if (theButton.getAttribute('src') == collapseBtnUrl) {
            glob['consoles on'] = false;
            hideConsole(currentConsole, true, toggleDuration);
            editClass(theButton, 'console-button-expand', 'console-button', 'add');
            theButton.setAttribute('src', expandBtnUrl);  

        } else {
            glob['consoles on'] = true;
            if (!glob['is projects']) {
                showConsole(currentConsole, true);
                editClass(theButton, 'console-button-expand', '', 'remove')
            } else {
                if (glob['is mobile'] && glob['orientation'] == 'portrait') {
                    showConsole(consoles[0])
                } else {
                    setConsoleButton(currentConsole);
                    setProjectConsoles(previousConsole, currentConsole, true);
                }
                editClass(theButton, 'console-button-expand', '', 'remove')
            }
            theButton.setAttribute('src', collapseBtnUrl);    
        }
    }
    

    theButtonWrap.addEventListener('click', function(e) {
        toggleIt();
    }, {passive: true});
    theButtonWrap.addEventListener('touchstart', function(e) {
        toggleIt();
    }, {passive: true});
}

/* projects gallery page */
function projectsGallery() {
    
    var projBoxes;
    let img = document.querySelector("#company-name-image")
    img.style.display = 'block'  
    projBoxes = document.querySelectorAll('.projects-gallery-box');
    gainLock();

    // show content on hover; open project page on click
    function boxData(resp) {

        // push PHP object into array
        let theProjects = []
        for (let proj in resp) {
            theProjects.push(resp[proj]);
        }
        let projNumber = theProjects.length;

        // add background images
        for (let i = 0; i < projNumber; i++) {
            let theBox = projBoxes[i];
            theBox.style.backgroundImage = "url('" + theProjects[i][4]['guid'] + "')";
        }

        function mouseEnter(e, index) {
            e.style.opacity = 0;
            e.style.transition = 'opacity 0s'	
            setTimeout(function() { // timeout for 2nd transition to work
                e.style.backgroundColor = theProjects[index][1];
                e.querySelector(".proj-header").textContent = theProjects[index][0];
                e.querySelector(".proj-content").textContent = theProjects[index][2];
                e.style.backgroundImage = '';
                e.style.opacity = 1;
                e.style.transition = 'opacity 1s'	
            }, 1)
        }

        // add event listeners
        function doEventListeners(e) {
      
            e.clicked = 0;
            e.style.overflow = 'hidden'
            let id = e.id
            let index = Number(id.slice(9)); // takes out proj-box-; parseInt didn't work
            e.addEventListener('mouseenter', function() {
                e.style.opacity = 0;
                e.style.transition = 'opacity 0s'	
                setTimeout(function() { // timeout for 2nd transition to work
                    e.style.backgroundColor = theProjects[index][1];
                    e.querySelector(".proj-header").textContent = theProjects[index][0];
                    e.querySelector(".proj-content").textContent = theProjects[index][2];
                    e.style.backgroundImage = '';
                    e.style.opacity = 1;
                    e.style.transition = 'opacity 1s'	
                }, 1)
            }, {passive: true});

            e.addEventListener('mouseleave', function() {
                e.querySelector(".proj-header").innerHTML = '';
                e.querySelector(".proj-content").innerHTML = '';
                e.style.backgroundImage = "url('" + theProjects[index][4]['guid'] + "')";
                // sometimes text gets stuck: ensure that change happens if box is out of focus
                for (let i = 0; i < projNumber; i++) {
                    let theBox = projBoxes[i];
                    if (theBox.id !== e.id) {
                        theBox.style.backgroundImage = "url('" + theProjects[i][4]['guid'] + "')";
                    }
                }
            }, {passive: true});
            
            e.addEventListener('click', function() {
                window.location = theProjects[index][3];
            }, {passive: true});

            e.addEventListener('touchstart', function(elem) {
               // for mobile - first click reveals open button; second click opens project page
               if (glob['is mobile']) {
                    for (let i = 0; i < projNumber; i++) {
                        let theBox = projBoxes[i];
                        if (theBox.id == elem.srcElement.id) {   
                            let open = elem.srcElement.querySelector('.project-open');
                            let openWrap = elem.srcElement.querySelector('.project-open-wrap');
                            openWrap.style.transform = 'scale(1)';
                            open.style.transform = 'scale(1)';
                            open.addEventListener('touchstart', function(e) {
                                window.location = theProjects[index][3];
                            }, {passive: true});
                            break;
                        }
                    }
                } else {
                    window.location = theProjects[index][3];
                }   
            });      
        }       
        Array.prototype.forEach.call(projBoxes, doEventListeners)
    }

    glob['projects data'] = jsonWork;
    boxData(jsonWork);
}

/* show name image on landing else show logo */
function toggleNameImage(pageIndex, duration) {
    let theImage = document.querySelector("#company-name-image"); 
    let theLogo = document.querySelector("#company-logo-wrap"); 
    if (glob['is projects']) {   
        theImage.style.opacity = 0;
        theImage.style.transition = "opacity 1s";           // projects
        theLogo.style.opacity = 1;
        theLogo.style.transition = "opacity 1s";
    } else if (window.location.href.indexOf('?') != -1 && 
        window.location.href.indexOf('#') == -1 ) {         // standalone eg probono
            theImage.style.opacity = 0;
            theImage.style.transition = "opacity 1s"; 
            theLogo.style.opacity = 1;
            theLogo.style.transition = "opacity 1s";
    } else if (pageIndex == 0) {                            // landing page
        theImage.style.opacity = 1;
        theImage.style.transition = "opacity 1s";
        theLogo.style.opacity = 0;
        theLogo.style.transition = "opacity 1s";
    } else {                                                // other landing page sections
        theImage.style.opacity = 0;
        theImage.style.transition = "opacity 1s";
        theLogo.style.opacity = 1;
        theLogo.style.transition = "opacity 1s";
    }
}

// console buttons - from landing page & project templates
function storeConsoleButtons() {
    // 'is gallery' check in case project (not gallery) with one page
    if (glob['pages'].length > 0 && !glob['is gallery']) {
        glob['expand button'] = expandButton;
        glob['collapse button'] = collapseButton;
    }
}

/* set onPage to zero if clicked home icon */
function homeIconPageReset(onPage) {
        
    let compName = document.querySelector("#company-name-image");
    compName.addEventListener('click', function(e) { 
        onPage = 0; 
        sessionStorage.scrollTop = 0;
        loadPage(true, 0, glob['base href']);
    }, {passive: true})
    compName.addEventListener('touchstart', function(e) { 
        onPage = 0; 
        sessionStorage.scrollTop = 0; 
        loadPage(true, 0, glob['base href']);
    }, {passive: true})
    
    let compLogo = document.querySelector("#company-logo");
    compLogo.addEventListener('click', function(e) { 
        onPage = 0; 
        sessionStorage.scrollTop = 0; 
        loadPage(true, 0, glob['base href']);
    }, {passive: true})
    compLogo.addEventListener('touchstart', function(e) { 
        onPage = 0; 
        sessionStorage.scrollTop = 0; 
        loadPage(true, 0, glob['base href']);
    }, {passive: true})

    return onPage;
}

/* add/remove class names */
function editClass(elem, theName, curName, action) {

    if (elem) {
        if (action == 'add') {
            if (elem.className.indexOf(theName) == -1) {
                elem.className += ' ' + theName;
            }  
        } else if (action == 'remove') {
            elem.className =  elem.className.replace(theName, '');
        } else if (action == 'swap') {
            elem.className =  elem.className.replace(curName, theName);
        }
        elem.className =  elem.className.trim();
    }
}

/* previous | next project buttons */
function setPreviousNext() {
    
    let theProjects = [];
    let projNames = [];
    let curProjIndex, nextProjIndex, prevProjIndex;
    let projData = glob['projects data'];
    let pages = glob['pages'];

    // push needed data to array
    for (let proj in projData) {
        theProjects.push(projData[proj][3]);
        projNames.push(projData[proj][0]);
    }

    // set previous project && next project links
    let numbOfProjects = theProjects.length;
    curProjIndex = theProjects.indexOf(window.location.href);
    prevProjIndex = curProjIndex - 1;
    if (prevProjIndex < 0) {
        prevProjIndex = numbOfProjects - 1;
    }
    nextProjIndex = curProjIndex + 1;
    if (nextProjIndex > numbOfProjects - 1) {
        nextProjIndex = 0;
    }

    let prevLink = theProjects[prevProjIndex];
    let prevName = projNames[prevProjIndex];
    let nextLink = theProjects[nextProjIndex];
    let nextName = projNames[nextProjIndex];

    // attach links to document
    let main = document.querySelector( "#main");
    let navWrap = document.querySelector( "#proj-nav-wrap")
    
    if (navWrap == null) {
        navWrap = document.createElement("div");
        navWrap.setAttribute('id', "proj-nav-wrap");
        main.appendChild(navWrap)
        
        let prevImg = document.createElement("img");
        prevImg.setAttribute('src', prevProjectArrow[0]);
        let nextImg = document.createElement("img");
        nextImg.setAttribute('src', nextProjectArrow[0]);
        navWrap.innerHTML  = "<a id='proj-nav-left' class='proj-nav' href='"+prevLink+"'><img src="+prevProjectArrow+"></a><a id='proj-nav-right' class='proj-nav' href='"+nextLink+"'><img src="+nextProjectArrow+"></a>";
    }
}

/* hide / show project consoles */
function setProjectConsoles(prevConsole, currentConsole, fromToggle=false) {

    let pages = glob['pages'];
    let docHeight = 0;

    for (let p = 0; p < pages.length; p++) {
        docHeight += pages[p].clientHeight;
    }

    if (currentConsole && prevConsole) {
        showConsole(currentConsole, fromToggle);
        if (currentConsole != prevConsole) { 
            hideConsole(prevConsole)
        }  
    } else if (!currentConsole && prevConsole) {
        hideConsole(prevConsole, true);
    } else if (currentConsole && !prevConsole) {
        showConsole(currentConsole, fromToggle);
        hideConsole(prevConsole);
    }
}

function atDocumentBottom() {
    let atBottom = false;
    let pages = glob['pages'];
    const atBottomMargin = 0.25 ;

    // calculate height of document - sum of all pages
    let docHeight = 0;
    for (let p = 0; p < pages.length; p++) {
        docHeight += pages[p].clientHeight;
    }

    // check if close to the bottom of the document
    if (window.innerHeight + parseInt(sessionStorage.scrollTop) > docHeight * (1 - atBottomMargin)) {
        atBottom = true;           
    } 
    return atBottom
}

function projectsScrolling(onPage) {

    // on load
    let pages = glob['pages']; 
    let consoles = glob['consoles'];
    let prevConsole = consoles[onPage] // default
    var hasScrolled = false;

    // determine if in mobile portrait view 
    let mobilePortrait = false; 
    if (glob['mobile like']  && glob['orientation'] == 'portrait') {
        mobilePortrait = true;
    }
     
    // update consoles on scrolling
    glob['last scroll'] = sessionStorage.scrollTop || 0; 
    glob['start scroll'] = onPage;
    var isScrolling;        // timer
    let scrollIDs = []
    let checkIDs = [];
    let atBottom = false;

    let main = document.querySelector("#main");
    //main.style.overflowY = 'scroll'; // not ''
    main.style.overflowX = 'hidden';

    if (main.scrollTop < window.innerHeight) {
        setConsoleButton(consoles[0]);
        setProjectConsoles(null, consoles[0]);
    }
   
    main.addEventListener('scroll', function() { 
    
        // check where user is during scrolling - 
        sessionStorage.scrollTop = Math.max(0, main.scrollTop);  
        onPage = isOnPageProjects();
        let currentConsole = consoles[onPage];

        // check scroll direction
        setTimeout(function() {
            glob['last scroll'] = sessionStorage.scrollTop;
        }, 500);       
        if (onPage > glob['start scroll'] || sessionStorage.scrollTop > glob['last scroll']) {
            glob['scroll direction'] = 'down' ;
        } else if (onPage < glob['start scroll'] || sessionStorage.scrollTop < glob['last scroll']) {
            glob['scroll direction'] = 'up' ;
        }
        glob['start scroll'] = onPage; // update

        // check if close to the bottom of the document
        if (atDocumentBottom()) {
            atBottom = true;           
        } else 

        // set current console
        // for projects portrait; it's impossible to have a console to a page
        // so we keep current console to the first one and then hide it
        // close to bottom to reveal Previous / Next Project buttons
        if (mobilePortrait) {
            currentConsole = consoles[0];
        } else {
            currentConsole = consoles[onPage];
        }
        
        // create a timout function that registers an ID while user is scrolling
        isScrolling = setTimeout(function() {}, 20);
        scrollIDs.push(isScrolling);

        // we then clear the TimeoutIDs until only one is left
        // this is the indication the user has stopped scrolling
        while (scrollIDs.length > 1) {         
            window.clearTimeout(scrollIDs[0]);
            scrollIDs.shift(); 
            hasScrolled = true;  
        }

        // meanwhile we periodically register the last console seen
        // once user stops scrolling, check if last console has changed
        // if yes, then update the console and console button
        let check = setTimeout(function() {
            
            if (hasScrolled) {
                hasScrolled = false;

                if (atBottom) setPreviousNext();

                if (mobilePortrait) {
                    if (atBottom && currentConsole.style.opacity != 0) {
                        setConsoleButton(null);
                        hideConsole(currentConsole, true);
                    } else if (!atBottom && (currentConsole.style.opacity != 1 || currentConsole.style.zIndex < 0)) {
                        setConsoleButton(currentConsole);
                        setProjectConsoles(prevConsole, currentConsole);
                    } 
                } else {
                    if (prevConsole != currentConsole) { // also takes care of when both are null
                        setConsoleButton(currentConsole);                   // set console button
                        setProjectConsoles(prevConsole, currentConsole);
                        prevConsole = currentConsole;                       // updates and resets
                    }
                }
            }
        }, 20) 
        // clear timer to avoid repeated actions
        checkIDs.push(check);
        while (checkIDs.length > 1) {         
            window.clearTimeout(checkIDs[0]);
            checkIDs.shift(); 
        }  
    });

    // on load - if no console loaded yet then load the first one
    // but don't if atBottom
    if (!hasScrolled) {
        let currentConsole = consoles[0];
        if (atDocumentBottom()) {
            setConsoleButton(null);
            setPreviousNext();
            if (mobilePortrait) hideConsole(null, true);
        } else {
            if (currentConsole) {
                setConsoleButton(currentConsole);
                setProjectConsoles(prevConsole, currentConsole);
            }
        }
    }
}

function setMobileDimensions() {
    let dimA = window.innerWidth;
    let dimB = window.innerHeight;
    glob['mobile short end'] = Math.min(dimA, dimB);
    glob['mobile long end'] = Math.max(dimA, dimB);
}

function deviceLike() {
    let winWidth = window.innerWidth;
    let winHeight = window.innerHeight;
    glob['window height'] = winHeight;
    glob['window width'] = winWidth;
    if (winWidth > 1400) {
        glob['desktop like'] = true;
    } else if (winWidth > 760) {
        glob['tablet like'] = true;
    } else {
        glob['mobile like'] = true;
    }
}
 
/* store window parameters */
function setScreenVariables() {

    // store window dimensions in cookie - will be used by PHP templates
    document.cookie = 'window_width='+window.innerWidth;
    document.cookie = 'window_height='+window.innerHeight;

    // screen variables
    deviceLike()
    glob['orientation'] = getOrientation();
    glob['loaded orientation'] = getOrientation(); // for mobile orientation changes
     // if really mobile
     glob['is mobile'] = checkIfMobile();
 
    // store href location
    let href = window.location.href;
    let whereName = href.indexOf('withininternational');
    let whereSlash = href.indexOf('/',whereName);
    let baseHref = href.slice(0,whereSlash);
    glob['base href'] = baseHref;

    if (href.indexOf('projects') != -1) {
        glob['landing'] = false;
        if (href.indexOf('gallery') == -1) { // not gallery page
            glob['is projects'] = true;
        } else {
            glob['is gallery'] = true;
        }
    } else {
        if (href.indexOf('?') == -1) { // exclude privace/pro-bono
            glob['landing'] = true;
        }
    }
}

/* rebuild team console after swipes so not stuck on team member bio */
function rebuildTeamConsole() {

    // set variables
    let teamConsole, conLeft, conMid, conRight;
    teamConsole = document.querySelector('#team-console');
    if (teamConsole) {
        if (glob['mobile like'] && glob['orientation'] == 'portrait') { 
            conLeft = teamConsole.querySelector(".console-mobile-title");
            conMid = teamConsole.querySelector('.console-mobile-text');
            conRight = teamConsole.querySelector('.console-mobile-text');
        } else {
            conLeft = teamConsole.querySelector('#team-console-left');
            conMid = teamConsole.querySelector('#team-console-middle');
            conRight = teamConsole.querySelector('#team-console-right');
        }

        // rebuild
        if (glob['mobile like'] && glob['orientation'] == 'portrait') { 
            conLeft.innerHTML = glob['default team console']['conLeft'];
            conMid.innerHTML = glob['default team console']['conMid'];
            teamConsole.querySelector('.console-mobile-secondary').textContent = '';
            conMid.style.display = 'block';
        } else {
            conLeft.innerHTML = glob['default team console']['conLeft'];
            conMid.innerHTML = glob['default team console']['conMid'];
            conRight.innerHTML = glob['default team console']['conRight'];
        }
        teamConsole.style.zIndex = 30; 
        editClass(teamConsole, 'team-reveal', '','remove');
        editClass(teamConsole, 'team-reveal-console', '','remove');
        editClass(conLeft, 'team-reveal', '', 'remove');
        editClass(conMid, 'team-reveal', '', 'remove');
        editClass(conRight, 'team-reveal', '', 'remove');
    }
}


function teamSwipe(teamSize=20) {
    let teamConsole = document.querySelector('#team-console');
    let leftSwipeBtn = document.querySelector("#teamswipeLeft")
    let rightSwipeBtn = document.querySelector("#teamswipeRight")
    let row = document.querySelector("#team-row")
    let duration = 1200;
    rightSwipeBtn.style.display = 'none'; // on load
    
    // move page into view or out of view
    let move = 0; // set outside event listener
    let totalWidth = 0
    let showMembers = 0
    let membersMovedLeft = 0;
    let membersRemainingRight = 0;

    function goRight() {
        let members = document.querySelectorAll(".team-member");
        let winWidth = window.innerWidth; // redone in case page resized
        let memberWidth = members[0].clientWidth;
        
        let leftMargin = parseFloat(window.getComputedStyle(members[0]).marginLeft);
        let rightMargin = parseFloat(window.getComputedStyle(members[0]).marginRight);
        totalWidth = memberWidth + leftMargin + rightMargin;
        showMembers = parseInt(winWidth / totalWidth);
        move += totalWidth * showMembers;
        membersRemainingRight = teamSize - membersMovedLeft - showMembers
       
        if (membersRemainingRight > 0) {
            row.style.transform = 'translateX(-'+move+'px)';
            row.style.transition = "transform "+duration+"ms";
            membersMovedLeft += showMembers;
            membersRemainingRight -= showMembers;

            if (teamConsole) rebuildTeamConsole();
            rightSwipeBtn.style.display = "block";
            leftSwipeBtn.style.display = "block";   
            if ((membersMovedLeft + showMembers) >= teamSize) leftSwipeBtn.style.display = "none";             
        }
    }

    function goLeft() {
        let members = document.querySelectorAll(".team-member");
        let winWidth = window.innerWidth; // redone in case page resized
        let memberWidth = members[0].clientWidth;
        
        let leftMargin = parseFloat(window.getComputedStyle(members[0]).marginLeft);
        let rightMargin = parseFloat(window.getComputedStyle(members[0]).marginRight);
        totalWidth = memberWidth + leftMargin + rightMargin;
        showMembers = parseInt(winWidth / totalWidth);
        move -= totalWidth * showMembers;

        if (membersMovedLeft > 0) {
            if (Math.abs(move) < 1) move = 0; 
            row.style.transform = 'translateX(-'+move+'px)';
            row.style.transition = "transform "+duration+"ms";
            membersMovedLeft -= showMembers;
            membersRemainingRight += showMembers;

            if (teamConsole) rebuildTeamConsole();               
            leftSwipeBtn.style.display = "block";
            rightSwipeBtn.style.display = "block";   
            if (membersMovedLeft == 0) rightSwipeBtn.style.display = "none";             
        }
    }

    leftSwipeBtn.addEventListener('click', function(e) {
        goRight();
    }, {passive: true})
    leftSwipeBtn.addEventListener('touchstart', function(e) {
        goRight();
    }, {passive: true})
    rightSwipeBtn.addEventListener('click', function(e) {
        goLeft();
    }, {passive: true})
    rightSwipeBtn.addEventListener('touchstart', function(e) {
        goLeft();
    }, {passive: true})  
}

function teamReveal(e, fromOrientationChange=false) {
    //show highlight image and update console
    // show console if click on person 
    let theButton = document.querySelector('#console-button');
    let teamConsole = document.querySelector('#team-console');

    let conLeft, conMid, conRight;

    let orient = glob['orientation'];
    if (fromOrientationChange)  {
        orient = (glob['orientation'] == 'portrait') ? 'landscape' : 'portrait'
    }


    if (teamConsole) {
        if (glob['mobile like'] && orient == 'portrait') { 

            conLeft = teamConsole.querySelector(".console-mobile-title");
            conMid = teamConsole.querySelector('.console-mobile-text');
            conRight = teamConsole.querySelector('.console-mobile-text');
        } else {
            conLeft = teamConsole.querySelector('#team-console-left');
            conMid = teamConsole.querySelector('#team-console-middle');
            conRight = teamConsole.querySelector('#team-console-right');
        }
    }

    if (glob['is mobile'] && orient == 'landscape') {
        conLeft.textContent = '';
        if (!glob['consoles on']) {                   
            theButton.click();
        }
    } else if (glob['mobile like'] && orient == 'portrait') {
        conLeft = teamConsole.querySelector(".console-mobile-title");
        conLeft.textContent = '';
        conMid = teamConsole.querySelector(".console-mobile-secondary");
        conRight = teamConsole.querySelector('.console-mobile-text');
        if (!glob['consoles on']) {                   
            theButton.click();
        }
    } else {
        conLeft.textContent = '';
    }
    
    let par, linked_;
    par = e.parentElement;
    linked_ = par.getAttribute('linked');

    glob['member selected'] = e;

    // name
    let nam = document.createElement('div');
    nam.setAttribute('class','console-team-name');
    let the_name = par.getAttribute('name');
    nam.innerHTML = the_name;
    teamConsole.querySelector('.console-mobile-text').style.display = 'none';
    
    conLeft.appendChild(nam);

    // create linked-in
    let linked = document.createElement('div');
    conLeft.appendChild(linked);
    let link_a = document.createElement('a');
    link_a.setAttribute('href', par.getAttribute('linked'));  
    link_a.setAttribute('target', 'new');    
    link_a.style.textDecoration = 'none !important';
    editClass(link_a,'linkedin','','add');
    // skip linked in line if no details
    if (linked_ != '') { 
        linked.textContent = 'Contact on ';
        link_a.textContent = 'LinkedIn'; 
    }
    linked.appendChild(link_a);
    conLeft.appendChild(linked);

    // create email
    let mail = document.createElement('div');
    conLeft.appendChild(mail);
    mail.textContent = 'Email: ';
    let mail_a = document.createElement('a');
    mail_a.setAttribute('href', "mailto:"+par.getAttribute('email'));
    mail_a.textContent = par.getAttribute('email');
    mail_a.style.textDecoration = 'none';
    mail.appendChild(mail_a);
    conLeft.appendChild(mail);


    editClass(teamConsole, 'team-reveal', '','add');
    editClass(teamConsole, 'team-reveal-console', '','add');
    editClass(conLeft, 'team-reveal', '', 'add');
    editClass(conMid, 'team-reveal', '', 'add');
    editClass(conRight, 'team-reveal', '', 'add');
    editClass(link_a, 'team-reveal', '', 'add');
    editClass(mail_a, 'team-reveal', '', 'add');

    // bios
    let bio1 = par.getAttribute('bio1');
    let clip = 200;
    if (glob['mobile like'] && glob['orientation'] == 'portrait') {
        bio1 = bio1.slice(0, clip);
        conMid.textContent = bio1 + ' ...'
    } else {
        conMid.textContent = bio1;
        conRight.textContent = par.getAttribute('bio2');
    }
}

/* team page - build and resets */
function team_page() {

    function capitalise(words) {
        let splitUp = words.split(' ');
        let capped = '';
        for (let w = 0; w < splitUp.length; w ++) {
            let word = splitUp[w];
            let capw = word[0].toUpperCase() + word.slice(1).toLowerCase();
            capped += capw + ' ';
        }
        capped = capped.trim();
        return capped;
    }

    var conLeft, conMid, conRight;
    let teamConsole = document.querySelector('#team-console');
    var teamSize;

    if (teamConsole) {
        if (glob['mobile like'] && glob['orientation'] == 'portrait') { 
            conLeft = teamConsole.querySelector(".console-mobile-title");
            conMid = teamConsole.querySelector('.console-mobile-text');
            conRight = teamConsole.querySelector('.console-mobile-text');
        } else {
            conLeft = teamConsole.querySelector('#team-console-left');
            conMid = teamConsole.querySelector('#team-console-middle');
            conRight = teamConsole.querySelector('#team-console-right');
        }

        // save original data as needed to rebuild console so not stuck on a bio
        var clonedConLeft = conLeft.cloneNode(true);
        var clonedConMid = conMid.cloneNode(true);
        var clonedConRight = conRight.cloneNode(true);
        glob['default team console'] = {
            'conLeft': clonedConLeft.innerHTML,
            'conMid': clonedConMid.innerHTML,
            'conRight': clonedConRight.innerHTML,
        }
    }

    var numP; // number of pages 
    var mTop;

    createTeamPages(jsonTeam);
    var teamPhotos = document.querySelectorAll(".member-photo");
    var teamNames = document.querySelectorAll(".member-name");
    var teamPositions = document.querySelectorAll(".member-position");
    var eventElems = [teamPhotos, teamNames, teamPositions];
    for (let e = 0; e < eventElems.length; e++) {
        Array.prototype.forEach.call(eventElems[e], teamHover);
    }

    function createTeamPages(people) {

        // push PHP object into array
        let theTeam = []
        for (let member in people) {
            theTeam.push(people[member]);
        }
        let many = theTeam.length;
        teamSize = theTeam.length;

        let par = document.querySelector("#team-row");
        let memPerPage = 500; // default members per page
        if (glob['tablet like'] || (glob['mobile like'] && glob['orientation'] == 'landscape')) {
            memPerPage = 500;
        } else if (glob['mobile like'] && glob['orientation'] == 'portrait') {
            memPerPage = 500;
        }
        numP = Math.ceil(many / memPerPage);

        // fields
        //('publish', 'first_name', 'last_name', 'position', 'linkedin_link', "email", "biography_1", "biography_2", "initial_image", "highlight_image" );
        for (let r = 0; r < numP; r++ ) {
            let mPage = document.createElement('div');
            par.appendChild(mPage);
            mPage.setAttribute('id', 'team-page-'+r);
            mPage.setAttribute('class', 'team-page');

            let pStart = r * memPerPage;
            let pEnd = (r + 1) * memPerPage
            
            for (let p = pStart; p < pEnd; p++) {

                let member = theTeam[p];
                let mMem = document.createElement('span');

                if (member != undefined) {
                    let mName = member[1] + ' ' + member[2];
                    mMem.setAttribute('index', p);
                    mMem.setAttribute('name', mName);
                    mMem.setAttribute('class', 'team-member');
                    mMem.setAttribute('img1', member[8]['guid']);
                    mMem.setAttribute('img2', member[9]['guid']);
                    mMem.setAttribute('bio1',  member[6]);
                    mMem.setAttribute('bio2',  member[7]);
                    mMem.setAttribute('linked',  member[4]);
                    mMem.setAttribute('email',  member[5]);
                    mPage.appendChild(mMem);
                
                    let mPho = document.createElement('div');
                    mPho.setAttribute('class', 'member-photo');

                    let p1 = document.createElement('img');
                    p1.setAttribute('src', mMem.getAttribute('img1'));
                    p1.setAttribute('class','initial-image');
                    mMem.appendChild(mPho);
                    mPho.appendChild(p1);

                    let mNam = document.createElement('div');
                    mNam.setAttribute('class', 'member-name');
                
                    mNam.textContent = mName.toUpperCase();
                    mMem.appendChild(mNam);

                    let mPos = document.createElement('div');
                    mPos.setAttribute('class', 'member-position');
                    let memPos = member[3];
                    mPos.textContent = memPos;
                    mMem.appendChild(mPos);
                } 
            } 
        }
    }

    function teamHover(e) {
        
        var par = e.parentElement;
        var eImg = e.getElementsByTagName('img');
        if (eImg.length == 0 ) { // member names and positions
            eImg = par.firstChild.getElementsByTagName('img');
        }
        
        // on hover
        e.addEventListener('mouseenter', function () {      
            eImg[0].src = par.getAttribute('img2');
            teamReveal(e)
        }, {passive: true});

        e.addEventListener('mouseleave', function () {      
            eImg[0].src = par.getAttribute('img1');
        }, {passive: true});

        e.addEventListener('click', function () {      
            eImg[0].src = par.getAttribute('img2');
            teamReveal(e)
        }, {passive: true});

        e.addEventListener('touchstart', function (e) {      
            eImg[0].src = par.getAttribute('img2');
            teamReveal(e.srcElement.parentElement)
        }, {passive: true});
    }

    teamSwipe(teamSize);
}

/* scaling shifts swipe button around - and buttons don't stay in same position during resizing 
   this little algorithm is intended to keep the buttons fixed using 15" 1440px laptop as a base setting
   */
function setSwipeButton() {
    let swipeUp = document.querySelector("#swipe-up");
    let swipeUpWrap = document.querySelector("#swipe-up-wrap");
    let swipeDown = document.querySelector("#swipe-down");
    let swipeDownWrap = document.querySelector("#swipe-down-wrap");
    if (glob['landing']) {
        swipeUp.style.display = 'block';
        swipeDown.style.display = 'block';
        swipeUpWrap.style.display = 'block';
        swipeDownWrap.style.display = 'block';
    }
}

/* show/hide swipe buttons */
function toggleSwipeButton() {
    let swipeUp = document.querySelector("#swipe-up");
    let swipeDown = document.querySelector("#swipe-down");
    let swipeUpWrap = document.querySelector("#swipe-up-wrap");
    let swipeDownWrap = document.querySelector("#swipe-down-wrap");
    if (!glob['landing']) {
        swipeUp.style.display ='none';
        swipeDown.style.display ='none';
        swipeUpWrap.style.display ='none';
        swipeDownWrap.style.display ='none';
    } 
}

/* swipe from buttons - usefl for Edge as vanilla mousewheel doesn't work 
https://blogs.windows.com/msedgedev/2017/12/07/better-precision-touchpad-experience-ptp-pointer-events/
*/
function swipeButtons() {
    let swipeUp = document.querySelector("#swipe-up");
    let swipeDown = document.querySelector("#swipe-down");
    let swipeUpWrap = document.querySelector("#swipe-up-wrap");
    let swipeDownWrap = document.querySelector("#swipe-down-wrap");

    function swipe(direction) {
        let onPage = isOnPage();
        if (!glob['animating']) {
            swipePage(false, onPage, direction);
        }
    }

    swipeUp.addEventListener('click', function() {
        swipe('up');
    }, {passive: true});
    swipeUp.addEventListener('touchstart', function() {
        swipe('up');
    }, {passive: true});
    swipeDown.addEventListener('click', function() {
        swipe('down');
    }, {passive: true});
    swipeDown.addEventListener('touchstart', function() {
        swipe('down');
    }, {passive: true});

    swipeUpWrap.addEventListener('click', function() {
        swipe('up');
    }, {passive: true});
    swipeUpWrap.addEventListener('touchstart', function() {
        swipe('up');
    }, {passive: true});
    swipeDownWrap.addEventListener('click', function() {
        swipe('down');
    }, {passive: true});
    swipeDownWrap.addEventListener('touchstart', function() {
        swipe('down');
    }, {passive: true});
}

/* get DST time */
function getClock(zone, region) {

    var dst = 0;
    var time = new Date();
    var getMS = time.getTime() + (time.getTimezoneOffset() * 60000);
    var gmtTime = new Date(getMS);
    var day = gmtTime.getDate();
    var month = gmtTime.getMonth();
    var year = gmtTime.getFullYear();
    
    if (year < 1000) {
        year += 1900
    };

    var monthArray = new Array ("January", "February", "March", "April", "May",
     "June", "July", "August", "September", "October", "November", "December");

    var monthDays = new Array ("31", "28", "31", "30", "31", "30", "31", "31", "30", "31", "30", "31");
    
    // leap years
    if (year % 100 == 0 && year % 400 != 0) {
        monthDays = new Array ("31", "29", "31", "30", "31", "30", "31", "31", "30", "31", "30", "31");
     }

     var hr = gmtTime.getHours() + zone;
     var min = gmtTime.getMinutes();
     var sec = gmtTime.getSeconds();

     if (hr >= 24) {
         hr = hr - 24;
         day -= -1
     }

     if (hr < 0) {
        hr -= -24;
        day -= -1
    }

    if (hr < 10)  { hr = "0" + hr; }
    if (min < 10) { min = "0" + min; }
    if (sec < 10) { sec = "0" + sec; }

    if (day <= 0) {
        if (month == 0) {
            month = 11;
            year -= 1;
        } else {
            month = month - 1;
        }
        day = monthDays[month];
    }

    if (day > monthDays[month]) {
        day = 1;
        if (month == 11) {
            month = 0;
            year -= -1;
        } else {
            month -= -1;
        }
    }

    if (region == 'london') {
        var startDST = new Date();
        var endDST = new Date();
        startDST.setMonth(2);
        startDST.setHours(1);
        startDST.setDate(31);
        var dayDST = startDST.getDay();
        if (dayDST != 0) {
            startDST.setDate( 31 - dayDST)
        } else {
            startDST.setDate(1)
        }
        endDST.setMonth(9);
        endDST.setHours(0);
        endDST.setDate(31);
        dayDST = endDST.getDay();
        endDST.setDate(31 - dayDST);
        var currentTime = new Date()
        currentTime.setMonth(month);
        currentTime.setFullYear(year);
        currentTime.setDate(day);
        currentTime.setHours(hr);

        if (currentTime >= startDST && currentTime < endDST) {
            dst = 1
        }
    }

    if (region == 'new york') {
        var startDST = new Date();
        var endDST = new Date();
        startDST.setMonth(3);
        startDST.setHours(2);
        startDST.setDate(1);
        var dayDST = startDST.getDay();
        if (dayDST != 0) {
            startDST.setDate( 8 - dayDST)
        } else {
            startDST.setDate(1)
        }
        endDST.setMonth(9);
        endDST.setHours(1);
        endDST.setDate(31);
        dayDST = endDST.getDay();
        endDST.setDate(31 - dayDST);
        var currentTime = new Date()
        currentTime.setMonth(month);
        currentTime.setFullYear(year);
        currentTime.setDate(day);
        currentTime.setHours(hr);
        if (currentTime >= startDST && currentTime < endDST) {
            dst = 1
        }
    }

    if (region == 'hong kong') {
        var startDST = new Date();
        var endDST = new Date();
        startDST.setMonth(0);
        startDST.setHours(0);
        startDST.setDate(0);
        var dayDST = startDST.getDay();
        if (dayDST != 0) {
            startDST.setDate( 0 - dayDST)
        } else {
            startDST.setDate(1)
        }
        endDST.setMonth(9);
        endDST.setHours(1);
        endDST.setDate(31);
        dayDST = endDST.getDay();
        endDST.setDate(31 - dayDST);
        var currentTime = new Date()
        currentTime.setMonth(month);
        currentTime.setFullYear(year);
        currentTime.setDate(day);
        currentTime.setHours(hr);
        if (currentTime >= startDST && currentTime < endDST) {
            dst = 1
        }
    }

    if (dst == 1) {
        hr -= -1;
        if (hr >= 24) {
            hr = hr - 24;
            day -= -1;
        }
        
        if (hr < 10) {
            //hr = "0" + hr;
        }
        if (day > monthDays[month]) {
            day = 1;
            if (month == 11) {
                month = 0;
                year -= -1;
            } else {
                month -= -1;
            }
        }
    } 

    // store current offset from system time
    currentTime = new Date(year, month, day, hr, min, sec).getTime();
    glob[region] = Math.round((currentTime - new Date().getTime())/3600000);
}

/* show or hide navigation bar */ 
function toggleNavIndicator(onPage) {
    let navInd = document.querySelector("#nav-indicator");
    let menuIcon = document.querySelector("#menu-icon");
    if (glob['mobile like'] && glob['orientation'] == 'portrait') {
        navInd.style.display = 'none';
        menuIcon.style.display = 'block';
    } else {
        if (glob['landing'] && onPage == 0) {
            navInd.style.display = 'none';
        } else {
            navInd.style.display = 'flex';
        }
    }
    if (!glob['landing'] && !glob['is projects']) {
        navInd.style.display = 'none';
    }
}

/* update highlight */
function updateNavIndicator(direction, index) {
    let indicator = document.querySelector('#nav-indicator');
    let navIndex = index - 1;
    if (navIndex != -1) { // if it exists
        editClass(indicator.children[navIndex], 'current-indicator', '', 'add') ;
        for (let c = 0; c < indicator.children.length; c++) {
            if (c != navIndex) {
                editClass(indicator.children[c], 'current-indicator', '', 'remove');
            }
        }
    }
}

/* show name image on landing else show logo */
function toggleNameImage(pageIndex) {
    let theImage = document.querySelector("#company-name-image"); 
    let theLogo = document.querySelector("#company-logo-wrap"); 
    let duration = 500;
    
    if (glob['is projects']) {   
        theImage.style.opacity = 0;
        theImage.style.transition = "opacity "+duration+"ms";           // projects
        theLogo.style.opacity = 1;
        theLogo.style.transition = "opacity 1s";
    } else if (window.location.href.indexOf('?') != -1 && 
        window.location.href.indexOf('#') == -1 ) {         // standalone eg probono
            theImage.style.opacity = 0;
            theImage.style.transition = "opacity "+duration+"ms"; 
            theLogo.style.opacity = 1;
            theLogo.style.transition = "opacity "+duration+"ms"; 
    } else if (pageIndex == 0) {   
        // landing page
        theImage.style.opacity = 1;
        theImage.style.transition = "opacity "+duration+"ms"; 
        theLogo.style.opacity = 0;
        theLogo.style.transition = "opacity "+duration+"ms"; 
    } else {    
        // other landing page sections
        theImage.style.opacity = 0;
        theImage.style.transition = "opacity "+duration+"ms"; 
        theLogo.style.opacity = 1;
        theLogo.style.transition = "opacity "+duration+"ms"; 
    }
}

/* get clocks first time 
   better performance to store time and increase every second
   than to calc DST time afresh every second 
*/
function doClocks() {
    let clocks = document.querySelectorAll('.locations-clock');
    setTimeout(function() { // needs time for DOM elements to be built else gmtOffset=Nan and no clock shows
        for (let c = 0; c < clocks.length; c++) {
            let theClock = clocks[c];
            let name = theClock.getAttribute('name');
            let gmtOffset = theClock.getAttribute('gmt');
            getClock(parseInt(gmtOffset), name);
        }
    }, 1250)
    setTimeout(function() { // after DOM elements are there
        updateClocks(); 
    }, 1350)
}

/* update clocks on location page */
function updateClocks() {
    let clocks = document.querySelectorAll('.locations-clock');
    for (let c = 0; c < clocks.length; c++) {
        let theClock = clocks[c];
        let name = theClock.getAttribute('name');
        setInterval(function() {
            let sysTime = new Date();
            let hr = sysTime.getHours() + glob[name];
            let min = sysTime.getMinutes();
            let sec = sysTime.getSeconds();
            while (hr > 23) {hr = hr - 24}
            if (hr < 10) { hr = '0' + hr}
            if (min < 10) { min = '0' + min}
            if (sec < 10) { sec = '0' + sec}
            let theTime = hr + ':' + min + ':' + sec;
            if (theClock.textContent == '') { // first time: fade in
                theClock.style.opacity = 0;
                theClock.textContent = theTime;
                setTimeout(function() {
                    theClock.style.opacity = 1;
                    theClock.style.transition = 'opacity 300ms'
                }, 1/2)
            } else {
                theClock.textContent = theTime;
            }
        }, 500);
    }
}

function locations_page() {

    // fields
    // 'short_form_name', 'long_form_name', 'location_desktop_video', 'location_text', "address", 'phone_number', 'contact_email', 'normal_gmt_offset

    function locData(jsonLocs) {
        
        let locations = document.querySelectorAll(".locations-video-wrap");
        var locationsConsole = document.querySelector("#locations-console");

        let locData = []
        for (let loc in jsonLocs) {
            locData.push(jsonLocs[loc]);
        }

        for (let i = 0; i < locations.length; i++) {

            let theLocation = locData[i];
            let wrap = locations[i];

            let vidDiv = wrap.querySelector(".locations-video");
            let nameDiv = wrap.querySelector(".locations-short-name");
            
            // load the video
            let vid = vidDiv.children[0];
            vid.src = theLocation[2]['guid'];

            let shortName = theLocation[0];
            let longName = theLocation[1];
            nameDiv.textContent = shortName;

            let timeDiv = wrap.querySelector(".locations-clock");
            timeDiv.id = shortName + '-clock';
            let gmtOffset = theLocation[7];
            timeDiv.setAttribute('gmt', gmtOffset);
            timeDiv.setAttribute('name', longName.toLowerCase());


            var leftCon, leftCurrent, midCon, midCurrent, rightCon, rightCurrent;
            var nameColor, locSlug, locLongName, locAddress, locPhone, locEmail;

            function setNames() {
                // store current values before listeners
                leftCon = document.querySelector("#locations-console-text-left");
                leftCurrent = leftCon.textContent;
                midCon = document.querySelector("#locations-console-middle");
                midCurrent = midCon.textContent;
                rightCon = document.querySelector("#locations-console-text-right");
                rightCurrent = rightCon.textContent;
                nameColor = nameDiv.style.color;
            }

            if (locationsConsole) {

                if (glob['mobile like'] && glob['orientation'] == 'portrait') { 
                    locLongName = locationsConsole.querySelector(".console-mobile-locations-text");
                    //locSlug = locationsConsole.querySelector(".console-mobile-locations-text");
                    
                    locAddress = locationsConsole.querySelector(".console-mobile-text");
                    locPhone = locationsConsole.querySelector(".console-mobile-supplementary-a");
                    locEmail = locationsConsole.querySelector(".console-mobile-supplementary-b");
                } else {
                    locSlug = locationsConsole.querySelector("#locations-console-middle");
                    locLongName = locationsConsole.querySelector(".locations-long-name");
                    locAddress = locationsConsole.querySelector(".locations-address");
                    locPhone = locationsConsole.querySelector(".locations-phone");
                    locEmail = locationsConsole.querySelector(".locations-email");
                }
            }

            function consoleUpdate() {
                leftCon.style.opacity = 0;
                rightCon.style.opacity = 0;
                locLongName.textContent = longName;
                midCon.textContent = theLocation[3];
                locAddress.innerHTML = theLocation[4];
                locPhone.innerHTML = theLocation[5];
                locEmail.innerHTML = theLocation[6];
                if (glob['mobile like'] && glob['orientation'] == 'portrait') { 
                editClass(locLongName, 'console-mobile-locations-long-name', '', 'add');
                }
                
                editClass(nameDiv, 'locations-name-hover', '', 'add');
                editClass(timeDiv, 'locations-clock-hover', '', 'add');
            }

            function addListeners(e) {
                let events = ['mouseenter', 'touchstart', 'click'];
                for (let ev = 0; ev < events.length; ev++) {
                    e.addEventListener(events[ev], function(e) {
                        vid.autoplay = true;    // safari - only play on click
                        vid.muted = true;       // safari
                        vid.play();             // chrome  - only play on click
                        if (locationsConsole) consoleUpdate();
                    }, {passive: true});
                }
            }
            setNames();
            let theDivs = [vidDiv, nameDiv, timeDiv];
            Array.prototype.forEach.call(theDivs, addListeners);
        }
    }

    // call function
    locData(jsonLocs);
}

function clients_page() {

    function clientData(resp) {    
        // clients fields
        // 'client_name', 'client_industry', 'client_slug', 'client_logo', "client_highlight_image"    
        let i = 0;
        for (let client in resp) { 
            clientCells[i].setAttribute('name', resp[client][0]);
            clientCells[i].setAttribute('industry', resp[client][1]);
            clientCells[i].setAttribute('slug', resp[client][2]);
            clientCells[i].setAttribute('img', resp[client][3]['guid']);
            clientCells[i].setAttribute('highlight', resp[client][4]['guid']);
            let eImg = clientCells[i].getElementsByTagName('img')[0];
            eImg.src = clientCells[i].getAttribute('img');
            i++;
        }
    }

    let clientsConsole = document.querySelector("#clients-console");
    var clientCells = document.querySelectorAll(".client-cell");

    // get the data if not's there already
    let resp = jsonClients;
    clientData(resp);

    function clientHoverPage(e) {
        var eImg = e.getElementsByTagName('img')[0]
        e.addEventListener('mouseenter', function () { 
            eImg.src = e.getAttribute('highlight');
        }, {passive: true});
        e.addEventListener('mouseleave', function () {      
            eImg.src = e.getAttribute('img');
        }, {passive: true});
    }

    let enterEvents = ['mouseenter', 'click', 'touchstart']; 
    function clientHoverConsole(e, event) {
        for (let ent = 0; ent < enterEvents.length; ent ++) {
            e.addEventListener(enterEvents[ent], function () { 
                leftCol.textContent = "";
                let normText = document.querySelector(".console-mobile-text-clients");
                normText.style.display = 'none';
                if (glob['mobile like'] && glob['orientation'] == 'portrait') { 
                    let theConsole = glob['current console'];
                    let mobConsTitle = theConsole.querySelector(".console-mobile-title");
                    let mobConsIndustry = theConsole.querySelector(".console-mobile-secondary");
                    let mobConsSlug = theConsole.querySelector(".console-mobile-supplementary-a");
                    mobConsTitle.textContent = e.getAttribute('name');
                    mobConsIndustry.textContent = e.getAttribute('industry').toUpperCase();
                    mobConsSlug.textContent = e.getAttribute('slug');
                } else {
                    name.textContent = e.getAttribute('name');
                    editClass(name,'page-clients-left','','remove');
                    industry.textContent = e.getAttribute('industry').toUpperCase();
                    slug.textContent = e.getAttribute('slug');
                }
            }, {passive: true});
        }

        e.addEventListener('mouseleave', function () {      
            leftCol.textContent = savedLeftCol;
            rightCol.textContent = savedRightCol;
            industry.textContent = "";
            slug.textContent = '';
            midCol.textContent = savedMidCol;
            editClass(leftCol,'page-clients-left','','add');
        }, {passive: true});
    }

    Array.prototype.forEach.call(clientCells, clientHoverPage)
    if (clientsConsole) {
        var slug = document.querySelector(".clients-general-slug");
        var industry = document.querySelector(".client-industry");
        var name = document.querySelector(".client-name");
        var leftCol = document.querySelector(".page-clients-left");
        var savedLeftCol = leftCol.textContent;
        var midCol = document.querySelector(".clients-general-slug");
        var savedMidCol = midCol.textContent;
        var rightCol = document.querySelector(".console-col-right");
        var savedRightCol = rightCol.textContent;
        Array.prototype.forEach.call(clientCells, clientHoverConsole)
    }
}

function buildTeamPage() {
    if (!glob['team page done']) { // only do once
        team_page();
        glob['team page done'] = true;
    } else {
        rebuildTeamConsole();
    }
}

function buildLocationsPage() {
    if (!glob['clocks done']) {
        doClocks();
        locations_page();
        glob['clocks done'] = true;
    }
} 

function buildClientsPage() {
    if (!glob['clients page done']) { // only do once
        clients_page();
        glob['clients page done'] = true;
    }
}

function hideContactConsole() {
    // on mobile, because contact console takes over whole page
    // it takes over focus of top section of other pages
    // correct this

    if ((glob['mobile like'] || glob['tablet like']) && glob['orientation'] == 'portrait') {
        let pages = glob['pages'];
        let thePage = pages[isOnPage()];
        if (thePage.id != 'page-contact') {
            let contactConsole = document.querySelector("#contact-console");
            if (contactConsole) {
                contactConsole.style.zIndex = -10;
            }
        }
    }
}

/* jobs after a page change */
function updatePage(direction, cpindex, thePage, prevPage, theConsole, prevConsole, reload=false) {

    let pages = glob['pages'];
    let consoles = glob['consoles'];
    let currentConsole = consoles[cpindex];

    glob['current page index'] = cpindex;
    glob['current page'] = pages[cpindex];
    glob['current console'] = currentConsole;
    
    // assign url else reloads and goes back to landing
    if (window.location.href.indexOf('projects') == -1) {
        window.location.href = glob['base href'] + "/#"+glob['current page'].id
    } else {
        glob['current page index'] = cpindex;
    }

    // build location and reload pages
    if (thePage.id == "page-locations") { 
        buildLocationsPage();
    } else if (thePage.id == "page-team") {
        buildTeamPage();
    } else if (thePage.id == "page-clients") {
        buildClientsPage();
    }  
    
    if (thePage.id != "page-contact") {

        hideContactConsole();
    }

    // logos, consoles, console button
    toggleNameImage(cpindex);
    toggleSwipeButton();
    setSwipeButton();
    setConsoleButton(theConsole);
    hideConsole(prevConsole);
    
    // now show current console
    if (theConsole) {

        if(direction == 'up' && (cpindex = pages.length - 1)) {
            //theConsole.style.transform = "translate3d(" + 0 + ", " + window.innerHeight + "px, 0)";
        }
        showConsole(theConsole);
    } 

    // start and stop videos if page is in or out of view
    if (thePage) {
        if (glob['pages with videos'].indexOf(thePage) != -1 || glob['pages with vimeos'].indexOf(thePage) != -1) {
            if (thePage.id != 'page-locations') { // bcos these play on clicks/hover 
                playVideo(thePage);
            }
        }
    }
    if (prevPage) {
        if (glob['pages with videos'].indexOf(prevPage) != -1 || glob['pages with vimeos'].indexOf(thePage) != -1) {
           pauseVideo(prevPage)
        }
    }

    // set flags and do locks
    glob['animating'] = false;
    glob['threshold catch'] = false;
    if (glob['is mobile']) { // avoid mobile scrolling
        gainLock();
    } 
    else {
       releaseLock();
        
    }
}

/* swipe page - for landing page only */
function swipePage(reload, index, direction, fromMenu=false, fromMenuIndex=0) {

    let pages = glob['pages'];
    let consoles = glob['consoles'];
    let move = 0;
    let moveTo = 0;
    let firstLanding;

    glob['animating'] = true;

    // easings
    var easeOutInQuint = function (t) { return t<.5 ? 16*t*t*t*t*t : 1+16*(--t)*t*t*t*t };
    var easeInOutQuart = function (t) { return t<.5 ? 8*t*t*t*t : 1-8*(--t)*t*t*t };
    var easeOutCubic = function (t) { return (--t)*t*t+1 };
    var easeInOutCubic = function (t) { return t<.5 ? 4*t*t*t : (t-1)*(2*t-2)*(2*t-2)+1 }

    // set page id and set index so new pages appear over top of previous ones
    let thePage, prevPage, prevIndex, theConsole, prevConsole;

    if (fromMenu) {
        index = index;
        prevIndex = fromMenuIndex
    } else {
        if (direction == 'down') {      
            if (index == pages.length - 1)  {
                prevIndex = index;
                index = 0;
            } else {
                prevIndex = index;
                index = Math.min(index + 1, pages.length - 1);
            }    
        } else if (direction == 'up') {
            if (index == 0)  {
                prevIndex = 0;
                index = pages.length - 1;
            } else {
                prevIndex = index; 
                index = Math.max(0, index - 1);
            }
        }
    }

    thePage = glob['pages'][index];
    prevPage = glob['pages'][prevIndex];

    theConsole = consoles[index];
    prevConsole =  consoles[prevIndex];
    
    var starttime;

    let isLastPage = false;
    let wasLastPage = false;
    if (index == pages.length - 1) isLastPage = true;
    if (prevIndex == pages.length - 1) wasLastPage = true;

    var winHeight;
    if (!glob['is mobile']) {
        winHeight = window.innerHeight; // recalculate as window may have been resized
    } else {
        setMobileDimensions();
        if (glob['orientation'] == 'portrait') {
            winHeight = glob['mobile long end'];
        } else {
            winHeight = glob['mobile short end'];
        }
    }
    
    function translate (thePage, moveTo, index, direction) {
        thePage.style.transform = "translate3d(" + 0 + ", " + moveTo + "px, 0)";
    }

    let notThere = false;
    let s = 0;

    // build trajectory points
    let numPoints = 40;
    let points = [];
    let thePoint;
    for (let n = 1; n < numPoints + 1; n++) {
        thePoint = 1/numPoints * n
        points.push(thePoint)
    }
    let copied = points.slice(0);
    let slowerMarks = 25;
    for (let m = 0; m < slowerMarks - 2 ; m++) {
        let toInsert = (copied[numPoints - m] + copied[numPoints - m + 1]) / 2
        if (!isNaN(toInsert)) {
            points.splice((numPoints - m + 1), 0, (copied[numPoints - m] + copied[numPoints - m + 1]) / 2);
        }
    }

    let moved = 0;

    // now show current console
    if (theConsole && !isLastPage) {
        if (direction == 'down') {
            showConsole(theConsole);
        }
    }

    resetPageZ(direction, index, prevIndex)
    resetPageTransforms(false, direction, index, prevIndex, false)

    function swipeIt(timestamp, index, distance, direction){  
    
        // calc move differential
        let t = points[s]
        s++
        move = easeOutInQuint(t) * distance

        if (distance - move < 1) move = distance; 

        if (!glob['is mobile']) {
            releaseLock(); 
        }

        // get where to slide to
        if (reload) moveTo += winHeight;
        moveTo = (direction == 'down') ? distance - move : move - distance;
        
        if (direction == 'down') {
            translate(thePage, moveTo, index, direction)
            if (glob['is mobile']) {
                if (isLastPage) {
                    translate(theConsole, moveTo, index, direction)
                } else if (wasLastPage) { // stack last console behind first page
                    prevConsole.style.zIndex = thePage.style.zIndex - 1;
                }
            }
        } else {
            translate(thePage, moveTo, index, direction);
            if (glob['is mobile']) {
                if (isLastPage) {
                    translate(theConsole, moveTo, index, direction)
                } else if (wasLastPage) {
                    prevConsole.style.zIndex = thePage.style.zIndex - 1;
                }
            }
        }
            
        // loop if not fully swiped else finish
        if (Math.round(Math.abs(move)) < distance ) {
            timestamp = performance.now();   
            window.requestAnimationFrame(function(){
                swipeIt(timestamp, index, distance, direction);
            }, 1/60)
        } else {   
            updatePage(direction, index, thePage, prevPage, theConsole, prevConsole, false);
        }
    }
    
    // request swipe
    let timestamp = performance.now();
    starttime = performance.now();
    updateNavIndicator(direction, index);
    toggleNavIndicator(index);

    for (let p = 0; p < pages.length; p++) {
        if (pages[p].style.position = 'fixed') {
            pages[p].style.position = ''
        }
    }
   
    let distance = winHeight;

    // move page into pre-position - already ok if swiping 'up' to the top
    if (direction == 'down') {
        // if last page, for mobiles console is 100% so move into pre-position and ensure will be visible 
        if (isLastPage && glob['is mobile']) {
            if (theConsole) {
                theConsole.style.transform = "translate3d(" + 0 + ", " + winHeight + "px, 0)";
            }
            if (theConsole) showConsole(theConsole);
        }
    } else {

        if (isLastPage && glob['is mobile']) {
            if (theConsole) {
                theConsole.style.transform = "translate3d(" + 0 + ", -" + winHeight + "px, 0)";
                theConsole.style.transition = 'transform 0s';
            }
            showConsole(theConsole);
        }
    }

    swipeIt(timestamp, index, distance, direction);
}


/* detect move by mouse or touch */
function swipeDetect() {

    // no swiping on projects
    if (glob['is projects']) { return false;}

    let cpindex;
    
    // lock screen from scrolling - important!!
    document.body.style.overflow = 'hidden';
    document.addEventListener('mousewheel', preventDefault, {passive: false}); 

    //FF doesn't recognize mousewheel as of FF3.x, use DOMMouseScroll
    var mousewheelevt=(/Firefox/i.test(navigator.userAgent))? "DOMMouseScroll" : "mousewheel";

    // event listener to window or even document.body
    // mousewheels and trackpads
    let goSwipe;
    let startedScroll = 0;
    let threshold = 5;
    if (mousewheelevt == "DOMMouseScroll") {
        threshold = 1; 
    }


    window.addEventListener(mousewheelevt, function(e){            
        let yDelta = e.deltaY
        if (mousewheelevt == "DOMMouseScroll") {
            yDelta = e.detail;
        }
        if ('is mobile') {
            e.preventDefault();
            e.stopImmediatePropagation();
        }

        if (Math.abs(yDelta) >= threshold && !glob['threshold catch']) {
            glob['threshold catch'] = true;
            document.body.style.overflow = 'hidden';
            document.addEventListener('mousewheel', preventDefault, {passive: false}); 
            cpindex = isOnPage();
        
            clearTimeout(goSwipe);
            goSwipe = setTimeout(function() {
                let newTime = new Date().getTime();
                let scrollInterval = 500;
                if  (!glob['animating'] && (newTime - startedScroll) > scrollInterval) {  
                    glob['animating'] = true; // catch early to stop further wheel action
                    startedScroll = newTime;
                    let direction = yDelta > 0 ? 'down' : 'up';          
                    gainLock();
                    if (direction == 'down' ||
                        direction == 'up') {
                        swipePage(false, cpindex, direction);
                    } else {
                        glob['animating'] = false;
                        releaseLock();
                    }
                } 
            }, 100)
        }
    },  {passive: false})

    // mobile touch
    var startX;
    var startY;
    var distX;
    var distY;
    threshold = 20; //min distance to be considered swipe - nb much higher than wheel and must account for diagonals
    let allowedTime = 100; // minimum time allowed to travel that distance
    let elapsedTime;
    let startTime;
    var direction;
 
    /* mobile touch check for swipe and swipe */
    function mobileSwipe(e) {

        var touchobj = e.changedTouches[0];
        distX = touchobj.pageX - startX // get horizontal dist traveled by finger while in contact with surface
        distY = touchobj.pageY - startY // get vertical dist traveled by finger while in contact with surface
        elapsedTime = new Date().getTime() - startTime // get time elapsed

        if (Math.abs(distY) >= threshold){ // condition for vertical swipe met
            direction = (distY > 0) ? 'up' : 'down' // if dist traveled is negative, it indicates up swipe
        
        } else if (Math.abs(distX) >= threshold){ // condition for horizontal swipe met
            direction = (distX < 0) ? 'left' : 'right' // if dist traveled is negative, it indicates left swipe
        
        } else {
            let touched = touchobj.target.getAttribute('class');
                if (touched.indexOf('indicator-col') != -1) {
                    direction = 'down'
            }
        }

        if (!glob['animating'] && direction != undefined) {  
            if (Math.abs(distY) >= threshold || elapsedTime >= allowedTime) {
                cpindex = isOnPage(); 
                let cpid = glob['pages'][cpindex].id
                if (direction == 'down' || direction == 'up') {
                    glob['animating'] = true; // catch early to stop further wheel action
                    swipePage(false, cpindex, direction);

                } else if (direction == 'right' || direction == 'left') {
                    gainLock();
                    return false;
                } else {
                    glob['animating'] = false;
                    gainLock();
                }
            } else {
                gainLock();
                glob['animating'] = false;
            }
        } else {
            gainLock();
        }
    }

    // need to allow default action on buttons, icons etc
    var allowed = ['company-logo', ] 
    var touchobj;


    window.addEventListener('touchstart', function(e){

        cpindex = isOnPage();
        touchobj = e.changedTouches[0];

        if (glob['is mobile'] && glob['pages'][cpindex].id == 'page-work') {
            e.preventDefault();
            e.stopImmediatePropagation();
        }

        document.body.style.overflow = 'hidden'; 
        gainLock();
        window.addEventListener('mousewheel', preventDefault, {passive: false});

        direction = undefined;
        startX = touchobj.pageX
        startY = touchobj.pageY
        startTime = new Date().getTime() // record time when finger first makes contact with surface
    },  {passive: false})

    window.addEventListener('touchmove', function(e){
        e.preventDefault();
        e.stopImmediatePropagation();
        document.body.style.overflow = 'hidden';   
        window.addEventListener('mousewheel', preventDefault, {passive: false});    
        gainLock();
        mobileSwipe(e);
    },  {passive: false})

    window.addEventListener('touchend', function(e){
        e.preventDefault();
        e.stopImmediatePropagation();
        document.body.style.overflow = 'hidden';   
        window.addEventListener('mousewheel', preventDefault, {passive: false});
        gainLock();
  
        if (allowed.indexOf(touchobj['target'].id) == -1) {
            mobileSwipe(e);
        }
    },  {passive: false})

}

function resizeClientsPage() {
    let thePage = document.querySelector("#clients-visuals");
    thePage.style.padding = "7% 12.5% 0 12.5%"
}

function resizePages() {
    // because page-wraps are relative; resizing causes pages to restack vertically
    // this sets all positions to fixed and hides non-current pages
    let thePage = glob['pages'][glob['current page index']];
    let pages =  glob['pages']; 
    // set a time to check if window area has changed indicating user still resizing
            for (let p = 0; p < pages.length; p++) {
                if (pages[p].id != thePage.id) {
                    pages[p].style.position = 'fixed';
                    pages[p].style.zIndex = -20;
                }
            }
    // if after first resize user swipes then this keeps subsequent resizings working
    thePage.style.transform = 'translate3d(0, 0, 0)';
}

/* rescale images during resizing to fill up window */ 
function resizeWpImages() {
    let thePage = glob['pages'][glob['current page index']];
    let images = thePage.querySelectorAll('.wp-post-image');
    let deviceArea = screen.width * screen.height;
    let curArea = window.innerWidth * window.innerHeight;
    let ratio = deviceArea / curArea * (1 + (deviceArea / curArea - 1)/2);
    if (images) {
        for (let i = 0; i < images.length; i++) {
            images[i].style.transform = 'scale('+ratio+')';
        }
    }
}

/* for desktop screen resizes */
function checkIfMobileLike() {
    // not real mobile values which are <400
    // but for desktop miminal resizes which are > 400 
    let isMobileLike = false;
    if (window.innerWidth <= glob['mobile limit'] * 1.5) {
        isMobileLike = true;
    }
    return isMobileLike;
}

/* resize jobs */
function resizing() {
    document.body.style.overflowX = 'hidden';
    glob['orientation'] = getOrientation();
    deviceLike(); // updates if mobile/tablet like
    if (!glob['is mobile']) {
        resizeMenuPage();
        if (!glob['is projects']) {
            resizeClientsPage();
            resizePages();
        }
        resizeWpImages();
    }
    // because mobile view portrait takes up 100%
    hideContactConsole();
}


function getOrientation() {
    let orientation;
    (window.innerHeight > window.innerWidth) ? orientation = 'portrait': orientation = 'landscape';
    return orientation
}


/* stuff eg images/videos to change post orientation change */
function loadOrientationAssets(onPage, fromChange=false) {

    let pages = glob['pages']; 
    // nb. on orientation change getOrientation actually returns the old one
    let theOrientation = getOrientation();
    // but on reload or from load orientation is the current one 
    // we'll reset theOrientation to be the 'other' one
    if (!fromChange) {
        glob['orientation'] = theOrientation;
        (theOrientation == 'landscape') ? theOrientation = 'portrait' : theOrientation = 'landscape'; 
    }

    if (glob['is mobile']) {
        let thePage = pages[onPage];
        let landingPage = pages[0];
        let vimeo = thePage.querySelector("iframe");
        let video = thePage.querySelector(".post-video");
        let image = thePage.querySelector(".post-image");
        
        // we always swap the landing page
        function doLanding(orientation) {
            if (orientation == 'landscape') { // LANDSCAPE ---> PORTRAIT
                let vimeoL = landingPage.querySelector("iframe");
                let mobileL = (vimeoL) ? 'mobile vimeo' : 'mobile video';
                let landPost = (landingPage.querySelector("iframe") || landingPage.querySelector(".post-video"));
                landPost.src = mobileObjects[landingPage.id][mobileL];
            } else { // PORTRAIT --> LANDSCAPE
                let vimeoL = landingPage.querySelector("iframe");
                let mobileL = (vimeoL) ? 'post vimeo' : 'post video';
                let landPost = (landingPage.querySelector("iframe") || landingPage.querySelector(".post-video"));
                landPost.src = mobileObjects[landingPage.id][mobileL];
            }
        }
        if (thePage.id != landingPage.id) doLanding(theOrientation);
    
        // everything else we adjust the style
        if (vimeo || video || image) {
            let posted, post, mobile;
            if (vimeo || video) {
                posted = (vimeo) ? 'post vimeo' : 'post video';
                mobile = (vimeo) ? 'mobile vimeo' : 'mobile video';
                post = (vimeo) ? vimeo : video;
            }

            if (theOrientation == 'landscape') { // LANDSCAPE ---> PORTRAIT
                if (post) {
                    if (glob['mobile like']) {
                        if (glob['loaded orientation'] == 'landscape') {
                            if (mobileObjects[thePage.id][mobile].indexOf('http') != -1) {
                                post.src = mobileObjects[thePage.id][mobile];
                            } else {
                                post.style.transform = 'scale(3.25)';
                            }
                        } else {
                            if (mobileObjects[thePage.id][mobile].indexOf('http') != -1) {
                                post.src = mobileObjects[thePage.id][mobile];
                            } else {
                                post.style.transform = '';
                            }
                        }
                       
                    } else if (glob['tablet like'] ) {
                        if (glob['loaded orientation'] == 'landscape') {
                            post.style.transform = 'scale(1.75) translateY(-6%)';
                        } else {
                            post.style.transform = '';
                        }
                    }
                }
                if (image) {
                    image.setAttribute('src', mobileObjects[thePage.id]['mobile image']);
                }         

            } else { // PORTRAIT ---> LANDSCAPE
                if (post) {
                    if (glob['mobile like']) {
                        if (glob['loaded orientation'] == 'portrait') {
                            if (mobileObjects[thePage.id][mobile].indexOf('http') != -1) {
                                post.src = mobileObjects[thePage.id][posted];
                            } else {
                                // do nothing;
                            }
                        } else {
                            if (mobileObjects[thePage.id][mobile].indexOf('http') != -1) {
                                post.src = mobileObjects[thePage.id][posted];
                            } else {
                                post.style.transform = '';
                            }
                        }
                    } else if (glob['tablet like'] ) {
                        if (glob['loaded orientation'] == 'portrait') {
                            post.style.transform = 'scale(1.8) translateY(15%)';
                        } else {
                            post.style.transform = '';
                        } 
                    }
                }
                if (image) {
                    image.setAttribute('src', mobileObjects[thePage.id]['post image']);
                }
            }
        }

        // because mobile portrait consoles are so different
        // we have to rebuild this with every orientation change
        if (thePage.id == 'page-team' && glob['is mobile']) {
            let selected = glob['member selected'];            
            // show member details
            if (selected) {
                teamReveal(selected, true);
          
                // slide to right position - short timeout to pick the new orientation
                // as the old one is still immediately active 
                setTimeout(function() {
                    let row = document.querySelector('#team-row');
                    let rightSwipeBtn = document.querySelector("#teamswipeRight")
                    let par = selected.parentElement;
                    let idx = parseInt(par.getAttribute('index'));
                    let memWidth = parseFloat(window.getComputedStyle(par).width);
                    let memMargin = parseFloat(window.getComputedStyle(par).marginLeft);
                    let memPosition = (memWidth + memMargin) * idx
                    row.style.transform = 'translate3d(-' + memPosition + 'px, 0, 0)';
                    if (idx > 0) { // because there's at least one person to the left
                        rightSwipeBtn.style.display = 'block';
                    }
                }, 500);
            }
        }  
    }

    // set orientation
    (theOrientation == 'landscape') ? glob['orientation'] = 'portrait' : glob['orientation'] = 'landscape';

    // update
    if (fromChange) setSwipeButton();
    updateNavIndicator('down', onPage);
    toggleNavIndicator(onPage); 
}

function checkIfMobile() {
    let isMobile = false;
    if(    navigator.userAgent.match(/Android/i)
        || navigator.userAgent.match(/webOS/i)
        || navigator.userAgent.match(/iPhone/i)
        || navigator.userAgent.match(/iPad/i)
        || navigator.userAgent.match(/iPod/i)
        || navigator.userAgent.match(/BlackBerry/i)
        || navigator.userAgent.match(/Windows Phone/i)) {
        isMobile = true;
    }
    return isMobile;
}

/* find browser */
function browserIs_() {
    let browser = ''
        if((navigator.userAgent.indexOf("Opera") || navigator.userAgent.indexOf('OPR')) != -1 ) 
       {
           browser = 'Opera';
       }
       else if(navigator.userAgent.indexOf("Chrome") != -1 )
       {
        browser = 'Chrome';
       }
       else if(navigator.userAgent.indexOf("Safari") != -1)
       {
        browser = 'Safari';
       }
       else if(navigator.userAgent.indexOf("Firefox") != -1 ) 
       {
        browser = 'Firefox';
       }
       else if((navigator.userAgent.indexOf("MSIE") != -1 ) || (!!document.documentMode == true )) //IF IE > 10
       {
        browser = 'IE';
       }  
    return browser
}

/* retrieve page id from url */
function getUrlPageIndex() {
    let pageIndex = null;
    let pages = glob['pages'];
    let href = window.location.href;
    if (href.indexOf("#page") != -1) {
        let pageId = href.slice(href.indexOf("#page-"));
        let thePage = document.querySelector(pageId);
        pageIndex = pages.indexOf(thePage);
    }
    return pageIndex;
}

/* build pages that need work doing */
function buildPages() {
    try {buildTeamPage()} catch(e) {}
    try {buildClientsPage()} catch(e) {}
    try {buildLocationsPage()} catch(e) {}
    if (!glob['gallery done']) {
        projectsGallery();
        glob['gallery done'] = true; 
    } 
}

/* open full screen on orientation change */
function openFullscreen() {
    var elem = document.documentElement;
    if (elem.requestFullscreen) {
      elem.requestFullscreen();
    } else if (elem.mozRequestFullScreen) { /* Firefox */
      elem.mozRequestFullScreen();
    } else if (elem.webkitRequestFullscreen) { /* Chrome, Safari and Opera */
      elem.webkitRequestFullscreen();
    } else if (elem.msRequestFullscreen) { /* IE/Edge */
      elem.msRequestFullscreen();
    }
}

function getPageIndex(href) {
    let index = 0;
    let pages = glob['pages'];
    let name;
    let pos = href.indexOf("#page");
    if (pos != -1) {
        name = href.slice(pos+1);
        for (let p = 0; p < pages.length; p++) {
            if (name == pages[p].id) {
                index = p;
                break;
            }
        }
    }
    return index
}

window.addEventListener('DOMContentLoaded',onLoad) // main load event

function onLoad() {

    let href = window.location.href;
    let fromProjNav = false;
    if (href.indexOf('autoplay') != -1) return false;
   
    // set initial variables and elements
    setScreenVariables();               // set screen variables
    gatherPagesConsoles();              // get pages and consoles

    // onPage but first in case using nav indcator from projects
    let onPage = 0; //default
    let navPos = href.indexOf("#nav-");
    if (navPos != -1) {
        onPage = parseInt(href.slice(navPos+5));
        fromProjNav = true;
    } else {
        onPage = isOnPage();
    }

    onPage = homeIconPageReset(onPage); // reset if home icon clicked
    resetPageZ('down', onPage, onPage);
    toggleNameImage(onPage);            // hide/show name image 
    toggleConsole();
    storeConsoleButtons();
    openCloseMenu();
    navIndicator();
    toggleNavIndicator(onPage);
    let pages =  glob['pages'];
    glob['current page index'] = onPage;
    glob['current page'] = pages[onPage];

    // set lock so site functions can be initialized else if
    // user starts scrolling/swiping - risk js swipe function fails
    // also critical variables may not be in place for js functions to work
    if (pages.length > 0 && !glob['is projects']) {
        document.body.style.overflow = 'hidden';
        document.addEventListener('mousewheel', preventDefault, {passive: false}); 
        gainLock();
    } else {
        releaseLock();
    }

    // housekeeping for orientation change
    if (glob['landing']) {
        window.onorientationchange = function() { 
            let nowOnPage = isOnPage();
            glob['orientation change'] = true;
            loadOrientationAssets(nowOnPage, true);
            openFullscreen(); // nb only works on user gesture eg orientation change
        };
    }

    /* do below if not standalone pages - privacy, pro-bono form */
    if (pages.length > 0 && !glob['is projects']) {

        // load page and console
        let reload = false;
        let href = window.location.href;
        if (getPageIndex(href) == onPage) reload = true;
       
        let passHref = null;

        if (fromProjNav) {
            // we'll pass the href from here
            passHref = glob['base href'] + '/#' + pages[onPage].id;
        }
        loadPage(reload, onPage, passHref);
        
        let currentConsole = glob['consoles'][onPage];
        setConsoleButton(currentConsole)
        setConsoles(currentConsole);
        swipeDetect();
        buildPages();
        swipeButtons();
        setSwipeButton();
        
        if (pages[onPage].id != 'page-location') {
            hideContactConsole(); 
        }

    } else if (glob['is projects']) {
        glob['projects data'] = jsonWork;
        toggleSwipeButton();
        projectsScrolling(onPage);
   
    } else { // for probono/privacy
        document.querySelector('#console-button-wrap').style.display = 'none';
        toggleSwipeButton();
        toggleNavIndicator();
    }

    // release lock if not mobile/tablet
    // need this for mousewheel/trackpads to be able to swipe
    if (!glob['is mobile']) {
        releaseLock();
    }
    // jobs to deal with window resizing
    window.addEventListener("resize", resizing);

}

window.addEventListener('load',afterLoad) // after everything has loaded

function afterLoad() {

    var done = []; // track page videos/vimeos with mute/unmutes
    getPagesWithVideos();
    getPagesWithVimeos();
    doVideos();
    doUnmutes();

    function doVideos () {
        let pagesVid = glob['pages with videos'];
        let vids;
        for (let p = 0; p < pagesVid.length; p++) {
            vids = pagesVid[p].querySelectorAll('video');
            for (let v = 0; v < vids.length; v++) {
                let vid = vids[v]
                if (vid.getAttribute('preload') == 'none' || vid.getAttribute('preload') == 'metadata') {
                    fetch(vid.src)
                        .then(function(response) {
                            if (pagesVid[p].id != 'page-locations') { // locations play on click
                                vid.autoplay = true;    // safari
                                vid.load();
                            }
                            vid.muted = true;       // safari
                            vid.load();             // chrome
                            // Do stuff with the response
                    })
                        .catch(function(error) {
                    });
                }
            }
        }
    }

    function unmuteVid(page) {
        let videos = page.querySelectorAll(".post-video");
        let vimeos = page.querySelectorAll(".post-vimeo");
        let media = [videos, vimeos];
        
        for (let m = 0; m < media.length; m++ ) {
            let med = media[m];
            let video, vimeo
            
            if (med.length == 0) continue;

            for (let v = 0; v < med.length; v++) {
                if (med[v].getAttribute('class').indexOf('video') != -1) {
                    video = med[v]
                    if (!video || video.style.display == 'none') continue;
                } else {
                    vimeo = med[v]
                    if (!vimeo || vimeo.style.display == 'none') continue;
                }

                if (vimeo) 
                    try {var player = new Vimeo.Player(vimeo);
                } catch(e) {}

                if (video || vimeo) {
                    let events = ['click', 'touchend']
                    let muteButton = page.querySelector(".unmute-button");
                    if (muteButton) {
                        for (let e = 0; e < events.length; e++) {  
                            let _done = page.id+events[e];
                            if (done.indexOf(_done) != -1) continue;
                            done.push(page.id+events[e])
                            muteButton.addEventListener(events[e], function() {             
                                if (muteButton.textContent == 'UNMUTE') {  
                                    if (player) player.setVolume(1);
                                    if (video) video.muted = false;
                                    muteButton.textContent = 'MUTE';
                                } else {
                                    if (player) player.setVolume(0);
                                    if (video) video.muted = true;
                                    muteButton.textContent = 'UNMUTE';
                                }
                            }, {passive: true});
                        }
                    }
                }
            }
        }
    }

    function doUnmutes () {
        let pagesVid = glob['pages with videos'];
        let pagesVim = glob['pages with vimeos'];
        let pagesV = pagesVid.concat(pagesVim);
        pagesV = new Set(pagesV);   // to set to remove duplicated pages
        pagesV = [...pagesV];       // back to array
        for (let p = 0; p < pagesV.length; p++) {
            unmuteVid(pagesV[p]);
        }
    }
}
