import blackBackpack from "../Images/BlackBackpack.jpeg";
import blueHoodieLar from "../Images/BlueHoodieLar.jpeg";
import blueHoodieMed from "../Images/BlueHoodieMed.jpeg";
import coffeeMug from "../Images/CoffeeMug.jpeg";
import denimJacket from "../Images/DenimJacket.jpeg";
import deskMat from "../Images/DeskMat.jpeg";
import gamingMouse from "../Images/GamingMouse.jpeg";
import mechanicalKeyboard from "../Images/MechanicalKeyboard.jpeg";
import runningShorts from "../Images/RunningShorts.jpeg";
import whiteSneakers from "../Images/WhiteSneakers.jpeg";
import wirelessEarbuds from "../Images/WirelessEarbuds.jpeg";
import yogaMat from "../Images/YogaMat.jpeg";

export const getProductImage = (name) => {
  const map = {
    "Black Backpack": blackBackpack,
    "Blue Hoodie - Large": blueHoodieLar,
    "Blue Hoodie - Medium": blueHoodieMed,
    "Coffee Mug": coffeeMug,
    "Denim Jacket": denimJacket,
    "Desk Mat": deskMat,
    "Gaming Mouse": gamingMouse,
    "Mechanical Keyboard": mechanicalKeyboard,
    "Running Shorts": runningShorts,
    "White Sneakers": whiteSneakers,
    "Wireless Earbuds": wirelessEarbuds,
    "Yoga Mat": yogaMat
  };
  return map[name];
};
