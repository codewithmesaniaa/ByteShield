// Show selected file names
document.getElementById("file1").onchange = e => {
    document.getElementById("name1").innerText = e.target.files[0].name;
};

document.getElementById("file2").onchange = e => {
    document.getElementById("name2").innerText = e.target.files[0].name;
};


// Main function
async function checkSimilarity() {
    const file1 = document.getElementById("file1").files[0];
    const file2 = document.getElementById("file2").files[0];

    if (!file1 || !file2) {
        alert("Please upload both files!");
        return;
    }

    const formData = new FormData();
    formData.append("file1", file1);
    formData.append("file2", file2);

    try {
        const response = await fetch("/check_similarity", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            throw new Error("Server error");
        }

        const data = await response.json();

        const resultDiv = document.getElementById("result");

        // Store data
        localStorage.setItem("comparisonData", JSON.stringify(data));

        // Clean UI
        resultDiv.innerHTML = `
            <h2>Result</h2>
            <p><b>Final Similarity:</b> ${data.final_similarity}%</p>
            <p><b>Verdict:</b> ${data.verdict}</p>

            <button onclick="viewDetails()"
                style="
                    margin-top:15px;
                    padding:10px 20px;
                    background: linear-gradient(45deg, #4e54c8, #8f94fb);
                    border:none;
                    color:white;
                    border-radius:8px;
                    cursor:pointer;
                ">
                View Detailed Comparison
            </button>
        `;

    } catch (error) {
        console.error(error);
        document.getElementById("result").innerText = "Error connecting to backend";
    }
}


// Redirect to details page
function viewDetails() {
    window.location.href = "/details";
}