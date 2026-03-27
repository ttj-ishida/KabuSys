# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、因子計算、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム／リサーチ基盤構築を目的とした Python パッケージです。  
主な責務は以下です。

- J-Quants API を使った株価・財務・カレンダーデータの差分取得と DuckDB への保存（ETL）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）と OpenAI を用いたニュースセンチメント解析（銘柄別 ai_score）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM 評価を合成）
- 研究向けユーティリティ（ファクター計算、将来リターン、IC 計算、Zスコア正規化）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ生成

設計上、ルックアヘッドバイアスを避けるため日付参照を外部から与える設計（内部で date.today()/datetime.today() を多用しない）になっています。

---

## 機能一覧

- 環境変数／.env 自動読み込み（.env / .env.local、自動ロード無効化可）
- J-Quants API クライアント（認証、ページネーション、レート制御、リトライ、保存用関数）
- ETL パイプライン（run_daily_etl / 個別 ETL ジョブ）
- 市場カレンダー管理（営業日判定、次/前営業日取得、カレンダー更新ジョブ）
- ニュース収集（RSS、SSRF 対策、前処理、raw_news 保存）
- ニュース NLP（gpt-4o-mini を用いた銘柄別スコアリング、チャンク処理・リトライ）
- 市場レジーム判定（ma200 とマクロセンチメントの合成）
- 研究用ツール（momentum, value, volatility ファクター等、forward returns, IC, summary）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログスキーマの初期化ユーティリティ（DuckDB 用）

---

## 前提条件

- Python 3.9+
- 必要な主要パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- J-Quants のリフレッシュトークン、OpenAI API キーなどの環境変数が必要

（このリポジトリには requirements.txt が含まれていない想定のため、上記ライブラリをプロジェクトに合わせてインストールしてください。）

---

## 環境変数

主に以下の環境変数を参照します（settings を通じて取得）。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN: Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID
- KABU_API_PASSWORD: kabu ステーション連携に必要なパスワード（利用する場合）

任意 / デフォルトあり:
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（モニタリング等）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）

自動 .env 読み込み:
- パッケージ初期化時にプロジェクトルート (.git または pyproject.toml のあるディレクトリ) を探索し、
  OS 環境変数 > .env.local > .env の順で読み込みます。
- 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

ヒント: .env.example を参考に .env を用意してください（リポジトリに example がある想定）。

---

## セットアップ手順（例）

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - pip install -e .   # パッケージを編集可能インストールする場合
4. 環境変数を設定
   - .env または .env.local に必要なキーを入れる
     例（.env の一部）
       JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
       OPENAI_API_KEY=sk-...
       SLACK_BOT_TOKEN=xoxb-...
       SLACK_CHANNEL_ID=C01234567
       DUCKDB_PATH=data/kabusys.duckdb
       KABUSYS_ENV=development
5. DuckDB 用ディレクトリを作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要な例）

以下は Python から直接利用する最小の使用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）を受け取ります。

- ETL（日次）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（銘柄別 ai_score の生成）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数で指定している前提
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key=None)
  ```

- 監査ログ DB 初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って order_requests 等にアクセスできます
  ```

- 研究用ファクター計算
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  factors = calc_momentum(conn, target_date=date(2026,3,20))
  # factors は dict のリスト
  ```

注意点:
- OpenAI 呼び出しを行う関数（score_news, score_regime）は api_key 引数を受け取ります。None の場合は環境変数 OPENAI_API_KEY を参照します。
- ETL / 保存系は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news, ai_scores 等）が前提です。初回は適切なスキーマ初期化処理（本リポジトリ外のスクリプトや別モジュール）を行ってください。

---

## 主要 API（抜粋）

- kabusys.config.settings - 環境設定アクセサ
- kabusys.data.pipeline.run_daily_etl(...) - 日次 ETL のメイン関数
- kabusys.data.jquants_client.* - J-Quants API 向け fetch_* / save_* / get_id_token
- kabusys.data.news_collector.fetch_rss(...) - RSS 取得ユーティリティ
- kabusys.ai.news_nlp.score_news(...) - OpenAI を用いて銘柄別ニューススコアを生成
- kabusys.ai.regime_detector.score_regime(...) - 市場レジーム判定を実行
- kabusys.data.quality.run_all_checks(...) - データ品質チェックを一括実行
- kabusys.research.* - 研究用の因子・統計ユーティリティ
- kabusys.data.audit.init_audit_db(...) - 監査DB 初期化

---

## 自動 .env 読み込みの挙動

- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基に `.env` と `.env.local` を読み込みます。
- 読み込み優先度: OS 環境変数 > .env.local > .env
- テスト等で自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主なモジュール構成です。

- kabusys/
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
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

各ファイルは上記 README に記載した機能群を担う実装になっています。詳細な関数仕様や設計方針は各モジュールの docstring を参照してください。

---

## 注意事項 / ベストプラクティス

- OpenAI や J-Quants の API キーは機密情報です。公開リポジトリに含めないでください。
- DuckDB のスキーマ定義（テーブル作成）は本リポジトリにあるモジュールに依存しますが、初回スキーマ作成用のスクリプトやマイグレーションは別途用意してください（このコードベースは保存/更新機能を提供しますが、全テーブル DDL の網羅的な初期化 API はモジュール毎に分散しています）。
- 本パッケージはバックテストや本番運用でのルックアヘッドバイアス回避に注意して設計されています。日付パラメータを外部から明示的に与えることを推奨します。
- ニュース収集や外部ネットワークアクセスは SSRF・巨大レスポンス対策が組み込まれていますが、運用環境ではネットワークの安全性設定（ファイアウォール等）も行ってください。

---

必要であれば、README に記載するサンプル .env.example、requirements.txt の候補、あるいは CLI ラッパーや初期スキーマ作成スクリプトのテンプレートも作成します。どの情報を追加しますか？