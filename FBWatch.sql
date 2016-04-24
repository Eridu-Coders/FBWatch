-- phpMyAdmin SQL Dump
-- version 4.0.10deb1
-- http://www.phpmyadmin.net
--
-- Host: localhost
-- Generation Time: Apr 24, 2016 at 10:23 PM
-- Server version: 5.5.47-0ubuntu0.14.04.1
-- PHP Version: 5.5.9-1ubuntu4.16

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;

--
-- Database: `FBWatch`
--

-- --------------------------------------------------------

--
-- Table structure for table `TB_MEDIA`
--

CREATE TABLE IF NOT EXISTS `TB_MEDIA` (
  `ID_OWNER` varchar(200) NOT NULL,
  `TX_URL_LINK` text NOT NULL,
  `TX_SRC_PICTURE` text NOT NULL,
  `TX_RAW` text NOT NULL,
  PRIMARY KEY (`ID_OWNER`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `TB_OBJ`
--

CREATE TABLE IF NOT EXISTS `TB_OBJ` (
  `ID` varchar(200) NOT NULL,
  `ID_FATHER` varchar(200) NOT NULL,
  `ID_PAGE` varchar(200) NOT NULL,
  `ID_POST` varchar(200) NOT NULL,
  `DT_CRE` datetime NOT NULL,
  `ST_TYPE` varchar(10) NOT NULL,
  `ST_FB_TYPE` varchar(20) NOT NULL,
  `TX_NAME` text NOT NULL,
  `TX_CAPTION` text NOT NULL,
  `TX_DESCRIPTION` text NOT NULL,
  `TX_STORY` text NOT NULL,
  `TX_MESSAGE` text NOT NULL,
  `ID_USER` varchar(200) NOT NULL,
  `DT_LAST_UPDATE` datetime DEFAULT NULL,
  `N_LIKES` int(11) NOT NULL,
  `N_SHARES` int(11) NOT NULL,
  `TX_PLACE` text NOT NULL,
  PRIMARY KEY (`ID`),
  KEY `ID_FATHER` (`ID_FATHER`),
  KEY `ID_PAGE` (`ID_PAGE`),
  KEY `ID_USER` (`ID_USER`),
  KEY `ST_TYPE` (`ST_TYPE`),
  FULLTEXT KEY `TX_1` (`TX_STORY`),
  FULLTEXT KEY `TX_2` (`TX_MESSAGE`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `TB_USER`
--

CREATE TABLE IF NOT EXISTS `TB_USER` (
  `ID` varchar(200) NOT NULL,
  `ST_NAME` varchar(250) NOT NULL,
  `DT_CRE` datetime NOT NULL,
  `DT_MSG` datetime NOT NULL,
  PRIMARY KEY (`ID`,`ST_NAME`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `V_PAGE`
--
-- in use(#1356 - View 'FBWatch.V_PAGE' references invalid table(s) or column(s) or function(s) or definer/invoker of view lack rights to use them)

-- --------------------------------------------------------

--
-- Table structure for table `V_PAGE_COUNT`
--
-- in use(#1356 - View 'FBWatch.V_PAGE' references invalid table(s) or column(s) or function(s) or definer/invoker of view lack rights to use them)

-- --------------------------------------------------------

--
-- Stand-in structure for view `V_USER_CHANGE`
--
CREATE TABLE IF NOT EXISTS `V_USER_CHANGE` (
`ID` varchar(200)
,`UCOUNT` bigint(21)
,`UNAME` varchar(250)
,`ST_NAME` varchar(250)
,`DT_CRE` datetime
);
-- --------------------------------------------------------

--
-- Table structure for table `V_USER_COMM`
--
-- in use(#1356 - View 'FBWatch.V_USER_COMM' references invalid table(s) or column(s) or function(s) or definer/invoker of view lack rights to use them)

-- --------------------------------------------------------

--
-- Table structure for table `V_USER_COMM_COUNT`
--
-- in use(#1356 - View 'FBWatch.V_USER_COMM' references invalid table(s) or column(s) or function(s) or definer/invoker of view lack rights to use them)

-- --------------------------------------------------------

--
-- Stand-in structure for view `V_USER_UNIQUE`
--
CREATE TABLE IF NOT EXISTS `V_USER_UNIQUE` (
`ID` varchar(200)
,`ST_NAME` varchar(250)
,`UCOUNT` bigint(21)
);
-- --------------------------------------------------------

--
-- Stand-in structure for view `V_USER_UNIQUE_1`
--
CREATE TABLE IF NOT EXISTS `V_USER_UNIQUE_1` (
`ID` varchar(200)
,`DMIN` datetime
,`UCOUNT` bigint(21)
);
-- --------------------------------------------------------

--
-- Structure for view `V_USER_CHANGE`
--
DROP TABLE IF EXISTS `V_USER_CHANGE`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `V_USER_CHANGE` AS select `U`.`ID` AS `ID`,`U`.`UCOUNT` AS `UCOUNT`,`U`.`ST_NAME` AS `UNAME`,`R`.`ST_NAME` AS `ST_NAME`,`R`.`DT_CRE` AS `DT_CRE` from (`V_USER_UNIQUE` `U` join `TB_USER` `R` on((`U`.`ID` = `R`.`ID`))) where (`U`.`UCOUNT` > 1);

-- --------------------------------------------------------

--
-- Structure for view `V_USER_UNIQUE`
--
DROP TABLE IF EXISTS `V_USER_UNIQUE`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `V_USER_UNIQUE` AS select `A`.`ID` AS `ID`,`A`.`ST_NAME` AS `ST_NAME`,`B`.`UCOUNT` AS `UCOUNT` from (`TB_USER` `A` join `V_USER_UNIQUE_1` `B` on(((`A`.`ID` = `B`.`ID`) and (`A`.`DT_CRE` = `B`.`DMIN`)))) order by `B`.`UCOUNT` desc,`A`.`ST_NAME`;

-- --------------------------------------------------------

--
-- Structure for view `V_USER_UNIQUE_1`
--
DROP TABLE IF EXISTS `V_USER_UNIQUE_1`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `V_USER_UNIQUE_1` AS select `TB_USER`.`ID` AS `ID`,min(`TB_USER`.`DT_CRE`) AS `DMIN`,count(1) AS `UCOUNT` from `TB_USER` group by `TB_USER`.`ID`;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
