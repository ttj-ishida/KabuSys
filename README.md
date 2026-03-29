# KabuSys

日本株向け自動売買・データプラットフォーム（KabuSys）。  
市場データの ETL、ニュースの収集・NLP スコアリング、マーケットレジーム判定、ファクター研究、監査ログ等を備えたモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は、J-Quants / JPX 等から取得した株価・財務・カレンダーデータを DuckDB に蓄積し、ETL、データ品質チェック、ニュース収集・センチメント評価（OpenAI）、レジーム判定、ファクター計算を行うためのライブラリ群です。監査ログ（シグナル→発注→約定のトレース）や RSS ニュース収集における SSRF/zip-bomb 等の安全対策も組み込まれています。

主な利用ケース:
- データパイプライン（日次 ETL）
- ニュースを使った銘柄ごとの AI スコアリング
- マーケットレジーム判定（ETF + LLM 複合）
- ファクター作成・解析（リサーチ用途）
- 監査ログ（発注/約定トレーサビリティ）

---

## 機能一覧

- 環境変数・設定管理（自動 .env ロード／保護）: kabusys.config
  - 自動ロードはプロジェクトルート（.git / pyproject.toml）を基準に `.env` / `.env.local` を読み込み
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

- データ ETL: kabusys.data.pipeline, jquants_client
  - J-Quants API から日次株価 / 財務 / カレンダーを差分取得（ページネーション、レートリミット、トークン自動リフレッシュ）
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
  - ETL 結果を ETLResult に集約

- データ品質チェック: kabusys.data.quality
  - 欠損、重複、スパイク、日付不整合（未来日付／非営業日）検出

- ニュース収集: kabusys.data.news_collector
  - RSS 取得・前処理・正規化・SSRF/圧縮対策・冪等保存
  - 記事IDは正規化URLの SHA-256（先頭32文字）

- AI ニュース NLP: kabusys.ai.news_nlp
  - OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントスコアを算出し ai_scores に保存
  - バッチ処理、JSON mode、リトライ/バックオフ、レスポンスバリデーションあり

- マーケットレジーム判定: kabusys.ai.regime_detector
  - ETF(1321) の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して daily レジームを判定・保存

- 研究ユーティリティ: kabusys.research
  - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、z-score 正規化

- 監査ログ（audit）: kabusys.data.audit
  - signal_events / order_requests / executions 等のテーブル定義と初期化関数
  - 監査DBの初期化ユーティリティ（UTC タイムゾーン設定、トランザクション対応）

---

## セットアップ手順

前提: Python 3.9+ を想定（typing の新構文を利用）。依存パッケージのインストールが必要です。

1. リポジトリをクローン / プロジェクトルートへ移動

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. インストール（pip）
   - pip install -e .  # setup.cfg / pyproject がある前提
   - 必須パッケージの例:
     - duckdb
     - openai
     - defusedxml

   （プロジェクトに requirements.txt / pyproject の指定がない場合は上記を個別にインストールしてください）

4. 環境変数設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（.env.local で上書き可）
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
   - SLACK_BOT_TOKEN: Slack Bot Token（通知等で使用する場合）
   - SLACK_CHANNEL_ID: Slack 送信先チャンネルID
   - KABU_API_PASSWORD: kabuステーション API パスワード（実行・発注に利用する場合）
   - OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）

   省略可能 / デフォルト
   - KABUSYS_ENV: development（development / paper_trading / live のいずれか）
   - LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db
   - KABU_API_BASE_URL: http://localhost:18080/kabusapi

   例 `.env`（プロジェクトルート）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_kabu_password
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データベース初期化（監査用 DB の例）
   - Python REPL またはスクリプトで:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - DuckDB ファイルの親ディレクトリは自動作成されます（":memory:" でインメモリ可能）

---

## 使い方（基本的な呼び出し例）

以下はライブラリを直接利用する例です。実運用では適切なスケジューラ（cron / Airflow 等）から呼び出してください。

- 日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（ai_scores へ保存）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を使う場合は None
  print(f"written: {written}")
  ```

- マーケットレジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査スキーマ初期化（既存接続に追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  m = calc_momentum(conn, target_date=date(2026,3,20))
  v = calc_value(conn, target_date=date(2026,3,20))
  vol = calc_volatility(conn, target_date=date(2026,3,20))
  ```

注意:
- これらの関数は DuckDB に必要なテーブル（raw_prices, raw_financials, raw_news, news_symbols, market_calendar など）が存在することを前提とします。
- OpenAI を使う関数は OPENAI_API_KEY を環境変数か引数で渡してください。API 呼び出しはリトライやクリッピング等のフェイルセーフを備えていますが、料金とレートに注意してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールと役割の概観です。

- kabusys/
  - __init__.py (パッケージ定義、__version__ = "0.1.0")
  - config.py
    - 環境変数管理、自動 .env ロード、settings オブジェクト
  - ai/
    - __init__.py (score_news を公開)
    - news_nlp.py (ニュース NLP スコアリング、OpenAI 呼び出し/バッチ/検証)
    - regime_detector.py (マクロ + ETF MA による市場レジーム判定)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント、fetch/save 実装)
    - pipeline.py (ETL パイプライン、run_daily_etl 等)
    - etl.py (ETLResult の再エクスポート)
    - news_collector.py (RSS 収集、前処理、保存)
    - calendar_management.py (市場カレンダー管理・営業日判定)
    - stats.py (z-score 等の統計ユーティリティ)
    - quality.py (データ品質チェック)
    - audit.py (監査スキーマ初期化・監査 DB ユーティリティ)
  - research/
    - __init__.py (公開 API)
    - factor_research.py (momentum/value/volatility 計算)
    - feature_exploration.py (将来リターン、IC、統計サマリー等)
  - monitoring/  (README の冒頭で __all__ に含まれているが、詳細実装は省略されている可能性があります)

---

## 運用上の注意

- 本コードベースは「ルックアヘッドバイアス防止」を設計方針としているため、多くの関数で datetime.today()/date.today() を直接参照しません。バックテスト・バッチ実行時は target_date を明示的に指定してください。
- OpenAI / J-Quants / kabuステーション 等の API キー・トークンは厳重に管理してください。ログにキーを出力しないよう注意してください。
- KABUSYS_ENV は development / paper_trading / live のいずれかを指定し、is_live/is_paper/is_dev の判定に使用されます。発注コードを組み合わせる場合は必ず環境に応じたガードを実装してください（ライブ口座での誤発注防止）。
- ETL は品質チェックを行いますが、品質チェックで検出された問題の取り扱い（停止するか警告で済ませるか）は呼び出し元で決定してください（ETL は Fail-Fast ではない設計）。

---

## 貢献・拡張

- 模組織化されたモジュール構造のため、新しいデータソースや AI モデルの差し替えがしやすくなっています。
- テストしやすさを考慮して内部の API 呼び出しは差し替え可能（例: news_nlp._call_openai_api を unittest.mock.patch で置換可能）に設計されています。
- 監査スキーマは冪等に初期化されるため、既存 DB に追加可能です。

---

必要であれば README にサンプル .env.example ファイル、CI / デプロイ手順、より詳細な API 使用例（kabuステーション連携や Slack 通知の実装例）を追記します。どの情報を追加したいか教えてください。