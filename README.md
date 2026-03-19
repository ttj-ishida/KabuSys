# KabuSys

日本株向け自動売買プラットフォームのライブラリ群（KabuSys）。  
データ収集（J-Quants / RSS）、DuckDB スキーマ管理、ETL パイプライン、研究用ファクター計算、ニュース解析、監査ログなど、量的運用に必要な基盤機能を提供します。

---

## 主な特徴（機能一覧）
- J-Quants API クライアント（ページネーション / リトライ / トークン自動リフレッシュ / レート制御）
- DuckDB ベースのスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- RSS ベースのニュース収集（正規化・SSRF 対策・トラッキング除去・銘柄紐付け）
- 研究用モジュール（ファクター計算：Momentum / Volatility / Value、IC 計算、将来リターン計算）
- 統計ユーティリティ（Zスコア正規化 等）
- 監査ログスキーマ（シグナル→発注→約定のトレーサビリティ）
- 設定管理（.env 自動読み込み / 必須環境変数チェック / 実行環境フラグ）

---

## 必要要件
- Python 3.10 以上（PEP 604 の `|` 型注釈等を使用）
- DuckDB（Python パッケージ: `duckdb`）
- defusedxml（RSS XML パースの安全化）

推奨インストール（pip）:
```
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# 本プロジェクトを開発インストールする場合:
pip install -e .
```

（プロジェクトに requirements.txt / pyproject があればそちらからインストールしてください）

---

## 環境変数（設定）
このパッケージは .env ファイルまたは OS 環境変数から設定を読み込みます。自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われ、以下の主要設定が利用されます。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — 実行環境 (development | paper_trading | live) （デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL) （デフォルト: INFO）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB パス（デフォルト: data/monitoring.db）

自動 .env 読み込みの無効化:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト等で便利です）。

設定取得は `from kabusys.config import settings` で可能です（プロパティで必須チェックを行います）。

---

## セットアップ手順（簡易）
1. リポジトリをクローン:
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化:
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール:
   ```
   pip install duckdb defusedxml
   # またはプロジェクトをインストール:
   pip install -e .
   ```

4. .env ファイルを作成（リポジトリの .env.example を参照）:
   ```
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   # 必要に応じて DUCKDB_PATH 等も設定
   ```

5. DuckDB スキーマ初期化（例）:
   Python REPL やスクリプトで:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```

---

## 使い方（主要な API 例）

- DuckDB スキーマ初期化
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 市場カレンダー更新ジョブ
  ```python
  from kabusys.data import calendar_management
  saved = calendar_management.calendar_update_job(conn)
  print("saved", saved)
  ```

- ニュース収集（RSS）と DB 保存
  ```python
  from kabusys.data.news_collector import run_news_collection
  # known_codes は既知の銘柄コード集合（抽出用）
  res = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
  print(res)
  ```

- J-Quants から日次株価を手動取得して保存（テスト・デバッグ）
  ```python
  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  ```

- 研究/ファクター計算の利用例
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2024, 1, 31)

  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

  # 例: mom と fwd から IC を計算
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)

  # 統計サマリー
  summary = factor_summary(mom, ["mom_1m", "ma200_dev"])
  ```

---

## ディレクトリ構成（主要ファイル）
リポジトリの主要モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py             — RSS ニュース収集 / 前処理 / DB保存
    - schema.py                     — DuckDB スキーマ定義と init_schema()
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETL ユーティリティ公開（ETLResult）
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - features.py                    — 特徴量ユーティリティ公開
    - calendar_management.py        — マーケットカレンダー管理
    - audit.py                      — 監査ログスキーマ初期化
    - (その他)
  - research/
    - __init__.py
    - feature_exploration.py        — 将来リターン / IC / サマリー
    - factor_research.py            — Momentum/Volatility/Value の実装
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（上記は現状の主要モジュールを抜粋したものです）

---

## 実装上の注意 / 開発メモ
- settings（kabusys.config.Settings）は実行時に環境変数の妥当性チェック（必須変数未設定、KABUSYS_ENV 値検証、LOG_LEVEL 等）を行います。
- .env の自動読み込み順序: OS 環境変数 > .env.local > .env。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- J-Quants クライアントは 120 req/min のレート制御を実装し、リトライ/指数バックオフ、401 時のトークン自動更新をサポートします。
- RSS フェッチは SSRF・XML Bomb 対策（ホスト検証、受信サイズ制限、defusedxml、gzip 解凍後サイズ確認）を実装しています。
- DuckDB の DDL は冪等（CREATE TABLE IF NOT EXISTS）です。init_schema() は存在しなければ親ディレクトリを作成します。
- 監査ログ（audit）はタイムゾーンを UTC に固定することを想定しています（init_audit_schema は SET TimeZone='UTC' を実行）。

---

## 今後の拡張案（例）
- Strategy 層の具体的なアルゴリズム実装・バックテストフレームワーク統合
- 発注実行（kabuステーション）との接続・エラー処理の強化
- CI 用のテストスイート・型チェック・Lint の追加
- Docker ベースの実行環境定義（ETL バッチ / 夜間ジョブ）

---

質問・使い方の追加サンプルや、README の英訳／詳細化が必要であれば教えてください。