# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュースの NLP スコアリング、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（発注→約定トレーサビリティ）などを提供します。

---

## プロジェクト概要

KabuSys は、以下を目的とした Python モジュール群です。

- J-Quants API からの差分 ETL（株価 / 財務 / マーケットカレンダー）
- ニュースの収集・前処理・LLM によるセンチメント評価（銘柄別スコア）
- ETF（1321）の MA とマクロニュースを組み合わせた市場レジーム判定
- リサーチ用ファクター（モメンタム / バリュー / ボラティリティ等）の計算と統計ユーティリティ
- 監査ログ（signal → order_request → execution）のための DuckDB スキーマ初期化
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計上の特徴：
- DuckDB を DB 層に採用（オンディスク / インメモリ両対応）
- LLM 呼び出しには OpenAI（gpt-4o-mini）を想定、JSON Mode を利用
- Look-ahead bias を避ける設計（datetime.today()/date.today() を直接参照しない等）
- 冪等性・リトライ・レート制御（J-Quants クライアント、news/etl 等）
- セキュリティ考慮（RSS の SSRF 対策、XML パースの安全化など）

---

## 主な機能（機能一覧）

- data/
  - jquants_client: J-Quants API クライアント（fetch/save の各関数、トークン管理、レート制限）
  - pipeline: 日次 ETL の統合処理（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - calendar_management: 市場カレンダー管理と営業日判定ヘルパー（is_trading_day 等）
  - news_collector: RSS 収集と前処理（fetch_rss 等）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - audit: 監査ログ用テーブル定義・初期化（init_audit_schema / init_audit_db）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp: ニュースを銘柄ごとに集約し LLM でセンチメント（score_news）
  - regime_detector: ETF（1321）の MA とマクロニュースセンチメントを合成して市場レジーム判定（score_regime）
- research/
  - factor_research: momentum/value/volatility の計算（calc_momentum 等）
  - feature_exploration: 将来リターン計算、IC、統計サマリ等
- config.py: 環境変数管理（.env の自動ロード、必要な設定のラッパー）
- audit / monitoring 関連の各種ユーティリティ

---

## 要求環境 / 依存

- Python 3.10+（PEP 604 の型記法（X | Y）を使用）
- 必要な主なパッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ: urllib, json, datetime, logging, pathlib, typing 等

（実行環境に合わせて requirements.txt を用意してください。サンプル: `pip install duckdb openai defusedxml`）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS/Linux
   .venv\Scripts\activate       # Windows (PowerShell 等)
   ```

3. 依存パッケージをインストール
   （プロジェクトに requirements.txt がある場合はそれを利用。無い場合は最低限以下）
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数 (.env) を準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能）。
   - 必須設定（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - OPENAI_API_KEY: OpenAI の API キー（score_news 等で使用）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（必要な場合）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（必要な場合）

   サンプル `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxx...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DB ファイル用ディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（基本例）

以下は主要な API の利用例です。実行は Python スクリプトや REPL で行ってください。

- 共通: DuckDB 接続の作成
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))  # settings.duckdb_path は Path を返す
  ```

- 日次 ETL 実行（J-Quants からの取得→保存→品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  # target_date を省略すると今日（ローカルタイム）を基準に実行します
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（指定日）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # score_news は OPENAI_API_KEY を環境変数 または api_key 引数で受け取ります
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定（ETF 1321 の MA とマクロ記事を使う）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # 必要に応じてアプリ側で監査ログを挿入 / 参照できます
  ```

- リサーチ: モメンタム / ボラティリティ計算
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_volatility

  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  volatility = calc_volatility(conn, target_date=date(2026, 3, 20))
  ```

注意:
- OpenAI の呼び出しは API キーが必須です。score_news/score_regime は api_key 引数で上書き可能です。
- 多くの処理は DuckDB 上の特定テーブル（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime 等）を前提とします。ETL を実行してテーブルを整備してください。
- J-Quants のトークンは config.Settings.jquants_refresh_token を通じ自動で refresh され、jquants_client が id_token を取得します。

---

## 主要モジュール / ディレクトリ構成

（src/kabusys 以下の主要ファイル / モジュール一覧）

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
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research パッケージは zscore_normalize 等を再利用
  - その他（strategy, execution, monitoring 等のトップレベルパッケージ名は __all__ に含まれていますが、ここに掲載されている機能が中心です）

---

## 設定・開発時の注意

- 環境変数の自動ロード:
  - config.py はプロジェクトルートを .git または pyproject.toml を基に探索し、.env/.env.local を自動読み込みします。テスト時等に自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Look-ahead bias 回避:
  - 多くの関数は内部で `date`/`datetime` を引数として受け、内部的に today を参照しない設計を採っています。バックテスト等での使用時は `target_date` を明示してください。
- OpenAI のレスポンスは厳密な JSON を期待する設計ですが、実際には前後に余計なテキストが混入する場合を考慮してパース耐性を実装しています。
- DuckDB の executemany に空配列を渡すとエラーになるバージョンがあるため、コード内で空チェックを行っています。

---

## 貢献・拡張

- 新しい ETL のデータソースやニュースフィードを追加する場合は、data/jquants_client.py や data/news_collector.py の設計を踏襲してください（冪等性・レート制御・エラーハンドリング）。
- AI モジュール（news_nlp, regime_detector）はテスト容易性を考慮して内部で API 呼び出しを分離しています。ユニットテストでは _call_openai_api をモックしてください。

---

README に含めるべき追加の情報（例: ライセンス、CI、詳細な API ドキュメント）があれば教えてください。必要なら README を拡張します。