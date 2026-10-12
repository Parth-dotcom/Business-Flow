document.addEventListener(
    "DOMContentLoaded",
    function () {

        const customerSelect =
            document.getElementById("customer");

        if (!customerSelect) {
            return;
        }


        /* =========================================
           CREATE BUTTON
        ========================================= */

        const customerWrapper =
            customerSelect.parentElement;


        const buttonWrapper =
            document.createElement("div");

        buttonWrapper.className =
            "quick-customer-button-wrapper";


        buttonWrapper.innerHTML = `

            <button
                type="button"
                class="btn btn-outline-primary quick-add-customer-btn"
                data-bs-toggle="modal"
                data-bs-target="#quickCustomerModal"
            >

                <i class="bi bi-person-plus-fill me-1"></i>

                Add Customer

            </button>

        `;


        customerWrapper.appendChild(
            buttonWrapper
        );


        /* =========================================
           MODAL
        ========================================= */

        const modalHTML = `

            <div
                class="modal fade"
                id="quickCustomerModal"
                tabindex="-1"
                aria-hidden="true"
            >

                <div
                    class="modal-dialog modal-dialog-centered modal-lg"
                >

                    <div class="modal-content border-0 shadow-lg">


                        <!-- HEADER -->

                        <div class="modal-header">

                            <div>

                                <h5 class="modal-title fw-bold mb-1">

                                    <i
                                        class="bi bi-person-plus-fill text-primary me-2"
                                    ></i>

                                    Add New Customer

                                </h5>

                                <small class="text-muted">

                                    Add customer details without leaving the invoice.

                                </small>

                            </div>


                            <button
                                type="button"
                                class="btn-close"
                                data-bs-dismiss="modal"
                                aria-label="Close"
                            ></button>

                        </div>


                        <!-- BODY -->

                        <div class="modal-body p-4">

                            <div
                                id="quickCustomerAlert"
                                class="alert d-none"
                                role="alert"
                            ></div>


                            <form
                                id="quickCustomerForm"
                            >

                                <div class="row g-3">


                                    <!-- NAME -->

                                    <div class="col-12 col-md-6">

                                        <label
                                            class="form-label fw-semibold"
                                            for="quickCustomerName"
                                        >

                                            Customer Name
                                            <span class="text-danger">*</span>

                                        </label>

                                        <input
                                            type="text"
                                            id="quickCustomerName"
                                            name="name"
                                            class="form-control"
                                            placeholder="Enter customer name"
                                            autocomplete="off"
                                            required
                                        >

                                    </div>


                                    <!-- PHONE -->

                                    <div class="col-12 col-md-6">

                                        <label
                                            class="form-label fw-semibold"
                                            for="quickCustomerPhone"
                                        >

                                            Phone Number
                                            <span class="text-danger">*</span>

                                        </label>

                                        <input
                                            type="text"
                                            id="quickCustomerPhone"
                                            name="phone"
                                            class="form-control"
                                            placeholder="Enter phone number"
                                            maxlength="15"
                                            autocomplete="off"
                                            required
                                        >

                                    </div>


                                    <!-- EMAIL -->

                                    <div class="col-12 col-md-6">

                                        <label
                                            class="form-label fw-semibold"
                                            for="quickCustomerEmail"
                                        >

                                            Email

                                        </label>

                                        <input
                                            type="email"
                                            id="quickCustomerEmail"
                                            name="email"
                                            class="form-control"
                                            placeholder="customer@email.com"
                                            autocomplete="off"
                                        >

                                    </div>


                                    <!-- CITY -->

                                    <div class="col-12 col-md-6">

                                        <label
                                            class="form-label fw-semibold"
                                            for="quickCustomerCity"
                                        >

                                            City

                                        </label>

                                        <input
                                            type="text"
                                            id="quickCustomerCity"
                                            name="city"
                                            class="form-control"
                                            placeholder="Enter city"
                                            autocomplete="off"
                                        >

                                    </div>


                                    <!-- ADDRESS -->

                                    <div class="col-12">

                                        <label
                                            class="form-label fw-semibold"
                                            for="quickCustomerAddress"
                                        >

                                            Address

                                        </label>

                                        <textarea
                                            id="quickCustomerAddress"
                                            name="address"
                                            class="form-control"
                                            rows="3"
                                            placeholder="Enter customer address"
                                        ></textarea>

                                    </div>

                                </div>

                            </form>

                        </div>


                        <!-- FOOTER -->

                        <div class="modal-footer px-4 pb-4">

                            <button
                                type="button"
                                class="btn btn-outline-secondary"
                                data-bs-dismiss="modal"
                            >

                                Cancel

                            </button>


                            <button
                                type="button"
                                id="saveQuickCustomerBtn"
                                class="btn btn-primary px-4"
                            >

                                <i
                                    class="bi bi-check-circle me-1"
                                ></i>

                                Save Customer

                            </button>

                        </div>

                    </div>

                </div>

            </div>

        `;


        document.body.insertAdjacentHTML(
            "beforeend",
            modalHTML
        );


        /* =========================================
           ELEMENTS
        ========================================= */

        const modalElement =
            document.getElementById(
                "quickCustomerModal"
            );


        const form =
            document.getElementById(
                "quickCustomerForm"
            );


        const alertBox =
            document.getElementById(
                "quickCustomerAlert"
            );


        const saveButton =
            document.getElementById(
                "saveQuickCustomerBtn"
            );


        /* =========================================
           CSRF TOKEN
        ========================================= */

        function getCookie(name) {

            let cookieValue = null;

            if (document.cookie) {

                const cookies =
                    document.cookie.split(";");

                for (
                    let cookie of cookies
                ) {

                    cookie =
                        cookie.trim();

                    if (
                        cookie.startsWith(
                            name + "="
                        )
                    ) {

                        cookieValue =
                            decodeURIComponent(
                                cookie.substring(
                                    name.length + 1
                                )
                            );

                        break;
                    }
                }
            }

            return cookieValue;
        }


        /* =========================================
           ALERT
        ========================================= */

        function showAlert(
            message,
            type = "danger"
        ) {

            alertBox.className =
                "alert alert-" +
                type;

            alertBox.textContent =
                message;

        }


        /* =========================================
           SAVE CUSTOMER
        ========================================= */

        saveButton.addEventListener(
            "click",
            async function () {

                if (
                    !form.checkValidity()
                ) {

                    form.reportValidity();

                    return;

                }


                saveButton.disabled =
                    true;


                saveButton.innerHTML = `

                    <span
                        class="spinner-border spinner-border-sm me-2"
                    ></span>

                    Saving...

                `;


                const formData =
                    new FormData(form);


                try {

                    const response =
                        await fetch(
                            "/customers/quick-create/",
                            {
                                method: "POST",

                                headers: {
                                    "X-CSRFToken":
                                        getCookie(
                                            "csrftoken"
                                        ),

                                    "X-Requested-With":
                                        "XMLHttpRequest",
                                },

                                body: formData,
                            }
                        );


                    const data =
                        await response.json();


                    if (!response.ok ||
                        !data.success
                    ) {

                        throw new Error(
                            data.message ||
                            "Unable to create customer."
                        );

                    }


                    /* =================================
                       ADD CUSTOMER TO DROPDOWN
                    ================================= */

                    const customer =
                        data.customer;


                    const option =
                        document.createElement(
                            "option"
                        );


                    option.value =
                        customer.id;


                    option.textContent =
                        customer.name +
                        " — " +
                        customer.phone;


                    option.selected =
                        true;


                    customerSelect.appendChild(
                        option
                    );


                    customerSelect.value =
                        customer.id;


                    /* =================================
                       CLOSE MODAL
                    ================================= */

                    const modal =
                        bootstrap.Modal.getInstance(
                            modalElement
                        );


                    if (modal) {

                        modal.hide();

                    }


                    /* =================================
                       RESET FORM
                    ================================= */

                    form.reset();

                    alertBox.className =
                        "alert d-none";


                } catch (error) {

                    showAlert(
                        error.message,
                        "danger"
                    );

                } finally {

                    saveButton.disabled =
                        false;


                    saveButton.innerHTML = `

                        <i
                            class="bi bi-check-circle me-1"
                        ></i>

                        Save Customer

                    `;

                }

            }
        );


        /* =========================================
           RESET MODAL WHEN CLOSED
        ========================================= */

        modalElement.addEventListener(
            "hidden.bs.modal",
            function () {

                form.reset();

                alertBox.className =
                    "alert d-none";

                alertBox.textContent =
                    "";

            }
        );

    }
);