-- phpMyAdmin SQL Dump
-- version 4.0.10deb1
-- http://www.phpmyadmin.net
--
-- Host: localhost
-- Generation Time: Apr 25, 2016 at 08:53 PM
-- Server version: 5.5.49-0ubuntu0.14.04.1
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
-- Table structure for table `TB_LIKE`
--

CREATE TABLE IF NOT EXISTS `TB_LIKE` (
  `ID_USER_INTERNAL` int(11) NOT NULL,
  `ID_OBJ_INTERNAL` int(11) NOT NULL,
  `DT_CRE` datetime NOT NULL,
  PRIMARY KEY (`ID_USER_INTERNAL`,`ID_OBJ_INTERNAL`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

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
  `F_LIKE_DETAIL` varchar(1) DEFAULT NULL,
  `F_WORD_SPLIT` varchar(1) DEFAULT NULL,
  `ID_INTERNAL` int(11) NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`ID_INTERNAL`),
  UNIQUE KEY `ID` (`ID`),
  KEY `ID_FATHER` (`ID_FATHER`),
  KEY `ID_PAGE` (`ID_PAGE`),
  KEY `ID_USER` (`ID_USER`),
  KEY `ST_TYPE` (`ST_TYPE`),
  KEY `F_LIKE_DETAIL` (`F_LIKE_DETAIL`),
  KEY `ST_FB_TYPE` (`ST_FB_TYPE`),
  KEY `F_WORD_SPLIT` (`F_WORD_SPLIT`),
  FULLTEXT KEY `TX_1` (`TX_STORY`),
  FULLTEXT KEY `TX_2` (`TX_MESSAGE`),
  FULLTEXT KEY `TX_NAME` (`TX_NAME`),
  FULLTEXT KEY `TX_CAPTION` (`TX_CAPTION`),
  FULLTEXT KEY `TX_DESCRIPTION` (`TX_DESCRIPTION`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 AUTO_INCREMENT=189528 ;

-- --------------------------------------------------------

--
-- Table structure for table `TB_USER`
--

CREATE TABLE IF NOT EXISTS `TB_USER` (
  `ID` varchar(200) NOT NULL,
  `ST_NAME` varchar(250) NOT NULL,
  `DT_CRE` datetime NOT NULL,
  `DT_MSG` datetime NOT NULL,
  `ID_INTERNAL` int(11) NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`ID_INTERNAL`),
  UNIQUE KEY `ID` (`ID`,`ST_NAME`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 AUTO_INCREMENT=696439 ;

-- --------------------------------------------------------

--
-- Stand-in structure for view `V_PAGES`
--
CREATE TABLE IF NOT EXISTS `V_PAGES` (
`ID` varchar(200)
,`TX_NAME` text
,`POST_COUNT` bigint(21)
,`POST_SHARES_TOTAL` decimal(32,0)
,`POST_LIKES_TOTAL` decimal(32,0)
,`COMMENT_COUNT_TOTAL` decimal(42,0)
,`COMM_LIKES_TOTAL` decimal(54,0)
);
-- --------------------------------------------------------

--
-- Stand-in structure for view `V_POST_AGGREGATES`
--
CREATE TABLE IF NOT EXISTS `V_POST_AGGREGATES` (
`POST_ID` varchar(200)
,`ID_PAGE` varchar(200)
,`POST_TYPE` varchar(20)
,`POST_MESSAGE` text
,`TX_STORY` text
,`POST_LIKES` int(11)
,`N_SHARES` int(11)
,`COMMENT_COUNT` bigint(21)
,`TOTAL_COMM_LIKES` decimal(32,0)
);
-- --------------------------------------------------------

--
-- Stand-in structure for view `V_POST_COMMENT_DETAIL`
--
CREATE TABLE IF NOT EXISTS `V_POST_COMMENT_DETAIL` (
`POST_ID` varchar(200)
,`ID_PAGE` varchar(200)
,`POST_TYPE` varchar(20)
,`POST_MESSAGE` text
,`TX_STORY` text
,`POST_LIKES` int(11)
,`N_SHARES` int(11)
,`COMMENT_ID` varchar(200)
,`ST_FB_TYPE` varchar(20)
,`TX_MESSAGE` text
,`COMMENT_LIKES` int(11)
);
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
-- Structure for view `V_PAGES`
--
DROP TABLE IF EXISTS `V_PAGES`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `V_PAGES` AS select `A`.`ID` AS `ID`,`A`.`TX_NAME` AS `TX_NAME`,count(1) AS `POST_COUNT`,sum(`P`.`N_SHARES`) AS `POST_SHARES_TOTAL`,sum(`P`.`POST_LIKES`) AS `POST_LIKES_TOTAL`,sum(`P`.`COMMENT_COUNT`) AS `COMMENT_COUNT_TOTAL`,sum(`P`.`TOTAL_COMM_LIKES`) AS `COMM_LIKES_TOTAL` from (`V_POST_AGGREGATES` `P` join `TB_OBJ` `A` on((`A`.`ID` = `P`.`ID_PAGE`))) group by `A`.`ID`,`A`.`TX_NAME`;

-- --------------------------------------------------------

--
-- Structure for view `V_POST_AGGREGATES`
--
DROP TABLE IF EXISTS `V_POST_AGGREGATES`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `V_POST_AGGREGATES` AS select `V_POST_COMMENT_DETAIL`.`POST_ID` AS `POST_ID`,`V_POST_COMMENT_DETAIL`.`ID_PAGE` AS `ID_PAGE`,`V_POST_COMMENT_DETAIL`.`POST_TYPE` AS `POST_TYPE`,`V_POST_COMMENT_DETAIL`.`POST_MESSAGE` AS `POST_MESSAGE`,`V_POST_COMMENT_DETAIL`.`TX_STORY` AS `TX_STORY`,`V_POST_COMMENT_DETAIL`.`POST_LIKES` AS `POST_LIKES`,`V_POST_COMMENT_DETAIL`.`N_SHARES` AS `N_SHARES`,count(1) AS `COMMENT_COUNT`,sum(`V_POST_COMMENT_DETAIL`.`COMMENT_LIKES`) AS `TOTAL_COMM_LIKES` from `V_POST_COMMENT_DETAIL` group by `V_POST_COMMENT_DETAIL`.`POST_ID`,`V_POST_COMMENT_DETAIL`.`ID_PAGE`,`V_POST_COMMENT_DETAIL`.`POST_TYPE`,`V_POST_COMMENT_DETAIL`.`POST_MESSAGE`,`V_POST_COMMENT_DETAIL`.`TX_STORY`,`V_POST_COMMENT_DETAIL`.`POST_LIKES`,`V_POST_COMMENT_DETAIL`.`N_SHARES`;

-- --------------------------------------------------------

--
-- Structure for view `V_POST_COMMENT_DETAIL`
--
DROP TABLE IF EXISTS `V_POST_COMMENT_DETAIL`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `V_POST_COMMENT_DETAIL` AS select `P`.`ID` AS `POST_ID`,`P`.`ID_PAGE` AS `ID_PAGE`,`P`.`ST_FB_TYPE` AS `POST_TYPE`,`P`.`TX_MESSAGE` AS `POST_MESSAGE`,`P`.`TX_STORY` AS `TX_STORY`,`P`.`N_LIKES` AS `POST_LIKES`,`P`.`N_SHARES` AS `N_SHARES`,`C`.`ID` AS `COMMENT_ID`,`C`.`ST_FB_TYPE` AS `ST_FB_TYPE`,`C`.`TX_MESSAGE` AS `TX_MESSAGE`,`C`.`N_LIKES` AS `COMMENT_LIKES` from (`TB_OBJ` `P` join `TB_OBJ` `C` on((`P`.`ID` = `C`.`ID_POST`)));

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
