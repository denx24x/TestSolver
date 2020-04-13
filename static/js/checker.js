async function getJSON(url) {
    let response = await fetch(url  );
    let commits = await response.json();
    return commits
};


class Checker{
    static init(){
        this.checking = false
        check();
    }

}
Checker.init()

async function check(){
    if(Checker.checking){
        return
    }
    Checker.checking = true;    
    while(Checker.checking){
        await sleep(2000);
        var answer = await getJSON('/result');
        document.getElementById("result").textContent = JSON.stringify(answer['result']);
        if(answer['result'] != 'Процесс выполняется...'){
            Checker.checking = false;
        }
    }
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}


function formSubmit(event) {
    var url = "/result";
    var request = new XMLHttpRequest();
    request.open('POST', url, true);

    request.onload = function() { 
      check()
    };
  
    request.onerror = function() {
        document.getElementById("result").textContent = "Ошибка отправки!";
    };
    request.send(new FormData(event.target)); // create FormData from form that triggered event
    event.preventDefault();
}

document.getElementById("main_form").addEventListener("submit", formSubmit);
