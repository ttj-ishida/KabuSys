# KabuSys

日本株向け自動売買／データプラットフォーム用ライブラリ（KabuSys）。  
データ取得（J-Quants）、DuckDB ベースのスキーマ管理、ETL パイプライン、データ品質チェック、ファクター計算・特徴量生成、ニュース収集、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム・研究基盤向けの内部ライブラリ群です。設計上のポイントは次のとおりです。

- DuckDB を用いたローカルデータレイク（Raw / Processed / Feature / Execution 層）のスキーマを提供
- J-Quants API クライアントを通じた株価・財務・マーケットカレンダーの差分取得（レート制御・リトライ・トークン自動更新対応）
- ETL（差分更新、バックフィル、品質チェック）パイプライン
- ニュース RSS 収集器（SSRF 対策、トラッキングパラメータ除去、記事IDは正規化URLのハッシュ）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー）と特徴量探索（将来リターン・IC・統計サマリー）
- 監査（audit）用スキーマ：シグナル→発注→約定 をトレース可能にするテーブル群
- データ品質チェック（欠損、スパイク、重複、日付不整合）

本ライブラリは本番発注やブローカー API への直接アクセスを伴わないデータ処理 / 研究ロジック部分が中心です（発注層は別モジュールで扱う想定）。

---

## 主な機能一覧

- 環境設定読み込み・管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルート判定）
  - 必須設定の取得ユーティリティ
- J-Quants API クライアント（kabusys.data.jquants_client）
  - レート制御、リトライ、トークン自動リフレッシュ
  - 日足 / 財務 / カレンダー取得、DuckDB への冪等保存関数
- DuckDB スキーマ管理（kabusys.data.schema）
  - init_schema() によるテーブル作成（Raw/Processed/Feature/Execution 層）
  - インデックス作成
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl(): カレンダー・株価・財務の差分取得と品質チェック
  - 個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
- データ品質チェック（kabusys.data.quality）
  - 欠損 / スパイク / 重複 / 日付不整合検出
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理、raw_news への冪等保存、銘柄抽出
  - SSRF 対策、受信サイズ制限、XML 安全パーサ
- 研究用ファクター（kabusys.research）
  - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）
  - calc_forward_returns, calc_ic, factor_summary, rank（特徴量探索）
  - zscore_normalize（data.stats）
- 監査ログスキーマ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の初期化ユーティリティ

---

## 必須・推奨依存関係

- Python 3.10 以上（typing の `X | Y` 構文を使用）
- duckdb
- defusedxml

インストール例（最低限）:
```
pip install duckdb defusedxml
```

プロジェクトには requirements.txt / pyproject.toml があればそれを利用してください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo_url>
   cd <repo_dir>
   ```

2. Python 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install duckdb defusedxml
   # または requirements.txt / pyproject.toml がある場合はそれに従う
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意（デフォルトあり／用途に応じて設定）:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG | INFO | ...)
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
   - 例 (.env):
     ```
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
     DUCKDB_PATH=data/kabusys.duckdb
     ```

5. DuckDB スキーマの初期化
   Python REPL またはスクリプトで次を実行:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```
   この呼び出しで必要なテーブルとインデックスが作成されます（冪等）。

---

## 使い方（主要ユースケース）

以下はライブラリの代表的な利用例です。実運用ではログ設定や例外処理を適切に追加してください。

- 日次 ETL を実行する（市場カレンダー・株価・財務取得＋品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- J-Quants から日足を手動で取得して保存する
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
  saved = save_daily_quotes(conn, records)
  ```

- ニュース収集ジョブを実行
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes は銘柄抽出用の有効銘柄セット（例: {'7203','6758',...}）
  result = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
  print(result)
  ```

- 研究用ファクター計算（例: モメンタム）
  ```python
  from datetime import date
  from kabusys.research import calc_momentum
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  factors = calc_momentum(conn, target_date=date(2024,6,30))
  # factors は各銘柄ごとの辞書リスト: {"date":..., "code":..., "mom_1m":..., ...}
  ```

- 特徴量の Z スコア正規化
  ```python
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(factors, columns=["mom_1m","ma200_dev"])
  ```

- 品質チェックを個別に実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

- カレンダー更新バッチ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved", saved)
  ```

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（get_id_token 用）
- KABU_API_PASSWORD — kabu API パスワード（将来の注文実行に使用）
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV (development|paper_trading|live)
- LOG_LEVEL (INFO など)
- KABU_API_BASE_URL
- DUCKDB_PATH
- SQLITE_PATH

自動 .env 読み込みを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                       — 環境変数 / 設定管理
- execution/                      — 発注 / 実行関連（未実装のエントリ）
- strategy/                       — 戦略ロジック（未実装のエントリ）
- monitoring/                     — 監視系モジュール（未実装のエントリ）
- data/
  - __init__.py
  - jquants_client.py             — J-Quants API クライアント + 保存ロジック
  - news_collector.py             — RSS 収集・保存・銘柄抽出
  - schema.py                     — DuckDB スキーマ定義・初期化
  - pipeline.py                   — ETL パイプライン（差分更新・品質チェック）
  - quality.py                    — データ品質チェック
  - calendar_management.py        — カレンダー更新と営業日ユーティリティ
  - audit.py                      — 監査ログ（signal/order/execution）スキーマ
  - etl.py                        — ETL 公開インターフェース
  - features.py                   — 特徴量ユーティリティ公開
  - stats.py                      — zscore_normalize 等の統計ユーティリティ
- research/
  - __init__.py
  - factor_research.py            — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py        — 将来リターン・IC・サマリー等
- その他 README やドキュメントファイルがプロジェクトルートに存在する想定

---

## 注意事項 / 開発メモ

- 多くのモジュールは DuckDB 接続を引数で受け取る設計です。接続/トランザクション管理は呼び出し側で制御してください。
- J-Quants の API レート制限や認証の取り扱いに注意してください（get_id_token の利用、_RateLimiter による制御あり）。
- ニュース RSS 取得は SSRF 対策や受信サイズ制限を実装していますが、外部の不正なフィードに対しては運用上の監視が必要です。
- 本リポジトリのコード例はデータ処理・研究用途が中心であり、本番での自動売買（実注文）を行う場合は別途リスク管理・レート制御・実行確認が必須です。

---

ご要望があれば次の内容を追加します:
- API リファレンス（各関数の引数/戻り値のまとめ）
- よくあるトラブルシューティング（DB 初期化失敗、J-Quants トークンエラーなど）
- CI / ローカルでのテスト実行方法

必要であれば教えてください。