# Core Documentation Baseline Plan

`Issue 5` として、`Core` 基準でのドキュメント導線を整理した記録。

この文書の目的は、`Addon` 未導入ユーザが `documents/` と `WebManual` を読んだときに、

- 何が `Core` の標準機能か
- 何が `Addon` の追加機能か
- 今どこまで設定すれば `Core` が動くか

を迷わず理解できる状態を作ること。

今回は実文書の修正ではなく、`どの文書に何を残し、何を逃がすか` の整理だけを行う。

## 1. 結論

現状の文書は、`Core` と `Addon` の情報が同居している。  
特に [B_CoreSetup.md](/C:/Users/tetsu/Projects/KabuSys/documents/WebManual/B_CoreSetup.md:87) が `Core` セットアップ文書でありながら、AI / LINE / TDnet / EDINET / Yahoo News を同じ流れで案内している。

ただし、`Addon` 情報を完全に外すと、今度は参照先文書が増えて理解しづらくなる。  
そのため `Issue 5` では、`Addon` 情報は文書から外さずに残し、`Core` と `Addon` を区分表示する方針を採る。

`Core` 基準に直すなら、導線は次の 3 層に分けるのが自然。

1. `Core` 利用者が必ず読む入口
2. `Core` だけで完了する設定・運用導線
3. 同じ文書内に併記する `Addon` 任意導線

## 2. 現状の主な混在箇所

### 2.1 WebManual 入口

- [INDEX.md](/C:/Users/tetsu/Projects/KabuSys/documents/WebManual/INDEX.md:1)
- [A_Overview.md](/C:/Users/tetsu/Projects/KabuSys/documents/WebManual/A_Overview.md:1)

現状では `Overview` に `Strategy Lab` が普通の構成要素として載っている。

- [A_Overview.md](/C:/Users/tetsu/Projects/KabuSys/documents/WebManual/A_Overview.md:46)

`Strategy Lab` は責務整理上 `Addon` なので、`Core` 入口で同列表示しない方がよい。

### 2.2 Core Setup 文書

- [B_CoreSetup.md](/C:/Users/tetsu/Projects/KabuSys/documents/WebManual/B_CoreSetup.md:87)

現状では次が 1 つの流れに同居している。

- `Core` 必須設定
- `Core` 推奨設定
- `Addon` 設定
- `Addon` ジョブ

混在が大きい箇所は次。

- 設定一覧表
- Task Scheduler 一覧
- `B-2. オプション機能の導入`
- セットアップ完了チェック

### 2.3 運用文書

- [D_LiveOperation.md](/C:/Users/tetsu/Projects/KabuSys/documents/WebManual/D_LiveOperation.md:100)
- [TradingRunbook.md](/C:/Users/tetsu/Projects/KabuSys/documents/08_Operations/TradingRunbook.md:115)
- [Monitoring.md](/C:/Users/tetsu/Projects/KabuSys/documents/08_Operations/Monitoring.md:202)

ここでも `Strategy Lab` や `LINE`、AI 分析が通常導線の中に出てくる。

### 2.4 障害対応文書

- [E_FailureRecovery.md](/C:/Users/tetsu/Projects/KabuSys/documents/WebManual/E_FailureRecovery.md:245)

ここは比較的整理されていて、AI 分析を省略可能と書けている。  
`Core` 基準化では、この書き方を他ページにも広げるのがよい。

## 3. 基本方針

`Issue 5` で採る整理方針は次のとおり。

### 3.1 外さないもの

- `Addon` 設定項目
- `Addon` ジョブ
- `Addon` 関連ページ名

理由:

- ユーザが参照する文書を増やしすぎないため
- `Core` 購入後に必要に応じて `Addon` へ進む導線を 1 つの文書で見せるため

### 3.2 区分表示するもの

- 設定一覧
- Task Scheduler 一覧
- セットアップ完了チェック
- 運用ページ一覧

区分は次を基本にする。

- `Core 必須`
- `Core 任意`
- `Addon 任意`

### 3.3 避けるもの

- `Core` と `Addon` を同列に見せること
- `Addon` 未設定だと `Core` が不足しているように見える書き方
- `Core` 導線の途中で `Addon` を必須のように見せること

## 4. Core 文書に残すべき内容

### 4.1 WebManual 入口

`Core` の入口には次だけを残す。

- KabuSys の概要
- `Core` でできること
- `Core` の基本ページ
- `paper_trading` までの導線
- `live` までの導線

### 4.2 Core Setup

`Core` セットアップ文書には次だけを残す。

- リポジトリ取得
- 仮想環境
- `.env` の基本設定
- `validate_config`
- DB 初期化
- J-Quants bootstrap
- Core 用 Task Scheduler
- `paper_trading` 開始までの確認

### 4.3 Core 運用

`Core` 運用文書には次だけを残す。

- `Home`
- `WebManual`
- `Signal Queue`
- `Performance`
- pre-market / execution / monitoring / market close の基本レポート
- kill switch / PID / risk logs / signal queue の基本確認

## 5. Addon 導線に逃がすべき内容

### 5.1 AI Addon

- AI センチメント設定
- OpenAI API キー設定
- `run_ai_analysis.py`
- `ai_scores` / `market_regime` の解説

### 5.2 Notification Addon

- LINE 通知設定
- LINE 認証情報
- 通知テスト手順

### 5.3 Disclosure Addon

- TDnet 設定
- EDINET 設定
- `run_tdnet_collection.py`
- `run_edinet_collection.py`
- `run_disclosure_classification.py`

### 5.4 News Source Addon

- Yahoo News RSS 設定
- `run_yahoonews_collection.py`

### 5.5 Operations UI / Premium Analytics Addon

- `Strategy Lab`
- 将来の強化 UI
- 高度な比較分析

## 6. 文書別の整理方針

### 6.1 `INDEX.md`

残すもの:

- `Core` 利用者向けの読む順番
- `Core` 主要ページへの案内

避けるもの:

- `Addon` を `Core` と同列の前提にする説明
- `Addon` 前提の読み順

### 6.2 `A_Overview.md`

残すもの:

- `Core` 概要
- `Core` の運用フロー
- `Home / WebManual / Signal Queue / Performance`

見直すもの:

- `Strategy Lab` の扱い
- AI を標準要素に見せる記述
- `Core 標準ページ` と `Addon ページ` の区分表示

### 6.3 `B_CoreSetup.md`

残すもの:

- `Core` 必須設定
- `Core` ジョブ
- `Core` セットアップチェック
- `Addon` 設定項目
- `Addon` ジョブ
- `Addon` 完了チェック

見直し方針:

- 設定一覧を `Core 必須 / Core 任意 / Addon 任意` に分ける
- Task Scheduler 一覧を `Core 標準ジョブ / Addon 有効時のみ動くジョブ` に分ける
- 完了チェックを `Core` と `Addon` に分ける
- `Addon` 項目には「未設定でも Core は動く」を明記する

### 6.4 `D_LiveOperation.md`

残すもの:

- `Core` 運用ページ
- 基本レポート
- 基本監視導線

切り分け対象:

- `Strategy Lab`
- AI 分析を前提にした説明

見直し方針:

- `Core 標準導線` と `Addon 導線` を同じ文書内で分けて書く

### 6.5 `Monitoring.md`

残すもの:

- `Home / Signal Queue / Performance`
- 基本的な監視 DB の説明

切り分け対象:

- `Strategy Lab`
- LINE 通知アーキテクチャの詳細

見直し方針:

- `Core 監視ページ` と `Addon 監視拡張` を区分表示する
- LINE は `Addon 通知` として明示する

## 7. 表記ルール

`Core` 基準化では、文書内の表記も揃える必要がある。

### 7.1 Core 文書での書き方

- `Core で標準提供`
- `Core 単体で利用可能`
- `Core 機能`

### 7.2 Addon 文書での書き方

- `Addon 機能`
- `別途導入時のみ有効`
- `Core 未導入時には不要`

### 7.3 移行期の書き方

`Core` 文書側では、`Addon` について触れるとしても次の粒度に留める。

- 「必要なら Addon 側で有効化可能」
- 「詳細は Addon 文書へ」

逆に、`Core` 文書内にある `Addon` 情報は削除せず、区分ラベルで誤解を防ぐ方がよい。

## 8. 推奨レイアウト

### 8.1 Core 側

- `INDEX.md`
- `A_Overview.md`
- `B_CoreSetup.md`
- `C_PaperTrading.md`
- `D_LiveOperation.md`
- `E_FailureRecovery.md`

### 8.2 Addon 側に将来分離する候補

- `Addon_AI.md`
- `Addon_Notification.md`
- `Addon_Disclosure.md`
- `Addon_News.md`
- `Addon_AdvancedUI.md`

現時点では新設しなくてもよいが、少なくとも `Core` 文書側では「後で逃がせる構造」にするのが重要。

## 9. 優先順位

文書整理の優先順位は次が妥当。

1. `B_CoreSetup.md` の設定一覧と Task Scheduler 一覧を区分表示にする
2. `B_CoreSetup.md` の完了チェックを `Core / Addon` に分ける
3. `A_Overview.md` のページ一覧を `Core 標準 / Addon` に分ける
4. `D_LiveOperation.md` と `Monitoring.md` の運用ページ説明を区分表示にする
5. `INDEX.md` の読み順を `Core` 基準で固定する

## 10. この Issue での成果

この `Issue 5` では、まだ文書本文は修正しない。  
成果物は次の 3 点。

- `Core` 文書に残す範囲
- `Addon` 情報を残したまま区分表示する方針
- `Addon` 文書へ逃がす範囲
- `Core` 利用者が迷わない読み順の判断基準

## 11. 関連

- [TODO_CoreAddonRepoSplit.md](/C:/Users/tetsu/Projects/KabuSys/documents/00_Architecture/TODO_CoreAddonRepoSplit.md)
- [TODO_CoreAddonResponsibilityMatrix.md](/C:/Users/tetsu/Projects/KabuSys/documents/00_Architecture/TODO_CoreAddonResponsibilityMatrix.md)
- [TODO_CoreAddonExtensionPoints.md](/C:/Users/tetsu/Projects/KabuSys/documents/00_Architecture/TODO_CoreAddonExtensionPoints.md)
- [TODO_CoreAddonImportBoundaryAudit.md](/C:/Users/tetsu/Projects/KabuSys/documents/00_Architecture/TODO_CoreAddonImportBoundaryAudit.md)
- [TODO_CoreAddonConfigSeparationPlan.md](/C:/Users/tetsu/Projects/KabuSys/documents/00_Architecture/TODO_CoreAddonConfigSeparationPlan.md)
