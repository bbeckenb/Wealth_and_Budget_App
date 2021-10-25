const dashBal = $('#dashboard-balances');

function updateDashboardBalances(balNoLoan, balWLoan) {
    let htmlStr = ''
    if (balNoLoan > 0) {
        htmlStr += '<li class="list-group-item list-group-item-action list-group-item-success text-dark bg-opacity-50">';
    } else if (balNoLoan == 0) {
        htmlStr += '<li class="list-group-item list-group-item-action list-group-item-dark">';
    } else {
        htmlStr += '<li class="list-group-item list-group-item-action list-group-item-danger">';
    }
    htmlStr += `<b>Total Wealth <i>(no loans)</i>:</b>  $ ${balNoLoan}</li>`;
    if (balWLoan > 0) {
        htmlStr += '<li class="list-group-item list-group-item-action list-group-item-success text-dark bg-opacity-50">';
    } else if (balWLoan == 0) {
        htmlStr += '<li class="list-group-item list-group-item-action list-group-item-dark">';
    } else {
        htmlStr += '<li class="list-group-item list-group-item-action list-group-item-danger">';
    }
    htmlStr += `<b>Total Wealth:</b>  $ ${balWLoan}</li>`;  
    dashBal.html(htmlStr);
}

function googleChart(pieChartData) {
    if(pieChartData && pieChartData.length > 1) {    
        google.charts.load("current", {packages:["corechart"]});
            let dataToInsert = `${pieChartData}`
            dataToInsert=dataToInsert.replaceAll('&#34;', '"')
            dataToInsert=JSON.parse(dataToInsert)   
            let data = google.visualization.arrayToDataTable(dataToInsert);
            let options = {
                title: 'Institution Breakdown',
                is3D: true,
                width: 450,
                height: 275,
                backgroundColor: {
                    fill: 'f5f5f5',
                    stroke: '#eef4f8',
                    strokeWidth: 1,
                    rx: 7.5,
                    ry: 7.5
                }
            };
            let chart = new google.visualization.PieChart(document.getElementById('piechart_3d'));
            chart.draw(data, options);
    } else {
        $('#piechart_3d').html("<p>No Institutions or no Accounts linked yet, click 'Link Account' under 'User Options' to get started</p>");
    }
}

function updatePieChart({pieChartData}) {  
    google.charts.load("current", {packages:["corechart"]});
    google.charts.setOnLoadCallback(googleChart);
    function googleChart() {
        if(pieChartData && pieChartData.length > 1) {    
            google.charts.load("current", {packages:["corechart"]});
                let dataToInsert = `${pieChartData}`
                dataToInsert=dataToInsert.replaceAll('&#34;', '"')
                dataToInsert=JSON.parse(dataToInsert)   
                let data = google.visualization.arrayToDataTable(dataToInsert);
                let options = {
                    title: 'Institution Breakdown',
                    is3D: true,
                    width: 450,
                    height: 275,
                    backgroundColor: {
                        fill: 'f5f5f5',
                        stroke: '#eef4f8',
                        strokeWidth: 1,
                        rx: 7.5,
                        ry: 7.5
                    }
                };
                let chart = new google.visualization.PieChart(document.getElementById('piechart_3d'));
                chart.draw(data, options);
        } else {
            $('#piechart_3d').html("<p>No Institutions or no Accounts linked yet, click 'Link Account' under 'User Options' to get started</p>");
        }
    }
}

/**
 * 
 */