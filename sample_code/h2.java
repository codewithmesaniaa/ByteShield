public class h2 {
    public static void main(String[] args) {
        int num = 5;
        int fact = 1;

        for (int k = 1; k <= num; k++) {
            fact *= k;
        }

        System.out.println(fact);
    }
}