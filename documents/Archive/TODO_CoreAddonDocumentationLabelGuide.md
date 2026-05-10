# Core Documentation Label Guide

`Issue 5` の補助資料として、`Core` / `Addon` を区分表示するための見出し名と表示ラベルを固定する。

目的は 1 つ。

- 文書ごとに言い方がぶれないようにする

このガイドは、特に次の文書で使う前提。

- [B_CoreSetup.md](/C:/Users/tetsu/Projects/KabuSys/documents/WebManual/B_CoreSetup.md)
- [A_Overview.md](/C:/Users/tetsu/Projects/KabuSys/documents/WebManual/A_Overview.md)
- [D_LiveOperation.md](/C:/Users/tetsu/Projects/KabuSys/documents/WebManual/D_LiveOperation.md)
- [Monitoring.md](/C:/Users/tetsu/Projects/KabuSys/documents/08_Operations/Monitoring.md)

## 1. 基本ルール

区分の軸は次の 2 つだけに統一する。

- `Core` か `Addon` か
- `必須` か `任意` か

避けるべき表現は次。

- `オプション`
- `拡張`
- `高度`
- `プレミアム`

理由:

- 商品設計や販売文脈では意味があるが、セットアップ文書では区分基準が曖昧になるため

## 2. 設定一覧で使うラベル

設定項目の区分は次で固定する。

- `Core 必須`
- `Core 任意`
- `Addon 任意`

### 2.1 意味

`Core 必須`

- `Core` 単体で動かすために必要

`Core 任意`

- `Core` で使うが、未設定でもデフォルトや別経路で成立する

`Addon 任意`

- `Addon` 導入時だけ意味を持つ
- 未設定でも `Core` は正常に動く

### 2.2 使い方

見出し例:

- `Core 必須設定`
- `Core 任意設定`
- `Addon 任意設定`

表の列ラベル例:

- `区分`
- `用途`
- `例`

## 3. ジョブ一覧で使うラベル

Task Scheduler やバッチ一覧の区分は次で固定する。

- `Core 標準ジョブ`
- `Addon 有効時のみ動くジョブ`

### 3.1 意味

`Core 標準ジョブ`

- `Core` の通常運用で前提となるジョブ

`Addon 有効時のみ動くジョブ`

- 対応する `Addon` を有効化したときだけ実行意味があるジョブ

### 3.2 使い方

見出し例:

- `Core 標準ジョブ一覧`
- `Addon 有効時のみ動くジョブ一覧`

補足文の定型:

- `未設定でも Core の売買フローには影響しません`

## 4. 完了チェックで使うラベル

セットアップや導入確認の区分は次で固定する。

- `Core 完了チェック`
- `Addon 追加チェック`

### 4.1 意味

`Core 完了チェック`

- ここまで通れば `Core` は使い始められる

`Addon 追加チェック`

- `Addon` を有効化した場合だけ追加で確認する

### 4.2 使い方

見出し例:

- `Core セットアップ完了チェック`
- `Addon 有効化時の追加チェック`

## 5. ページ一覧で使うラベル

Streamlit や運用ページの案内では次で固定する。

- `Core 標準ページ`
- `Addon ページ`

### 5.1 意味

`Core 標準ページ`

- `Core` 利用者が標準で見るページ

`Addon ページ`

- 分析強化や追加導線として使うページ

### 5.2 使い方

見出し例:

- `Core 標準ページ`
- `Addon ページ`

対象例:

- `Core 標準ページ`: `Home`, `WebManual`, `Signal Queue`, `Performance`
- `Addon ページ`: `Strategy Lab`

## 6. 本文中の補足文テンプレート

文書本文では、次の定型を優先して使う。

### 6.1 Addon 項目の説明

- `Addon 任意機能です`
- `未設定でも Core は動作します`
- `必要な場合のみ有効化してください`

### 6.2 Core 項目の説明

- `Core の標準導線です`
- `Core 利用時の前提です`
- `最初にここまで完了してください`

### 6.3 避ける言い方

- `あとで余裕があれば`
- `上級者向け`
- `必要に応じて`

これらは意味が曖昧で、セットアップ要否が伝わりにくい。

## 7. 文書別の適用イメージ

### 7.1 `B_CoreSetup.md`

使うラベル:

- `Core 必須設定`
- `Core 任意設定`
- `Addon 任意設定`
- `Core 標準ジョブ一覧`
- `Addon 有効時のみ動くジョブ一覧`
- `Core セットアップ完了チェック`
- `Addon 有効化時の追加チェック`

### 7.2 `A_Overview.md`

使うラベル:

- `Core 標準ページ`
- `Addon ページ`

### 7.3 `D_LiveOperation.md`

使うラベル:

- `Core 標準導線`
- `Addon 導線`

### 7.4 `Monitoring.md`

使うラベル:

- `Core 標準ページ`
- `Addon ページ`
- `Addon 任意機能`

## 8. このガイドの使い方

今後 `Issue 5` で本文を修正するときは、まずこのガイドのラベルに合わせる。  
新しい言い方を足すのではなく、既存ラベルへ寄せる。

## 9. 関連

- [TODO_CoreAddonDocumentationBaselinePlan.md](/C:/Users/tetsu/Projects/KabuSys/documents/00_Architecture/TODO_CoreAddonDocumentationBaselinePlan.md)
- [TODO_CoreAddonConfigSeparationPlan.md](/C:/Users/tetsu/Projects/KabuSys/documents/00_Architecture/TODO_CoreAddonConfigSeparationPlan.md)
- [TODO_CoreAddonRepoSplit.md](/C:/Users/tetsu/Projects/KabuSys/documents/00_Architecture/TODO_CoreAddonRepoSplit.md)
