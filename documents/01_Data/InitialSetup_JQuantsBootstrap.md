# 初回セットアップ手順: J-Quants CSV 一括取り込み

- 対象: KabuSys の初回環境構築を行うユーザー
- 目的: J-Quants から大量データを CSV で取得し、KabuSys の初期データ基盤を構築する
- 前提: 通常の日次差分更新ではなく、初回のみ行う bootstrap 作業である

---

## 1. この作業で何をするか

初回セットアップでは、J-Quants から過去の大量データを CSV で取得し、KabuSys に一括投入します。

この作業の目的は次の通りです。

- バックテストに必要な過去データを揃える
- 実運用開始前の基礎データを揃える
- 通常運用の日次差分更新へ移行できる状態を作る

この作業は、毎日の夜間バッチとは別です。  
初回導入時、または環境を再構築するときに実施します。

---

## 2. 事前に準備するもの

作業前に以下を準備してください。

- J-Quants を利用できること
- KabuSys の作業ディレクトリが用意されていること
- データ保存先に十分な空き容量があること
- DuckDB など、KabuSys が使用する DB ファイルの保存先が決まっていること

最低限、以下のデータを対象にします。

- 株価（日足 OHLCV）
- 銘柄マスタ
- 財務データ
- JPX カレンダー

### 補足

現時点では、**通常運用用の差分更新コマンド** は存在しますが、**CSV bootstrap 専用コマンドは未実装** の可能性があります。

存在確認できている既存コマンド:

- `python scripts/generate_config.py`
- `python scripts/run_data_update.py`
- `python scripts/run_feature_gen.py`

この手順書では、以下を分けて記載します。

- 今すぐ実行可能な準備コマンド
- bootstrap 実装後に使う想定コマンド

---

## 3. ディレクトリ構成

初回セットアップでは、CSV を以下のような場所に保存する想定です。

```text
data/bootstrap/raw/jquants/
  prices/{取得日}/
  listed_info/{取得日}/
  financials/{取得日}/
  calendar/{取得日}/
```

例:

```text
data/bootstrap/raw/jquants/prices/2026-04-21/
data/bootstrap/raw/jquants/listed_info/2026-04-21/
data/bootstrap/raw/jquants/financials/2026-04-21/
data/bootstrap/raw/jquants/calendar/2026-04-21/
```

ポイント:

- データ種別ごとに分ける
- 取得日ごとに分ける
- 元 CSV はそのまま保持する

### PowerShell での作成例

プロジェクトルートで以下を実行します。

```powershell
New-Item -ItemType Directory -Force data\bootstrap\raw\jquants\prices\2026-04-21
New-Item -ItemType Directory -Force data\bootstrap\raw\jquants\listed_info\2026-04-21
New-Item -ItemType Directory -Force data\bootstrap\raw\jquants\financials\2026-04-21
New-Item -ItemType Directory -Force data\bootstrap\raw\jquants\calendar\2026-04-21
```

---

## 4. 作業の全体フロー

初回セットアップは次の順で行います。

1. J-Quants から CSV をダウンロードする
2. CSV を所定ディレクトリに配置する
3. bootstrap 取り込みを実行する
4. 取込結果を確認する
5. 通常の日次差分更新へ移行する

### 推奨する実行順

```powershell
# 1. プロジェクトルートへ移動
Set-Location C:\Users\tetsu\Projects\KabuSys

# 2. config テンプレート生成（未作成時のみ）
python scripts\generate_config.py

# 3. Raw 配置用ディレクトリ作成
New-Item -ItemType Directory -Force data\bootstrap\raw\jquants\prices\2026-04-21
New-Item -ItemType Directory -Force data\bootstrap\raw\jquants\listed_info\2026-04-21
New-Item -ItemType Directory -Force data\bootstrap\raw\jquants\financials\2026-04-21
New-Item -ItemType Directory -Force data\bootstrap\raw\jquants\calendar\2026-04-21

# 4. CSV を配置
# 5. bootstrap 実行（実装後）
# 6. 取込結果確認
```

---

## 5. Step 1: J-Quants から CSV をダウンロードする

J-Quants から、初回投入に必要な CSV を取得します。

対象:

- 株価（日足）
- 銘柄マスタ
- 財務データ
- カレンダー

ダウンロード時の注意:

- どのデータ種別か分かるファイル名にする
- 取得日を記録する
- 取得した CSV は編集しない
- 可能ならダウンロード元情報も控える

推奨:

- 取得した CSV は、解凍後の元ファイルをそのまま保管する
- 取得日をディレクトリ名に含める

### ユーザー作業メモ

J-Quants 側のダウンロード操作自体は Web 画面または提供手段に依存するため、本手順書では KabuSys 側の配置以降を対象とします。

---

## 6. Step 2: CSV を所定ディレクトリに配置する

ダウンロードした CSV を、データ種別ごとのディレクトリに配置します。

配置例:

```text
data/bootstrap/raw/jquants/prices/2026-04-21/prices_daily.csv
data/bootstrap/raw/jquants/listed_info/2026-04-21/listed_info.csv
data/bootstrap/raw/jquants/financials/2026-04-21/financials.csv
data/bootstrap/raw/jquants/calendar/2026-04-21/market_calendar.csv
```

確認ポイント:

- 想定したデータ種別のディレクトリに入っているか
- ファイルが壊れていないか
- 文字コードや拡張子が想定通りか

### PowerShell での配置例

以下は `Downloads` にある CSV を移動する例です。

```powershell
Move-Item -LiteralPath "$HOME\Downloads\prices_daily.csv" `
  -Destination "data\bootstrap\raw\jquants\prices\2026-04-21\prices_daily.csv"

Move-Item -LiteralPath "$HOME\Downloads\listed_info.csv" `
  -Destination "data\bootstrap\raw\jquants\listed_info\2026-04-21\listed_info.csv"

Move-Item -LiteralPath "$HOME\Downloads\financials.csv" `
  -Destination "data\bootstrap\raw\jquants\financials\2026-04-21\financials.csv"

Move-Item -LiteralPath "$HOME\Downloads\market_calendar.csv" `
  -Destination "data\bootstrap\raw\jquants\calendar\2026-04-21\market_calendar.csv"
```

配置後に一覧確認します。

```powershell
Get-ChildItem -Recurse data\bootstrap\raw\jquants
```

---

## 7. Step 3: bootstrap 取り込みを実行する

CSV 配置後、bootstrap 取り込み処理を実行します。

この処理では、以下が行われます。

1. CSV の存在確認
2. ヘッダ・必須列の検証
3. Raw として保存または登録
4. Processed テーブルへ整形投入
5. 完了結果の記録

実行イメージ:

```text
bootstrap 実行
  -> CSV 検証
  -> Raw 取込
  -> Processed 変換
  -> 完了記録
```

注意:

- 初回は時間がかかる可能性があります
- 途中で止まっても、冪等に再実行できる設計を前提とします
- 同じ CSV を再投入しても重複しないことが理想です

### 現時点の注意

現時点では、CSV bootstrap 専用の実行スクリプトはリポジトリ上で確認できていません。  
そのため、この手順は **実装予定コマンドを含む暫定版** です。

### 想定コマンド案

bootstrap 実装後は、以下のようなコマンドで実行する想定です。

```powershell
python scripts\run_jquants_csv_bootstrap.py `
  --input-root data\bootstrap\raw\jquants `
  --as-of 2026-04-21 `
  --duckdb data\kabusys.duckdb
```

または、データ種別ごとに分割して実行できる形でもよいです。

```powershell
python scripts\run_jquants_csv_bootstrap.py `
  --dataset prices `
  --input-dir data\bootstrap\raw\jquants\prices\2026-04-21 `
  --duckdb data\kabusys.duckdb

python scripts\run_jquants_csv_bootstrap.py `
  --dataset listed_info `
  --input-dir data\bootstrap\raw\jquants\listed_info\2026-04-21 `
  --duckdb data\kabusys.duckdb
```

### 既存コマンドとの関係

以下のコマンドは **bootstrap の代替ではありません**。

```powershell
python scripts\run_data_update.py
python scripts\run_feature_gen.py
```

- `run_data_update.py`
  - 通常運用用の日次差分更新
- `run_feature_gen.py`
  - `prices_daily` 投入後に特徴量を生成する通常バッチ

bootstrap 完了後に `run_feature_gen.py` を使う可能性はありますが、CSV 一括投入そのものは別コマンドに分離すべきです。

---

## 8. Step 4: 取込結果を確認する

bootstrap 完了後、ユーザーは以下を確認してください。

### 8.1 取込成功の確認

- 取り込み処理が正常終了している
- 失敗ログが出ていない
- データ種別ごとの件数が妥当である

### 想定ログ確認コマンド

bootstrap 実装後は、専用ログを確認する想定です。

```powershell
Get-Content logs\jquants_csv_bootstrap.log -Tail 100
Select-String -Path logs\jquants_csv_bootstrap.log -Pattern "ERROR|CRITICAL|WARNING"
```

### 8.2 テーブル確認

最低限、以下を確認します。

- `prices_daily`
- `stocks`
- `financials` 系
- `market_calendar`

確認したい内容:

- データが空ではない
- 日付範囲が想定通り
- 銘柄コードが正しく入っている
- 明らかな欠損や重複がない

### DuckDB での確認例

```powershell
duckdb data\kabusys.duckdb "SELECT MIN(date), MAX(date), COUNT(*) FROM prices_daily;"
duckdb data\kabusys.duckdb "SELECT COUNT(*) FROM stocks;"
duckdb data\kabusys.duckdb "SELECT COUNT(*) FROM fundamentals;"
duckdb data\kabusys.duckdb "SELECT MIN(date), MAX(date), COUNT(*) FROM market_calendar;"
```

サンプル行確認:

```powershell
duckdb data\kabusys.duckdb "SELECT * FROM prices_daily ORDER BY date DESC, code LIMIT 20;"
duckdb data\kabusys.duckdb "SELECT * FROM stocks ORDER BY code LIMIT 20;"
```

### 8.3 バックテスト利用可否

最低限、バックテストに必要な履歴長が確保されているかを確認します。

例:

- 過去数年分の日足が揃っている
- 銘柄マスタが投入済み
- カレンダーが揃っている

### 特徴量生成まで進める場合

`prices_daily` まで投入できた後に、特徴量生成を試す場合は既存コマンドを利用できます。

```powershell
python scripts\run_feature_gen.py
```

確認例:

```powershell
duckdb data\kabusys.duckdb "SELECT MAX(date), COUNT(*) FROM features;"
```

---

## 9. Step 5: 通常運用へ移行する

初回 bootstrap が完了したら、通常運用では API ベースの日次差分更新へ移行します。

ここで確認すること:

- bootstrap の最終投入日
- その翌日以降を差分更新対象にできること
- 初回差分更新で重複が発生しないこと

考え方:

- bootstrap は「土台作り」
- 日次差分更新は「継続運用」

この 2 つを混同しないでください。

### 通常差分更新の確認コマンド

bootstrap 完了後、通常差分更新が動くかを確認する場合は既存の日次更新コマンドを使います。

```powershell
python scripts\run_data_update.py
```

その後、必要に応じて特徴量再生成を行います。

```powershell
python scripts\run_feature_gen.py
```

---

## 10. 失敗したときの対応

想定される失敗例:

- CSV が壊れている
- 列が足りない
- 型が不正
- 日付形式が異なる
- ディスク容量不足
- 処理途中で停止した

基本対応:

1. エラーログを確認する
2. 失敗したデータ種別を特定する
3. CSV 配置や内容を見直す
4. 必要なら該当データ種別のみ再実行する

重要:

- 元 CSV を直接編集しない
- 失敗時でも元ファイルは保持する
- 再実行前に何がどこまで入ったかを確認する

### 再実行の考え方

bootstrap 実装後の想定コマンド:

```powershell
python scripts\run_jquants_csv_bootstrap.py `
  --input-root data\bootstrap\raw\jquants `
  --as-of 2026-04-21 `
  --duckdb data\kabusys.duckdb `
  --resume
```

または、失敗したデータ種別のみ再実行します。

```powershell
python scripts\run_jquants_csv_bootstrap.py `
  --dataset financials `
  --input-dir data\bootstrap\raw\jquants\financials\2026-04-21 `
  --duckdb data\kabusys.duckdb
```

---

## 11. ユーザー向けチェックリスト

### 作業前

- `Set-Location C:\Users\tetsu\Projects\KabuSys` を実行した
- `python scripts\generate_config.py` を実行した、または `config/` が既にある
- J-Quants にアクセスできる
- 空き容量が十分ある
- 保存先ディレクトリを確認した

### ダウンロード後

- 株価 CSV を取得した
- 銘柄マスタ CSV を取得した
- 財務 CSV を取得した
- カレンダー CSV を取得した

### 配置後

- データ種別ごとの所定ディレクトリに配置した
- ファイル名と取得日が分かる
- `Get-ChildItem -Recurse data\bootstrap\raw\jquants` で配置確認した

### 取り込み後

- bootstrap が正常終了した
- `prices_daily` にデータが入った
- `stocks` にデータが入った
- `financials` 系にデータが入った
- `market_calendar` にデータが入った
- 必要なら `python scripts\run_feature_gen.py` で特徴量生成を確認した

### 移行前

- bootstrap の最終日を確認した
- 通常差分更新へ移行できる状態である

---

## 12. まとめ

初回セットアップでは、J-Quants の大量データを CSV で取得し、bootstrap として一括投入します。

ポイントは次の通りです。

- 初回取り込みは通常運用とは別処理と考える
- CSV は Raw として保持する
- 取り込み後は必ずテーブル内容を確認する
- その後、通常の日次差分更新へ移行する

この手順を守ることで、KabuSys のバックテストと実運用の土台となる初期データ基盤を安全に構築できます。
