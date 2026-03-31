# KabuSys

KabuSys は日本株向けの自動売買・データ基盤・リサーチ用ライブラリ群です。  
J-Quants/API からのデータ取得（ETL）、ニュース収集と LLM によるニュース/マクロ判定、ファクタ計算、監査ログ（発注/約定トレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

---

## 概要

主な目的は以下です。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS を用いたニュース収集とテキスト前処理、銘柄紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析（銘柄別）およびマクロセンチメントに基づく市場レジーム判定
- 研究用ユーティリティ（ファクター計算・将来リターン・IC 計算・統計サマリー）
- データ品質チェック、マーケットカレンダー管理、監査ログ（signal → order_request → execution のトレーサビリティ）

設計方針としては、ルックアヘッドバイアス回避、冪等性、外部 API の堅牢なリトライ制御、DuckDB を中心としたローカルデータ保存、外部ライブラリ依存の最小化（主要ロジックは標準ライブラリ＋最小限の依存）を採用しています。

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env 自動ロード（プロジェクトルート検出）、必須環境変数の取得ユーティリティ
- データ ETL（kabusys.data.pipeline / etl / jquants_client）
  - 差分フェッチ、ページネーション対応、トークン自動更新、レートリミット対応
  - DuckDB への冪等保存（ON CONFLICT）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF 対策、記事ID生成、前処理、raw_news への保存フロー設計
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合の検出
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定・前後営業日算出・夜間バッチ更新（J-Quants）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ（冪等）
- AI 関連（kabusys.ai）
  - score_news: 銘柄ごとのニュースセンチメント算出（LLM バッチ処理、JSON Mode）
  - score_regime: ETF（1321）200日 MA 乖離 + マクロセンチメント合成による市場レジーム判定
- 研究用ユーティリティ（kabusys.research）
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / zscore_normalize

---

## 必要条件・依存関係

- Python 3.10+
- 必須パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI API）
- J-Quants リフレッシュトークン、OpenAI API キー、kabu API パスワード、Slack トークン等（環境変数で管理）

実際の開発/運用では pyproject.toml / requirements.txt を用意して pip または Poetry で管理してください。

---

## セットアップ手順

1. リポジトリをクローンしてインストール（開発向け）
   - pip を使う例:
     ```
     git clone <repo-url>
     cd <repo>
     pip install -e .
     pip install duckdb openai defusedxml
     ```

2. 必要な環境変数を設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（自動ロードはデフォルト有効）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

3. 最低限必要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - OPENAI_API_KEY=...（score_news / score_regime を使う場合）
   - オプション:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development / paper_trading / live)
     - LOG_LEVEL (DEBUG/INFO/…)
   - 例（.env の一部）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```

4. DuckDB 初期化（監査ログ用 DB）
   - kabusys.data.audit.init_audit_db を利用して監査 DB を作成できます。
   - 例:
     ```
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（代表的な例）

以下に主要機能の利用イメージを示します。

- ETL（日次パイプライン）を実行する例:
  ```
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）を算出して ai_scores に書き込む:
  ```
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20))
  print("written codes:", n_written)
  ```

- 市場レジーム判定（score_regime）の例:
  ```
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 研究用ファクター計算:
  ```
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  ```

- カレンダー関連ユーティリティ:
  ```
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026,3,20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

注意点:
- score_news / score_regime は OpenAI API キー（OPENAI_API_KEY）を要求します。api_key を引数で明示的に渡すことも可能です。
- ETL / 保存処理は DuckDB のスキーマ（テーブル）前提の実装です。初期スキーマ作成は別途スキーマ初期化ユーティリティを用意してください（リポジトリにスキーマ定義がある想定）。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で必要）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（任意）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須と定義されている）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル（必須と定義されている）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを無効化

---

## ディレクトリ構成

（ソースは src/kabusys 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数管理・自動 .env ロード・Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py
      - 銘柄ごとのニュースセンチメント算出（LLM バッチ、検証、DuckDB への書込）
    - regime_detector.py
      - ETF（1321）200日 MA 乖離 + マクロセンチメント合成による市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py
      - 市場カレンダー管理・営業日判定・夜間バッチ更新
    - etl.py
      - ETLResult の再エクスポート
    - pipeline.py
      - 日次 ETL パイプライン（prices / financials / calendar）と個別 ETL ジョブ
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査ログテーブル定義・初期化（signal_events, order_requests, executions）
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・認証・レート制御・リトライ）
    - news_collector.py
      - RSS 取得・前処理・SSRF 対策・記事ID生成
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Value / Volatility / Liquidity ファクター計算
    - feature_exploration.py
      - 将来リターン計算・IC（スピアマン）・ランク・統計サマリー

---

## テスト・ローカル実行に関するメモ

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に行われます。テスト時にローカル .env を読み込みたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI や外部 API 呼び出し部分は内部で小さなラッパー関数を使っているため、ユニットテストではそれらの関数をモックしやすく設計されています（例: kabusys.ai.news_nlp._call_openai_api を patch）。
- DuckDB を使っているため、":memory:" を用いればインメモリ DB で高速にテスト可能です。

---

## ライセンス・コントリビューション

リポジトリ内の LICENSE / CONTRIBUTING ドキュメントに従ってください（本 README では割愛）。

---

不明点や README に追記したい具体的な使い方（例: スキーマ初期化スクリプト、CI 設定、実運用でのデプロイ手順）などあれば教えてください。必要に応じて README を拡張します。