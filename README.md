# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。市場データの取得（J-Quants）、DuckDB によるデータ永続化、データ品質チェック、特徴量計算、ニュース収集、監査ログ等の機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は、J-Quants 等のデータソースから日本株データを収集・保存し、
戦略用の特徴量を計算・正規化するためのモジュール群を備えたプロジェクトです。

設計のポイント:
- DuckDB をバックエンドにして効率的な分析と永続化を行う
- ETL は差分更新／バックフィルをサポートし冪等に保存（ON CONFLICT を利用）
- 品質チェック（欠損、スパイク、重複、日付不整合）を行い、問題を収集して報告
- ニュース（RSS）収集において SSRF や XML Bomb 等のセキュリティ対策を実装
- 発注／監査関連テーブルを含むスキーマを提供（監査ログは別 DB に分離可能）
- Research モジュールは prices_daily / raw_financials のみ参照し、実際の発注には影響しない

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants 接続およびデータ取得（株価日足、財務、マーケットカレンダー）
  - 保存関数は冪等（ON CONFLICT DO UPDATE / DO NOTHING）で DuckDB に保存
  - rate limit / retry / token refresh 対応

- ETL パイプライン
  - run_daily_etl: カレンダー、株価、財務の差分ETLと品質チェックを一括実行
  - 差分計算・バックフィルロジックを内蔵

- データ品質チェック
  - 欠損、スパイク（前日比閾値）、重複、日付不整合を検出
  - QualityIssue のリストで結果を返す

- ニュース収集
  - RSS から記事抽出、前処理、重複除去、記事ID生成（正規化URLの SHA-256）
  - 記事 → 銘柄コードの紐付け（known_codes を用いる）

- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマンランク相関）、統計サマリー
  - z-score 正規化ユーティリティ（data.stats）

- スキーマ & 監査
  - DuckDB のスキーマ定義と初期化（raw / processed / feature / execution 層）
  - 監査ログ（signal_events / order_requests / executions）用の初期化 API

- 設定管理
  - .env（.env.local）や環境変数から設定を自動読み込み
  - 必須設定が欠けている場合は明示的にエラーを出す

---

## 必要な環境 / 依存ライブラリ

必須:
- Python 3.9+（型表記で | を使用しているため 3.10 以上を推奨）
- duckdb
- defusedxml

例（pip）:
pip install duckdb defusedxml

パッケージが pyproject.toml 等で管理されていれば:
pip install -e .

（プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

---

## 環境変数 / 設定

自動的にプロジェクトルート（.git または pyproject.toml）を探索し、`.env` と `.env.local` を読み込みます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（必須は README 中で明示）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード（発注関連）
- KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

.env の例:
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG

設定は `from kabusys.config import settings` から参照できます（プロパティとして提供）。

---

## セットアップ手順（簡易）

1. Python 環境を用意（推奨: 仮想環境）
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （必要に応じて他ライブラリを追加）

3. ソースをインストール（プロジェクトルートに pyproject.toml/setup がある場合）
   - pip install -e .

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境に直接設定

5. DuckDB スキーマ初期化
   - Python からスキーマを作成します（親ディレクトリは自動生成されます）:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

6. （必要に応じて）監査 DB 初期化
   - from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/audit.duckdb")

---

## 使い方（主要な例）

- DuckDB スキーマ初期化
  ```
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行
  ```
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  # conn は init_schema で作成した接続
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
  ```
  from kabusys.data.news_collector import run_news_collection
  # known_codes は既知の銘柄コードセット（DB 等から取得）
  known_codes = {"7203", "6758", ...}
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- ファクター計算／研究ユーティリティ
  ```
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

  target = date(2025, 3, 1)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)

  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  summary = factor_summary(mom, ["mom_1m","mom_3m","mom_6m","ma200_dev"])
  ```

- z-score 正規化
  ```
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, ["mom_1m","atr_pct"])
  ```

- J-Quants API の直接呼び出し例
  ```
  from kabusys.data.jquants_client import fetch_daily_quotes
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

注意:
- research の関数群は prices_daily / raw_financials のみ参照し、実際の売買 API にはアクセスしない設計です（安全）。
- jquants_client はレート制限、リトライ、401 時のトークン自動リフレッシュを扱います。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュール構成です（抜粋）:

- kabusys/
  - __init__.py                     (バージョンなど)
  - config.py                       (環境変数 / 設定読み込み)
  - data/
    - __init__.py
    - jquants_client.py              (J-Quants API クライアント、取得・保存)
    - news_collector.py              (RSS 収集・保存・銘柄抽出)
    - schema.py                      (DuckDB スキーマ定義・初期化)
    - stats.py                       (z-score 等の統計ユーティリティ)
    - pipeline.py                    (ETL パイプライン: run_daily_etl 等)
    - features.py                    (特徴量ユーティリティ公開)
    - calendar_management.py         (マーケットカレンダー管理)
    - audit.py                       (監査ログ用スキーマ初期化)
    - etl.py                         (ETL 結果型の公開)
    - quality.py                     (データ品質チェック)
  - research/
    - __init__.py
    - feature_exploration.py         (将来リターン、IC、統計サマリー)
    - factor_research.py             (momentum/volatility/value 等の計算)
  - strategy/                        (戦略層のプレースホルダ)
  - execution/                       (発注 / execution 層のプレースホルダ)
  - monitoring/                      (監視用のプレースホルダ)

（ソースツリーにはさらに細かい実装が含まれます。README は主要な利用方法を示しています。）

---

## 注意事項 / 補足

- セキュリティ: RSS パーシングは defusedxml を使用しており、HTTP リダイレクト先のホストを検証して SSRF を防止します。news_collector は受信上限バイト数や gzip 解凍後のサイズチェックも実装しています。
- 冪等性: データ保存は可能な限り ON CONFLICT を用い冪等に実装されています（save_* 系関数）。
- テスト: config の自動 .env 読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト時に有用）。
- DuckDB の初期化により親ディレクトリが自動作成されます。メモリ DB は ":memory:" を指定できます。
- 実運用での発注機能を使う場合は、KABU 系の設定（API パスワードや URL）および監査ログのの運用を十分に検討してください。

---

この README はコードベースの概要と代表的な利用方法をまとめたものです。API の詳細や追加のユーティリティは各モジュールの docstring（ソース内コメント）を参照してください。必要であればサンプルスクリプトや CLI 用の起動手順を追加で用意します。