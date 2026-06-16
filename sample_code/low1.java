
public class low1 {
    public static void main(String[] args) {

        String firstName = "Sania";
        String lastName = "Khan";
        String fullName = firstName + " " + lastName;

        if (fullName.length() > 5) {
            System.out.println(fullName);
        } else {
            System.out.println("Name too short");
        }
    }
}
