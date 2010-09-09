var isOpera = navigator.userAgent.indexOf("Opera") > -1;
var isIE = navigator.userAgent.indexOf("MSIE") > 1 && !isOpera;
var isMoz = navigator.userAgent.indexOf("Mozilla/5.") == 0 && !isOpera;

var invisClass = "invisible";
function toggleDisplay(id) {
	toggleClass(id,invisClass)
}

function toggleClass(id,className,cookie) {
	var classTest = new RegExp(className, "gi");
	var me = document.getElementById(id);
	if (me.className.match(classTest)) {
		me.className = me.className.replace(classTest, "");
		if (cookie) setCookie(id+"."+className,'0');
	} else {
		me.className += " " + className;
		if (cookie) setCookie(id+"."+className,'1');
	}
	me.className = normalizeString(me.className);
}

function getStyleSheets(id, className)
{
	var linkElements = document.getElementsByTagName("link");
	var list = new Array();
	var i = 0;
	for(var j=0; (sheet = linkElements[j]); j++) {
		if(sheet.getAttribute("rel").indexOf("style") != -1) {
			styleId = sheet.getAttribute('id')
			styleClass = sheet.getAttribute('class')
			if((!id || styleId == id+'-'+className) && (!className || (styleClass && styleClass.match(RegExp("\\b"+className+"\\b"))))) {
				list[i] = sheet
				i++;
			}
		}
	}
	list.length = i

	return list;
}

function activeStyleSheets(id,className) {
	var sheets = getStyleSheets(id,className);
	var a = true;
	for(var i=0; i < sheets.length; i++) {
		sheets[i].rel = 'stylesheet';
		a = sheets[i].disabled = false;
	}
	return !a;
}

function disableStyleSheets(id,className) {
	var sheets = getStyleSheets(id,className);
	var a = false;
	for(var i=0; i < sheets.length; i++) {
		a = sheets[i].disabled = true;
	}
	return a;
}

function switchStyleSheets(id,className) {
	var ret = false;
	if(className) { ret = (disableStyleSheets(null,className) || ret); }
	if(id) { ret = (activeStyleSheets(id,className) || ret); }
	setCookie(className+'-sheet',id);
	return ret;
}

function toggleList(item) {
	parentNode = item.parentNode;
	if(parentNode.tagName == 'LI') {
		switchClass(parentNode,'left-on','left-off');
		switchClass(parentNode,'right-on','right-off');
		siblings = parentNode.parentNode.childNodes;
		
		for(var i = 0; (sibling = siblings[i]); i++) {
			if(sibling != parentNode && sibling.tagName == 'LI') {
				switchClass(sibling,'left-off','left-on');
				switchClass(sibling,'right-off','right-on');
			}
		}
	}
}

function switchClass(item,newClass,oldClass) {
	if(oldClass) {
		item.className = item.className.replace(RegExp("\\b"+oldClass+"\\b"), newClass);
	}
}


//-----------------------------------------------------------------------------
// sortTable(id, col, rev)
//
//  id  - ID of the TABLE, TBODY, THEAD or TFOOT element to be sorted.
//  col - Index of the column to sort, 0 = first column, 1 = second column,
//        etc.
//  rev - If true, the column is sorted in reverse (descending) order
//        initially.
//
//-----------------------------------------------------------------------------
function sortTable(id, col, rev, sorted) {
	// get the table or table section to sort.
	var tblEl = document.getElementById(id);

	// the first time this function is called for a given table, set up an
	// array of reverse sort flags.
	if (tblEl.reverseSort == null) {
		tblEl.reverseSort = new Array();
		tblEl.lastColumn = -1;
	}
	if (tblEl.reverseSort[col] == null && sorted) {
		tblEl.lastColumn = col;
		tblEl.reverseSort[col] = (rev == sorted)
	}

	// if this column was the last one sorted, reverse its sort direction.
	if (col == tblEl.lastColumn)
		tblEl.reverseSort[col] = !tblEl.reverseSort[col];
	else
		tblEl.reverseSort[col] = rev
	// remember this column as the last one sorted.
	tblEl.lastColumn = col;

	// set sorting order
	reverseSort = tblEl.reverseSort[col];

	// Set the table display style to "none" - necessary for Netscape 6 
	// browsers.
	var oldDsply = tblEl.style.display;
	tblEl.style.display = "none";

// 	if(tblEl.rows.length>800)
// 		return true;

	var i;
	if (isIE) {
		/* old junk sort, good enough for IE */
		var tmpEl;
		var j;
		var minVal, minIdx;
		var testVal;
		var cmp;
	
		for (i = 0; i < tblEl.rows.length - 1; i++) {
			// Assume the current row has the minimum value.
			minIdx = i;
			minVal = getTextValue(tblEl.rows[i].cells[col]);

			// Search the rows that follow the current one for a smaller value.
			for (j = i + 1; j < tblEl.rows.length; j++) {
				testVal = getTextValue(tblEl.rows[j].cells[col]);
				cmp = compareValues(minVal, testVal);
				// Negate the comparison result if the reverse sort flag is set.
				if (tblEl.reverseSort[col])
				cmp = -cmp;
				// Sort by the second column (team name) if those values are equal.
				if (cmp == 0 && col != 1)
				cmp = compareValues(getTextValue(tblEl.rows[minIdx].cells[1]),
									getTextValue(tblEl.rows[j].cells[1]));
				// If this row has a smaller value than the current minimum, remember its
				// position and update the current minimum value.
				if (cmp > 0) {
					minIdx = j;
					minVal = testVal;
				}
			}

			// By now, we have the row with the smallest value. Remove it from the
			// table and insert it before the current row.
			if (minIdx > i) {
				tmpEl = tblEl.removeChild(tblEl.rows[minIdx]);
				tblEl.insertBefore(tmpEl, tblEl.rows[i]);
			}
		}
	} else {
		var rowsCount = tblEl.rows.length;
		var list = new Array(rowsCount);
		// move rows into array, find and set sort key
		for (i = 0; i < rowsCount; i++) {
			list[i] = tblEl.removeChild(tblEl.rows[0]);
			list[i].textValue = getTextValue(list[i].cells[col]);
		}
		// sort
		list.sort(sortByValue);
		// move rows back into table
		for (i = 0; i < rowsCount; i++) {
			tblEl.appendChild(list[i]);
		}
		list.length = 0;
	}
	// make it look pretty.
	makePretty(tblEl, col, tblEl.reverseSort[col]);

	// restore the table's display style
	tblEl.style.display = oldDsply;

/*	if ((window.event.srcElement.tagName) && ("A" + 
		window.event.shiftKey))
		window.event.returnValue = false;*/
	return false;
}

//-----------------------------------------------------------------------------
// Functions to get and compare values during a sort.
//-----------------------------------------------------------------------------
var reverseSort = true
function sortByValue(a, b) {
	var x = a.textValue;
	var y = b.textValue;

	if (reverseSort)
		return ((x < y) ? -1 : ((x > y) ? 1 : 0));
	else
		return ((x < y) ? 1 : ((x > y) ? -1 : 0));
}

function compareValues(v1, v2) {
	var f1, f2;
	
	// If the values are numeric, convert them to floats.
	
	f1 = parseFloat(v1);
	f2 = parseFloat(v2);
	if (!isNaN(f1) && !isNaN(f2)) {
		v1 = f1;
		v2 = f2;
	}
	
	// Compare the two values.
	if (v1 == v2)
		return 0;
	if (v1 > v2)
		return 1
	return -1;
}

// This code is necessary for browsers that don't reflect the DOM constants
// (like IE).
if (document.ELEMENT_NODE == null) {
	document.ELEMENT_NODE = 1;
	document.TEXT_NODE = 3;
}

var date = new RegExp("(([0-9]+-[0-9]+-[0-9]+)|Never)");
var dateTime = new RegExp("(([0-9]+-[0-9]+-[0-9]+ [0-9]+:[0-9]+:[0-9]+)|Never)");
var time = new RegExp("(([0-9]+:[0-9]+:[0-9]+)|Never)");
// var versionNumber = new RegExp("([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)");
var bytes = new RegExp("([0-9]+.[0-9]+ .+B|NaN)");
var isNumber = new RegExp("^([0-9]+(|\.[0-9]+))$");
function getTextValue(el) {

	var i;
	var s;

	// Find and concatenate the values of all text nodes contained within the
	// element.

	s = "";
	for (i = 0; i < el.childNodes.length; i++) {
		if (el.childNodes[i].nodeType == document.TEXT_NODE ||
			el.childNodes[i].nodeType == document.COMMENT_NODE)
			s += el.childNodes[i].nodeValue;
		else if (el.childNodes[i].nodeType == document.ELEMENT_NODE &&
						el.childNodes[i].tagName == "BR")
			s += " ";
		else
			// Use recursion to get text within sub-elements.
			s += getTextValue(el.childNodes[i]);
	}
	if(s.match(bytes)) {
		s = s.replace("NaN", "-1 KiB");
		var number = s.split(" ")[0];
		var unit = s.split(" ")[1];
		var factor = 1;
		switch (unit) {
			case "YiB": factor *= 1024;
			case "ZiB": factor *= 1024;
			case "EiB": factor *= 1024;
			case "PiB": factor *= 1024;
			case "TiB": factor *= 1024;
			case "GiB": factor *= 1024;
			case "MiB": factor *= 1024;
			case "KiB": factor *= 1024; break;
			case "YB": factor *= 1000;
			case "ZB": factor *= 1000;
			case "EB": factor *= 1000;
			case "PB": factor *= 1000;
			case "TB": factor *= 1000;
			case "GB": factor *= 1000;
			case "MB": factor *= 1000;
			case "KB": factor *= 1000;
		}
		if(!isNaN(parseFloat(number))) {
			return parseFloat(number)*factor;
		}
	}

	if(s.match(date) || s.match(dateTime) || s.match(time)) {
		s = s.replace(/-/g, "");
		s = s.replace(/:/g, "");
		s = s.replace(/ /g, ".");
		s = s.replace("Never", "000000");
	}
// 	if ( s.match(versionNumber) ) {
// 		s = s.replace(/\./g,"");
// 		s = s.replace("None", "000000");
// 	}

	if( s.match(isNumber) ) {
		var f = parseFloat(s);
		if (!isNaN(f))
			return f;
	}

	return normalizeString(s);
}

// Regular expressions for normalizing white space.
var whtSpEnds = new RegExp("^\\s*|\\s*$", "g");
var whtSpMult = new RegExp("\\s\\s+", "g");

function normalizeString(s) {

	s = s.replace(whtSpMult, " ");  // Collapse any multiple whites space.
	s = s.replace(whtSpEnds, "");   // Remove leading or trailing white space.

	return s;
}

//-----------------------------------------------------------------------------
// Functions to update the table appearance after a sort.
//-----------------------------------------------------------------------------

// Style class names.
var rowOddClsNm = "odd";
var rowEvenClsNm = "even";
var colClsNm = "sorted";

var colAscClsNm = "asc";
var colDescClsNm = "desc";

// Regular expressions for setting class names.
var rowOddTest = new RegExp(rowOddClsNm, "gi");
var rowEvenTest = new RegExp(rowEvenClsNm, "gi");
var colTest = new RegExp(colClsNm, "gi");
var colAscTest = new RegExp(colAscClsNm, "gi");
var colDescTest = new RegExp(colDescClsNm, "gi");
var noPrettyTest = new RegExp("nopretty", "gi");

function makePretty(tblEl, col, rev, altOnly) {
	var i, j;
	var rowEl, cellEl;
	var off=1;

	// set style classes on each row to alternate their appearance.
	for (i = 0; i < tblEl.rows.length; i++) {
		rowEl = tblEl.rows[i];
		if(rowEl.className.match(invisClass))
			off += 1;

		if ((i-off) % 2 != 0)
			rowEl.className = rowEl.className.replace(rowEvenTest, rowOddClsNm);
		else
			rowEl.className = rowEl.className.replace(rowOddTest, rowEvenClsNm);

		rowEl.className = normalizeString(rowEl.className);
		// Set style classes on each column (other than the name column) to
		// highlight the one that was sorted.
		if(altOnly)
			continue;

		for (j = 0; j < tblEl.rows[i].cells.length; j++) {
			cellEl = rowEl.cells[j];
			cellEl.className = cellEl.className.replace(colTest, "");
			if (j == col)
				cellEl.className += " " + colClsNm;
			cellEl.className = normalizeString(cellEl.className);
		}
	}
	if(altOnly)
		return;

	// find the table header and footer, and highlight the column that was sorted by
 	makeTopBottomPretty(tblEl.parentNode.tHead,col,rev)
	makeTopBottomPretty(tblEl.parentNode.tFoot,col,rev)
}

function makeTopBottomPretty(blockEl, col, rev) {
	if (!blockEl) return
	// for each potental row in header / foot
	for (j = 0; j < blockEl.rows.length; j++) {
		var rowEl = blockEl.rows[j];
		// set style classes for each column
		if(rowEl.className.match(noPrettyTest)) continue;

		for (i = 0; i < rowEl.cells.length; i++) {
			cellEl = rowEl.cells[i];
			// clear old styles
			cellEl.className = cellEl.className.replace(colTest, "");
			cellEl.className = cellEl.className.replace(colAscTest, "");
			cellEl.className = cellEl.className.replace(colDescTest, "");
			// highlight the header of the sorted column.
			if (i == col) {
				cellEl.className += " " + colClsNm;
				if (rev)
					cellEl.className += " " + colAscClsNm;
				else
					cellEl.className += " " + colDescClsNm;
			}
			cellEl.className = normalizeString(cellEl.className);
		}
	}
}

function showToggle(tblId, ElementName, show)
{
	var tblEl = document.getElementById(tblId);
	if(!tblEl) return;
	for (i = 0; i < tblEl.rows.length; i++) {
		rowEl = tblEl.rows[i];
		if (rowEl.className.indexOf(ElementName) > -1) {
				if(!show) {
						rowEl.className += " " + invisClass;
				} else {
						rowEl.className = rowEl.className.replace(rowInvisTest, "");
				}
				rowEl.className = normalizeString(rowEl.className);
		}
	}
	makePretty(tblEl,null,null,true);
}



function SetAllCheckBoxes(Master,CheckValue)
{
	var objCheckBoxes = document.getElementsByTagName('input');
	if(!objCheckBoxes)
		return;

	// set the check value for all check boxes
	for(var i = 0; i < objCheckBoxes.length; i++) {
		if(objCheckBoxes[i].className == 'checkbox' && objCheckBoxes[i] != Master){
			objCheckBoxes[i].checked = CheckValue;
// 			objCheckBoxes[i].click();
		}
	}
}

//
//
//
function createCalendar(inputField, buttonName)
{
  Calendar.setup(
    {
      inputField  : inputField,         // ID of the input field
      ifFormat    : "%Y-%m-%d",    // the date format
      button      : buttonName          // ID of the button
    }
  );
}

function setCookie( cookieName, value, expiredays )
{
	deleteCookie( cookieName )
	var exdate=new Date();
	exdate.setDate(exdate.getDate()+expiredays);
	if (value==null) value = "";
	document.cookie=cookieName+ "=" +escape(value)+
		((expiredays==null) ? "" : ";expires="+exdate.toGMTString())+
		";path="+basepath;
}

function deleteCookie ( cookieName )
{
	var cookieDate = new Date ( );  // current date & time
	cookieDate.setTime ( cookieDate.getTime() - 1 );
	document.cookie = cookieName += "=; expires=" + cookieDate.toGMTString()+";path="+basepath;
}

function getCookie( cookieName )
{
	if (document.cookie.length>0)
	{
		cookieStart=document.cookie.indexOf(cookieName + "=");
		if (cookieStart!=-1)
		{ 
			cookieStart=cookieStart + cookieName.length+1; 
			cookieEnd=document.cookie.indexOf(";",cookieStart);
			if (cookieEnd==-1) cookieEnd=document.cookie.length;
			return unescape(document.cookie.substring(cookieStart,cookieEnd));
		}
	}
	return "";
}

function regDimensions( id )
{
	var dimObj = document.getElementsByTagName(id);
	setCookie('dimensions', dimObj.clientWidth + 'x' + dimObj.clientHeight)
}

// borrowed from webdeveloper and refactored not so well
function displayCSSMediaType(type, reset)
{
	var media            = null;
	var styleSheet       = null;
	var styleSheetLength = null;
	var styleSheetList   = null;

	styleSheetList   = document.styleSheets;
	styleSheetLength = styleSheetList.length;

	if(!type) reset = true;

	// Loop through the style sheets
	for(var j = 0; j < styleSheetLength; j++)
	{
		styleSheet = styleSheetList[j];
		media = styleSheet.media;

		// If resetting
		if(reset)
		{
			// If the style sheet has the webdeveloper-appended media
			if(media.mediaText.indexOf("webdeveloper-appended") != -1)
			{
				media.deleteMedium("webdeveloper-appended");
				media.deleteMedium("screen");
			}
			else if(media.mediaText.indexOf("webdeveloper-deleted") != -1)
			{
				media.appendMedium("screen");
				media.deleteMedium("webdeveloper-deleted");
			}
		}
		else
		{
			// If the style sheet matches this media
			if(media.mediaText.indexOf(type) != -1)
			{
				// If the style sheet has the screen media
				if(media.mediaText.indexOf("screen") == -1)
				{
					media.appendMedium("webdeveloper-appended");
					media.appendMedium("screen");
				}
			}
			else if(media.mediaText.indexOf("screen") != -1)
			{
				// If the media length is not 0
				if(media.length != 0)
				{
					media.deleteMedium("screen");
				}

				media.appendMedium("webdeveloper-deleted");
			}
		}

		// Force the styles to reapply by disabling and enabling the style sheet
		styleSheet.disabled = true;
		styleSheet.disabled = false;
	}
}
