# KabuSys

日本株向け自動売買・データプラットフォーム用ライブラリ（KabuSys）。  
ETL、ニュース収集、LLM を使ったニュースセンチメント評価、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（発注→約定トレース）などを提供します。

---

## 概要

KabuSys は J-Quants API を中心としたマーケットデータの取得・整備から、ニュース NLP を使った銘柄単位の AI スコアリング、ETF を使った市場レジーム判定、ファクター算出・解析、データ品質チェック、監査ログ（発注／約定）まで分離されたモジュールで実装したツール群です。  
バックテストや自動運用基盤の一部として組み込み可能な再利用性の高い関数群を提供します。

主な設計方針:
- ルックアヘッドバイアス回避（内部で date.today()/datetime.today() を直接参照しない等）
- DuckDB を中核にしたローカル DB（ETL の保存・検索）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（JSON mode 想定）
- J-Quants API のレートリミット・リトライ・トークン自動更新処理
- 冪等性（DB 保存は ON CONFLICT / INSERT ... DO UPDATE 等）

---

## 機能一覧

- データ取得・ETL
  - J-Quants から株価日足 / 財務データ / 上場銘柄情報 / 市場カレンダーを差分取得（ページネーション対応・レート制御・リトライ）
  - run_daily_etl で日次パイプライン実行（カレンダー→株価→財務→品質チェック）
- データ品質チェック
  - 欠損、重複、スパイク（前日比閾値）、日付整合性チェック（market_calendar との整合性）
- ニュース収集
  - RSS 収集、前処理、SSRF対策、トラッキングパラメータ排除、raw_news への冪等保存（news_symbols 連携）
- ニュース NLP（AI）
  - 銘柄ごとのニュース集約→OpenAI（gpt-4o-mini）でセンチメント評価→ai_scores へ保存（バッチ処理・リトライ・レスポンス検証）
  - 関数: kabusys.ai.news_nlp.score_news
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次レジーム（bull/neutral/bear）を判定・market_regime へ保存
  - 関数: kabusys.ai.regime_detector.score_regime
- 研究（Research）
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー、Zスコア正規化
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 の階層的トレース用テーブル定義と初期化ユーティリティ
  - DuckDB 上の監査 DB 初期化関数を提供
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出、.env / .env.local、OS 環境変数保護）
  - settings オブジェクト経由で必要なトークンやパスを取得

---

## セットアップ手順

1. リポジトリをクローン（適宜）
2. Python 仮想環境を作成・有効化（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell)
   ```
3. 依存パッケージをインストール
   - 必要な依存はプロジェクトの pyproject.toml / requirements に従ってください。最低限以下が必要です:
     - duckdb
     - openai
     - defusedxml
   例（pip）:
   ```bash
   pip install duckdb openai defusedxml
   # 開発インストール（プロジェクト直下で）
   pip install -e .
   ```
4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）で `.env` を作成すると自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化）。
   - 最低必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD (kabu API を使用する場合)
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（通知に使う場合）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - 例:
     ```
     # .env (例)
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-....
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     ```
5. データディレクトリの作成（必要なら）
   ```bash
   mkdir -p data
   ```

---

## 使い方（プログラム例）

基本は Python API を直接呼び出します。DuckDB 接続は `duckdb.connect(path)` で作成します。

- 日次 ETL を実行する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  # 実行日を指定するか省略して今日を使用
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを生成して ai_scores に保存する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY が必要
  print(f"scored {count} symbols")
  ```

- 市場レジーム判定:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY が必要
  ```

- 監査ログ用 DB 初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- 設定取得:
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

注意点:
- AI を呼ぶ関数は OpenAI API キーを引数で渡すこともできます（api_key=...）。環境変数 OPENAI_API_KEY が使われます。
- ETL や外部 API 呼び出しはネットワークや認証トークンが必要です。事前に .env に必要項目を用意してください。
- DuckDB のスキーマ/テーブルは ETL 実行前に用意しておく必要があります（プロジェクト内でスキーマ初期化スクリプトを用意してください）。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- KABU_API_PASSWORD: kabuステーション API パスワード（使用時）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用（任意）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- DUCKDB_PATH: DuckDB ファイルパス
- SQLITE_PATH: sqlite3（モニタリング等）ファイルパス
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env の自動読み込みを無効化

.env のパースはシンプルな shell 形式（export KEY=val / KEY=val、クォート対応、コメント対応）に対応しています。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル・モジュール一覧（src/kabusys 以下の主な構成）:

- src/kabusys/
  - __init__.py: パッケージ定義、バージョン
  - config.py: 環境変数・設定管理（.env 自動読み込み、settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py: ニュースセンチメント解析・ai_scores 書込（OpenAI 呼び出し、バッチ・リトライ）
    - regime_detector.py: 市場レジーム判定（ETF MA + マクロニュース融合）
  - data/
    - __init__.py
    - jquants_client.py: J-Quants API クライアント（取得・保存 helper、レート制御、リトライ）
    - pipeline.py: ETL パイプライン（run_daily_etl 等）
    - etl.py: ETLResult の再エクスポート
    - news_collector.py: RSS 収集、前処理、SSRF 対策
    - calendar_management.py: 市場カレンダー管理・営業日判定
    - quality.py: データ品質チェック
    - stats.py: 汎用統計ユーティリティ（zscore_normalize）
    - audit.py: 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py: モメンタム / ボラティリティ / バリュー算出
    - feature_exploration.py: 将来リターン計算、IC、統計サマリー、ランク関数
  - その他（strategy / execution / monitoring）: パッケージ公開用プレースホルダ（将来的な拡張）

各モジュールは docstring と設計方針・注意点を含み、DuckDB 接続オブジェクトを受け取る関数群が中心です。

---

## 開発・テストのヒント

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。CI や一部テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと良いです。
- OpenAI コールや外部 API 呼び出しは各モジュール内で _call_openai_api / _request 等の関数を経由しており、ユニットテストではこれらを patch して差し替え可能です。
- DuckDB を使った単体テストは ":memory:" 接続が使えます（init_audit_db も ":memory:" をサポート）。

---

## 免責・注意

- 本リポジトリは金融データ・自動売買に関連するユーティリティ群を提供しますが、実際の運用に当たっては十分な検証とリスク管理が必要です。
- 実際の発注ロジックや本番環境での運用は別途厳密なレビュー・テストを行ってください。
- API キーやシークレットは適切に管理し、公開リポジトリ等にコミットしないでください。

---

必要であれば README に含めるサンプルスクリプト、テーブルスキーマ初期化手順、より詳しい環境変数例や運用手順（cron / Airflow での ETL スケジューリング等）を追加できます。どの情報を優先して追記しますか？