$(function () {
  let syncClient;

  $.getJSON('/sync-token', function (tokenResponse) {
    // Get API token and initialize Sync client.
    syncClient = new Twilio.Sync.Client(tokenResponse.token, { logLevel: 'info' });
    syncClient.on('connectionStateChanged', function(state) {
      if (state !== 'connected') {
        console.log("Sync is not connected");
      } else {
        console.log("Sync is connected and listening to new orders.");
      }
    });

    // All orders are stored in a Sync Map.  Connect to the Sync Map and create event listeners for when
    // for when new items are added to the list and when items are closed from the list.
    syncClient.map(tokenResponse.syncMapID).then(function(syncMap) {
      syncMap.getItems().then(function(itm){
        itm.items.forEach(test => console.log(test));
      });

      // When a new arrival occurs create a new card with the details.
      syncMap.on('itemAdded', function(event) {
        console.log("New Order Added");
        createOrderCards(event.item);
      });

      syncMap.on('itemUpdated', function(item) {
        console.log("Order Updated");
        let orderID = item.item.key;
        let dat= item.item.value;

        // Update order status
        let card = $("div.card[data-order-id='" + orderID +"']");
        let cardStatus = card.find(".status");
        cardStatus.html('<b>Status: </b>' + dat.status);

        // If the customer has arrived change the class.
        if (dat.status === "Arrived") {
          card.removeClass("ordered");
          card.addClass("arrived");
        }

        // After sending a reminder remove that button from the order to prevent spamming customer.
        if (dat.status === "Reminder Sent") {
          let reminderBtn = card.find(".btn-info");
          reminderBtn.fadeOut(500, function() {
            reminderBtn.remove();
          });
        }

        // If customer has arrived add new info to the order card.
        // If the customer changes  one of their response update the card in-place.
        if ("in_car" in dat) {
          let cardInCar = card.find('.in-car');
          let inCar = '<p class="card-text in-car"><b>Waiting in Car:</b> ' + dat.in_car + '</p>';

          if ( cardInCar.length ){
            cardInCar.replaceWith(inCar);
          } else {
            $(inCar).insertAfter(cardStatus);
          }

          let cardCarMake = card.find('.car-make');
          let cardCarLicense = card.find(".car-license");

          // Add extra details if waiting in car.
          if (dat.in_car === "Yes") {
            let carMake = '<p class="card-text car-make"><b>Car Description: </b>'+ dat.car_make + '</p>';
            if ( cardCarMake.length ) {
              cardCarMake.replaceWith(carMake);
            } else {
              $(carMake).insertAfter(card.find(".in-car"));
            }

            let carLicense = '<p class="card-text car-license"><b>Car License: </b>'+ dat.car_license + '</p>';
            if ( cardCarLicense.length ){
              cardCarLicense.replaceWith(carLicense);
            } else {
              $(carLicense).insertAfter(card.find(".car-make"));
            }
          } else {
            // Remove car make and car license if they exist.
            cardCarMake.remove();
            cardCarLicense.remove();
          }
        }

      });

      // Listen for closing an order.  Remove order from Sync.
      $(document).on("click", ".btn-order-close", function(event) {
        let closeCardCol = $(event.target).closest("div.col-sm-8");
        let closeCard = $(event.target).closest("div.card");

        let order = closeCard.data("orderId");

        syncMap.remove(order).then(function(){
          console.log("Removing order...");
          closeCardCol.fadeOut(500, function () {
            closeCardCol.remove();
          });
        });
      });
    });
  });

  // Send reminder text messages.
  $(document).on("click", ".btn-order-ready", function(event) {
    let orderCard = $(event.target).closest("div.card");
    let orderId = orderCard.data("orderId");

    $.post("/send-order-reminder", {orderID: orderId}, function( data ){
      console.log(data);
    });
  });

  //Create new order cards
  function createOrderCards(order) {
    console.log(order.value);

    let divCol = document.createElement("div");
    divCol.className="col-sm-8 col-md-8 col-lg-6 pb-2";

    let card = document.createElement("div");
    card.className='card ordered';
    $(card).attr("data-order-id", order.key);

    let cardBody = document.createElement("div");
    cardBody.className = 'card-body';

    let cardTitle = document.createElement("h5");
    cardTitle.innerText = "Customer: " + order.value.name;
    cardTitle.className="card-title customer";

    let contentPhone = document.createElement("p");
    contentPhone.innerText = "Phone: " + order.value.readPhone;
    contentPhone.className="card-text phone";

    let contentStatus = document.createElement("p");
    contentStatus.innerText = "Status: " + order.value.status;
    contentStatus.className="card-text status";

    let closeButton = document.createElement("button");
    closeButton.className="btn btn-order-close mr-1";
    closeButton.innerHTML="Close Order";

    let remindButton = document.createElement("button");
    remindButton.className="btn btn-order-ready";
    remindButton.innerHTML="Send Order Ready Text";

    // Put the body together.
    cardBody.appendChild(cardTitle);
    cardBody.appendChild(contentPhone);
    cardBody.appendChild(contentStatus);
    cardBody.appendChild(closeButton);
    cardBody.appendChild(remindButton);

    card.append(cardBody);

    divCol.append(card);

    // Add card to HTML.
    document.getElementById("order-list").appendChild(divCol);
  }

});
