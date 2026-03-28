# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants 経由）、ニュース収集・NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、データ品質チェック、監査ログ（発注/約定トレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムおよびデータ基盤向けに設計された Python モジュール群です。主な責務は以下です。

- J-Quants API からの株価・財務・カレンダー等の差分取得（ETL）
- RSS 等からのニュース収集と前処理
- OpenAI を使ったニュースセンチメント評価（銘柄別 / マクロ）
- ETF とマクロセンチメントを用いた市場レジーム判定
- ファクター計算（モメンタム / バリュー / ボラティリティ 等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル → 発注 → 約定のトレース）を保持する監査スキーマの初期化
- 各種ユーティリティ（日時ウィンドウ計算、統計正規化、DB保存ヘルパー など）

設計方針として、ルックアヘッドバイアス防止（内部で date.today() を勝手に参照しない）、冪等性、フェイルセーフ（API障害のフォールバック）を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API 取得・保存（差分取得・ページネーション・レート制御・リトライ・トークン自動リフレッシュ）
  - pipeline: 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - news_collector: RSS 収集、前処理、raw_news への冪等保存（SSRF対策・XML防御）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - audit: 監査ログスキーマ（signal_events / order_requests / executions）の初期化
  - stats: Zスコア正規化などの統計ユーティル
- ai/
  - news_nlp: 銘柄ごとのニュースセンチメントを OpenAI（gpt-4o-mini）で評価し ai_scores へ書込
  - regime_detector: ETF(1321)のMA乖離とマクロニュースの LLM センチメントを合成して market_regime を算出
- research/
  - factor_research: モメンタム / ボラティリティ / バリューの計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）計算、統計サマリー、ランク変換
- config.py
  - 環境変数からの設定読み込み（.env / .env.local 自動読込、オーバーライド制御）
  - settings オブジェクト経由で各種設定を取得可能

---

## セットアップ手順

前提:
- Python 3.10+ を推奨（typing の | 演算子や型ヒントを利用）
- duckdb, openai, defusedxml などが必要

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成と有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージのインストール（代表的な依存）
   ここはプロジェクトに合わせて requirements.txt を参照してください。参考例:
   ```
   pip install duckdb openai defusedxml
   ```
   開発で使う場合は logger 等やテストツールを追加してください。

4. 環境変数の設定
   プロジェクトルートの `.env` / `.env.local` を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読込を無効化できます）。以下は最低限の例です。

   .env.example（例）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DB 初期化（監査テーブルなど）  
   Python REPL やスクリプトで duckdb 接続を作成して監査スキーマを初期化できます（例は「使い方」参照）。

---

## 使い方（主要な API と実行例）

以下は代表的な呼び出し例です。各関数は duckdb の接続オブジェクトを受け取ります（duckdb.connect(...) を使用）。

- 設定値の取得
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  print(settings.is_live)
  ```

- DuckDB 接続の作成
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェックの一括実行）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- 個別 ETL ジョブの呼び出し例
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl

  fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 20))
  ```

- ニュースのセンチメントスコア（銘柄別）を作成して ai_scores に保存
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数か api_key 引数で指定
  ```

- 市場レジーム判定の実行（market_regime テーブルへ書込）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))  # api_key を引数で渡せます
  ```

- 監査データベースの初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- RSS フィードを取得（news_collector 内部ユーティリティ）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

注意点:
- OpenAI 呼び出しは API レートやエラーに対してリトライ・フォールバックする実装ですが、API キーが必須です（関数の api_key 引数または環境変数 OPENAI_API_KEY）。
- J-Quants API 呼び出しは settings.jquants_refresh_token を必要とします。
- ETL 等は外部 API を呼ぶため適切な認証情報とネットワーク環境が必要です。

---

## 設定（環境変数）

主要な環境変数（代表例）:

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（通知等で使用する場合）
- SLACK_CHANNEL_ID: Slack チャネル ID
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読込を無効化

config.py はプロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動読み込みします。テスト時は自動読込を無効にすることができます。

---

## ディレクトリ構成

主要ファイル・モジュールのツリー（src/kabusys 配下）:

- src/
  - kabusys/
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
      - calendar_management.py
      - news_collector.py
      - quality.py
      - stats.py
      - audit.py
      - (その他: clients / helpers 等想定)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/** その他の研究ユーティリティ
    - (strategy/, execution/, monitoring/ はパッケージ公開対象として __all__ に含まれるが、実装はこのコードベース内の別モジュールを参照してください)

上記は主要モジュールの要約です。各モジュールは docstring に仕様 / 設計方針 / 入出力が詳述されていますので、実装変更や拡張時は docstring を参照してください。

---

## 運用上の注意・ベストプラクティス

- ルックアヘッドバイアスを避けるため、どの関数も内部で現在時刻を安易に参照せず、呼び出し側が target_date を指定するパターンを推奨します。
- ETL は外部 API 呼出しを伴うため、ジョブは retry や監視（Slack 通知等）を組み合わせて運用してください。
- OpenAI 呼び出しは API 費用がかかるため、テスト時はモック（unittest.mock.patch）して呼び出しを置き換えてください。news_nlp と regime_detector 内の _call_openai_api はテスト用に差し替え可能に設計されています。
- DuckDB の executemany は空リストを受け付けないバージョンがあるため、空チェックを行っています。DB 操作ごとにトランザクションの管理やエラーハンドリングを確認してください。
- news_collector には SSRF 対策・XML 防御・gzip サイズチェック等の安全機構を実装しています。外部フィードの追加時もこれらの前提に沿って URL を検証してください。

---

## 参考 / 今後の拡張案

- strategy / execution モジュールの拡張（注文ロジック、リスク管理、ポジション管理）
- モニタリング & アラート機能の強化（Prometheus / Grafana / Slack）
- バックテストフレームワークとの統合
- news_nlp の多言語対応やモデル切替用の抽象化

---

もし README にサンプルスクリプト（cron 用 / Dockerfile / CI 設定）や requirements.txt、.env.example のテンプレートを追加したい場合は、必要な形式と内容を教えてください。