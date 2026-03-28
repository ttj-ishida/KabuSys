# KabuSys

日本株向けの自動売買 / データプラットフォーム向けライブラリです。  
ETL（J-Quants からのデータ収集）、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、監査ログ用スキーマなどを提供します。

主に内部処理は DuckDB を利用してローカル DB 上で完結する設計になっており、OpenAI（gpt-4o-mini）を使ったニュースセンチメント解析や J-Quants API との連携機能が含まれます。

---

## 主な機能

- データ取得 / ETL
  - J-Quants からの株価（日足）、財務データ、マーケットカレンダー取得（pagination・リトライ・レート制御付き）
  - 差分取得・バックフィル・品質チェック（欠損・重複・スパイク・日付不整合）
  - ETL の統合 entrypoint: run_daily_etl
- ニュース収集・NLP
  - RSS 取得（SSRF 対策、サイズ制限、URL 正規化）
  - OpenAI を使った銘柄別ニュースセンチメント（score_news）
  - マクロニュース + ETF（1321）MA 乖離の合成による市場レジーム判定（score_regime）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合を検出するチェック群と QualityIssue 型
- 監査ログ（オーダー・約定トレーサビリティ）
  - 冪等設計の監査テーブル定義・初期化（init_audit_schema / init_audit_db）
- 設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）と Settings API

---

## 事前準備 / 必要な環境

- Python 3.10+（型アノテーションの構文を利用）
- パッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリ

（実際のインストール要件は setup.py/pyproject.toml を参照してください）

---

## セットアップ手順（例）

1. リポジトリをクローン / 作業ディレクトリへ移動

2. 仮想環境を作成して有効化（例）
   - macOS / Linux:
     python -m venv .venv
     source .venv/bin/activate
   - Windows:
     python -m venv .venv
     .venv\Scripts\activate

3. 必要パッケージをインストール
   - 例（最低限）:
     pip install duckdb openai defusedxml

   - 開発用にパッケージ一覧がある場合:
     pip install -e .

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置すると自動で読み込まれます（ただしテスト時など自動ロードを無効化可）。
   - 自動読み込みを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   - サンプル `.env`（最低限必要なキー）
     JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
     KABU_API_PASSWORD=kabu_api_password（kabuステーション用）
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     OPENAI_API_KEY=sk-...

   - 特に Settings から参照される環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
     - OPENAI_API_KEY（score_news / score_regime の api_key 引数を省略する場合）
     - KABUSYS_ENV（development / paper_trading / live、省略時 development）
     - LOG_LEVEL（DEBUG/INFO/...、省略時 INFO）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 sqlite のデフォルト: data/monitoring.db）

---

## 使い方（代表的な例）

以下はライブラリをインポートして主要機能を呼ぶ最小例です。実運用ではロギングやスケジューリング（cron / Airflow 等）を用いて定期実行します。

- DuckDB 接続を作成して ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- OpenAI を使ってニュースセンチメントを算出（score_news）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"ai_scores に書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定（ETF 1321 の MA とマクロニュースの合成）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- ニュース RSS の取得（単体）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["title"], a["datetime"])
  ```

※ OpenAI 呼び出し部はネットワーク・課金リスクがあるため、API キー管理・料金管理には注意してください。API 呼び出しは関数引数で明示的に api_key を与えて注入可能です（テスト容易性のため）。

---

## 設定管理の挙動（ポイント）

- 自動 .env 読み込み
  - パッケージの config.py は実行時にプロジェクトルートを探索して `.env` と `.env.local`（順に）を読み込みます。
  - OS 環境変数 > .env.local > .env の優先順位で決定されます。
  - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。

- Settings API
  - kabusys.config.settings 経由で必要な値を取得できます（プロパティで必須チェックを行う）。
  - 例: settings.jquants_refresh_token, settings.duckdb_path, settings.is_live など。

---

## ディレクトリ構成（主要ファイル説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env の自動読込と Settings クラスを提供
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュース記事をまとめて OpenAI に投げ、銘柄ごとの ai_score を ai_scores テーブルへ保存
    - regime_detector.py
      - ETF 1321 の MA 乖離 + マクロニュース LLM スコアから market_regime を算出・保存
  - data/
    - __init__.py
    - calendar_management.py
      - JPX カレンダー管理、営業日判定・next/prev/get_trading_days 等
    - etl.py
      - ETL インターフェースの再エクスポート（ETLResult）
    - pipeline.py
      - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl 等の ETL ロジック
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック群（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）テーブル定義と初期化関数
    - jquants_client.py
      - J-Quants API 呼び出し、取得・保存用ユーティリティ（fetch/save 系）
    - news_collector.py
      - RSS の安全な収集・前処理・raw_news への保存ロジック
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_value / calc_volatility
    - feature_exploration.py
      - calc_forward_returns / calc_ic / factor_summary / rank

---

## 運用上の注意・設計方針

- ルックアヘッドバイアス防止
  - バックテストや統計計算では datetime.today()/date.today() を直接参照しない実装方針を採っています。関数は target_date を明示的に受け取るか、ETL で調整します。
- フェイルセーフ
  - 外部 API（OpenAI, J-Quants）失敗時は可能な限りフェイルセーフ化（デフォルト値で継続・ログ出力）する設計です。致命的なケースは呼び出し側で扱ってください。
- 冪等性
  - DuckDB への保存は ON CONFLICT DO UPDATE（保存関数内で executemany 等）を用い、差分更新・再実行可能な ETL を意識しています。
- セキュリティ
  - news_collector は SSRF 対策、受信サイズ制限、defusedxml による XML パース保護を実施しています。

---

## 開発・テスト

- 自動 .env 読み込みを無効化してユニットテストを簡単に行えます:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 python -m pytest
- OpenAI / ネットワーク呼び出しは関数（_call_openai_api など）をモックしてテストする設計になっています。

---

## 参考 / 補足

- デフォルトの DuckDB ファイルパスは Settings.duckdb_path（data/kabusys.duckdb）。適宜設定を変更してください。
- 本リポジトリはライブラリ／内部コンポーネント群として設計されています。運用ジョブ（cron / systemd / Airflow 等）から ETL や NLP、レジーム判定をスケジュール実行することを想定しています。

---

必要であれば、README に含めるサンプル .env.example や実行スクリプト（systemd unit / cron サンプル）、デプロイ手順（Dockerfile / containerized 実行）なども作成できます。どの情報を追加しますか？