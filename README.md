# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
主に以下をサポートします：

- J‑Quants API からのデータ取得（株価／財務／市場カレンダー）と DuckDB への ETL
- RSS ベースのニュース収集と記事の前処理
- OpenAI を用いたニュース NLP（銘柄ごとのセンチメント付与）および市場レジーム判定
- 監査ログ（signal → order_request → execution のトレーサビリティ）テーブル初期化
- 研究用ファクター計算（モメンタム／ボラティリティ／バリュー）や特徴量探索ユーティリティ
- データ品質チェック、マーケットカレンダー管理 等

このリポジトリはモジュール群として設計され、ETLバッチ・AIスコアリング・研究用途それぞれで再利用できるようになっています。

---

## 主な機能一覧

- data/
  - jquants_client: J‑Quants API クライアント（取得・保存・ページネーション・認証リフレッシュ・レート制御・リトライ）
  - pipeline: 日次 ETL パイプライン（prices / financials / calendar の差分取得・保存・品質チェック）
  - news_collector: RSS 取得・前処理・raw_news への保存ロジック（SSRF 防止・サイズ制限・トラッキング除去）
  - calendar_management: JPX カレンダーの取得・営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ（signal_events / order_requests / executions）テーブル定義と初期化
  - stats: 汎用統計ユーティリティ（Zスコア正規化）
- ai/
  - news_nlp.score_news: 指定ウィンドウのニュースを LLM に送り銘柄ごとのスコアを ai_scores に保存
  - regime_detector.score_regime: ETF (1321) の MA200乖離 と マクロニュースセンチメントを合成して market_regime を計算・保存
- research/
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）計算、統計サマリー 等
- config: .env / 環境変数の自動読み込み、設定オブジェクト（settings）

---

## 要件

- Python 3.10+（型注釈で | を使うため 3.10 以上を推奨。3.11 を推奨）
- 必要なライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ：urllib, json, datetime, logging など

（実際のプロジェクトでは requirements.txt / pyproject.toml を用意してください）

---

## 環境変数（主なもの）

以下は必須または重要な環境変数です。`.env` または OS 環境変数で設定します。プロジェクトルートに `.env` / `.env.local` があれば自動で読み込まれます（無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

必須（メソッド呼び出しで _require により ValueError になるもの）:
- JQUANTS_REFRESH_TOKEN — J‑Quants リフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション連携用パスワード
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack チャネル ID

OpenAI 関連:
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 呼び出し時に引数で渡すことも可能）

その他（省略時はデフォルトが利用される）:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
- SQLITE_PATH — デフォルト `data/monitoring.db`
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など（監視設定）

---

## セットアップ手順（例）

1. リポジトリをクローンして仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   実際は requirements.txt / poetry を用意して pip install -r requirements.txt を使ってください。

3. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、OS 環境変数として設定します。
   - 最低例（.env）
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=sk-...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C...

4. DuckDB 用ディレクトリを作る（必要なら）
   - mkdir -p data

---

## 使い方（代表的な例）

以下はライブラリを直接インポートして Python から利用する例です。実行前に必要な環境変数を設定してください。

- 日次 ETL を実行（prices / financials / calendar の差分取得・保存・品質チェック）:

  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP で銘柄ごとのスコアを生成（前日15:00〜当日08:30 JST ウィンドウ）:

  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None -> OPENAI_API_KEY を使う
  print("書き込み件数:", written)
  ```

- 市場レジーム判定（1321 ETF の MA200 とマクロニュース合成）:

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ用 DB の初期化:

  ```python
  from kabusys.data.audit import init_audit_db

  # ファイル DB を作る（parent ディレクトリがなければ自動作成）
  conn = init_audit_db("data/audit.duckdb")
  ```

注意:
- score_news / score_regime は OpenAI を呼び出すため API キーが必要です。api_key 引数で直接渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ETL は J‑Quants API を呼び出すため JQUANTS_REFRESH_TOKEN が必要です。jquants_client.get_id_token が自動リフレッシュします。

---

## 実装上の設計・運用ポイント（抜粋）

- Look‑ahead bias を避けるため、内部実装は date.today() を直接参照しない設計（外部から target_date を与えるか ETL の target_date を指定）。
- J‑Quants クライアントはレート制御とリトライ、401 時の自動リフレッシュを実装。
- News collector は SSRF 対策（リダイレクト検査・プライベートアドレス禁止・受信サイズ制限）やトラッキングパラメータ除去を実装。
- AI 呼び出しは JSON モードを使用し、リトライ／レスポンス検証／フォールバック（失敗時は中立スコア）を行う。
- DB 書き込みは基本的に冪等（ON CONFLICT / DELETE→INSERT のパターン）で設計。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - (その他データ関連モジュール)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/__init__.py
- (将来的に strategy, execution, monitoring パッケージなど)

主要ファイルの役割：
- config.py: .env の自動読み込み・Settings オブジェクト（環境変数ラッパ）
- data/jquants_client.py: J‑Quants API の取得／保存ロジック
- data/pipeline.py: 日次 ETL のオーケストレーション（run_daily_etl）
- data/news_collector.py: RSS 収集と raw_news への保存
- ai/news_nlp.py: 記事を LLM に送り銘柄別スコアを ai_scores に保存
- ai/regime_detector.py: MA200 と LLM のマクロセンチメントを合成して市場レジーム判定
- research/*: 研究・バックテスト用のファクター計算・統計ユーティリティ

---

## 注意事項 / 運用上のヒント

- 本ライブラリは API キー・トークンを扱うため、`.env` や CI シークレットで適切に管理してください。
- OpenAI の呼び出しは課金対象となるため、ローカル実行時は API 使用量に注意してください（テスト時はモック化を推奨）。
- DuckDB のスキーマ（テーブル定義）は ETL 実行前に整備しておく必要があります（スキーマ初期化用ユーティリティは別途提供する想定）。
- 自動的に .env を読み込みますが、テスト時などに無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

もし README に具体的なコマンド例（systemd サービス・cron・docker-compose 等）、CI 設定、あるいは requirements.txt / pyproject.toml の雛形を追加したい場合は、利用環境（Docker / Linux / Windows / CI）や依存パッケージの固定バージョン方針を教えてください。それに合わせて README を拡張します。