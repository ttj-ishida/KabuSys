# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants）による市場データ収集、ニュース収集・NLP スコアリング、ファクター計算、監査ログ（オーディット）や市場カレンダー管理、監視・発注層との連携までを想定したモジュール群を提供します。

主な想定利用ケース：
- データプラットフォームの夜間バッチ（株価／財務／カレンダーの差分 ETL）
- ニュースを使った銘柄単位の AI センチメントスコア算出
- 市場レジーム判定（MA + マクロニュースの LLM 評価）
- 研究用途のファクター算出（モメンタム / ボラティリティ / バリュー 等）
- 監査テーブル（signal → order_request → execution）の初期化・管理
- データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）

---

## 機能一覧（抜粋）

- 環境設定管理
  - .env / .env.local 自動ロード（プロジェクトルート検出）
  - 必須環境変数チェック（Settings クラス）
- データ取得・保存（J-Quants API）
  - fetch/save: 日次株価、財務、上場銘柄情報、JPX カレンダー
  - レート制御・リトライ・トークン自動リフレッシュを含む堅牢な HTTP 層
- ETL パイプライン
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 品質チェック（quality.run_all_checks）
  - ETL 結果を ETLResult で返却
- ニュース収集（RSS）
  - RSS 正規化・SSRF 対策・gzip サイズ上限・トラッキングパラメータ削除
  - raw_news / news_symbols への冪等保存ロジック（設計方針に準拠）
- ニュース NLP（OpenAI）
  - batch 化して gpt-4o-mini に JSON Mode で投げる設計
  - score_news: 銘柄ごとの ai_score を ai_scores テーブルへ保存
  - 429 / ネットワーク断 / タイムアウト / 5xx はバックオフ付きでリトライ
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離（70%）とマクロニュース LLM 評価（30%）を合成
  - score_regime 関数で market_regime テーブルへ冪等書込
- ファクター研究ユーティリティ
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize
- データ品質チェック
  - 欠損、スパイク、重複、日付整合性チェック
  - QualityIssue オブジェクトで結果を返す
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルの DDL とインデックス
  - init_audit_schema / init_audit_db による初期化（UTC タイムゾーン固定）

---

## 必要環境（推奨）

- Python 3.10+
  - 型注釈で Python 3.10 の | 型合成を利用しているため
- 主な依存ライブラリ（最低限）
  - duckdb
  - openai
  - defusedxml

（プロジェクト配布時は requirements.txt / pyproject.toml を参照してください。ここにない依存がある場合はそれに従ってください）

---

## セットアップ手順

1. リポジトリをクローン / プロジェクトのルートへ移動

2. 仮想環境作成（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

3. 必要パッケージをインストール
   例（最低限）:
   ```bash
   pip install duckdb openai defusedxml
   ```
   ※ 実プロジェクトでは pyproject.toml / requirements.txt に従ってください。

4. 環境変数設定
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を置くことで自動ロードされます。
   - 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション等の API パスワード
     - SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意 / デフォルトを持つ:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/...（デフォルト INFO）
     - KABU_API_BASE_URL — デフォルト "http://localhost:18080/kabusapi"
     - DUCKDB_PATH — デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH — デフォルト "data/monitoring.db"

   .env 例（参考）
   ```
   JQUANTS_REFRESH_TOKEN=xxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   ```

5. DuckDB / 監査 DB 初期化（必要に応じて）
   - 監査ログ専用 DB を作成する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 既存接続にスキーマを追加する場合:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_schema
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn, transactional=True)
     ```

---

## 使い方（代表的な例）

以下はライブラリ API を直接呼び出すサンプルです。実運用ではジョブランナー（cron, Airflow 等）や CLI を用いて呼び出してください。

1. 日次 ETL を実行する（データ収集 → 品質チェック）
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

2. ニュース NLP で銘柄ごとスコアを生成（OpenAI API key は環境変数 OPENAI_API_KEY）
   ```python
   from datetime import date
   import duckdb
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect("data/kabusys.duckdb")
   count = score_news(conn, target_date=date(2026, 3, 20))
   print(f"scored {count} codes")
   ```

3. 市場レジームを判定して保存
   ```python
   from datetime import date
   import duckdb
   from kabusys.ai.regime_detector import score_regime

   conn = duckdb.connect("data/kabusys.duckdb")
   score_regime(conn, target_date=date(2026, 3, 20))
   ```

4. 監査スキーマ初期化
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_schema

   conn = duckdb.connect("data/kabusys.duckdb")
   init_audit_schema(conn, transactional=True)
   ```

5. 研究用ファクター計算
   ```python
   from datetime import date
   import duckdb
   from kabusys.research.factor_research import calc_momentum, calc_value

   conn = duckdb.connect("data/kabusys.duckdb")
   mom = calc_momentum(conn, date(2026, 3, 20))
   val = calc_value(conn, date(2026, 3, 20))
   ```

注意点：
- すべての関数は Look-ahead bias を避けるため内部で datetime.today() を参照しない設計です（target_date を明示してください）。
- OpenAI 呼び出しは外部 API に依存するため API キーやレート制限に注意してください。
- DuckDB による executemany の仕様など（空リスト不可など）に合わせた実装上の注意があります。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- OPENAI_API_KEY (score_news / score_regime で使用。引数で上書き可能)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (省略可、デフォルト "http://localhost:18080/kabusapi")
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (省略可、デフォルト "data/kabusys.duckdb")
- SQLITE_PATH (省略可、デフォルト "data/monitoring.db")
- KABUSYS_ENV ("development" | "paper_trading" | "live") — デフォルト "development"
- LOG_LEVEL ("DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL") — デフォルト "INFO"
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動ロードを無効化

設定は .env / .env.local に置くことで自動で読み込まれます（プロジェクトルートは .git または pyproject.toml から推定）。

---

## ディレクトリ構成（このリポジトリ内の主なファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
  - (その他 ETL 関連モジュール)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/*（ファクター計算・探索用ユーティリティ群）
- ai/*（ニュース NLP / レジーム判定）
- data/*（J-Quants クライアント、ETL、品質チェック、監査スキーマ など）

※ 実運用リポジトリでは tests/、scripts/、examples/、pyproject.toml / requirements.txt 等が付属することが想定されます。

---

## 運用上の注意

- API キーやトークンは厳重に管理してください（CI の secret、Vault 等の利用を推奨）。
- OpenAI / J-Quants のレート制限を守るため、並列実行やバッチ化の設計に注意してください（ライブラリ内で基本的なレート制御・バックオフは実装済みです）。
- DuckDB ファイルはバックアップ・ローテーションを検討してください（データ量に応じた運用設計が必要）。
- 本リポジトリの関数は多くが DB スキーマ（テーブル名）に依存します。初期スキーマの準備やマイグレーション手順を整備してください。

---

この README はコードベースの主要機能と使い方の概要をまとめたものです。詳細な API 仕様・ DB スキーマ・運用手引きは別途ドキュメント（Design/Doc ファイル）を参照してください。質問や README の追加補足が必要であれば教えてください。