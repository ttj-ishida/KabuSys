# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants 経由のデータ取得）、ニュース収集・NLP（OpenAI 経由）、リサーチ（ファクター計算）、監査ログ等のユーティリティを提供します。

> この README はリポジトリ内の実装（src/kabusys 以下）に基づいて作成しています。

## プロジェクト概要

KabuSys は次の目的を持つモジュール群を提供します。

- J-Quants API からの株価 / 財務 / 市場カレンダーの差分取得（ETL）
- RSS ベースのニュース収集と前処理（SSRF・サイズ等の安全対策実装）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄別 ai_score、マクロセンチメント）
- 市場レジーム判定（ETF 1321 の MA200乖離 + マクロセンチメント合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、統計サマリ、Zスコア正規化）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ / 初期化（シグナル → 発注 → 約定のトレーサビリティ）
- DuckDB を中心としたローカルデータストア操作 utilities

設計上のポイント：

- ルックアヘッドバイアスを避ける実装（target_date を引数で明示、内部で date.today() を直接参照しない箇所が多い）
- API 呼び出しはリトライ／バックオフ／レート制御を実装
- DB 書き込みは冪等（ON CONFLICT / upsert）を基本とする
- テキストパースや外部URL取得はセキュリティを考慮（SSRF対策、XMLの安全パーサ等）

---

## 主な機能一覧

- data.jquants_client
  - fetch_daily_quotes / save_daily_quotes（OHLCV）
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar
  - fetch_listed_info
  - 内部で ID トークンの自動取得・キャッシュ、レート制限、リトライ実装

- data.pipeline
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック を順に実行する日次 ETL
  - run_prices_etl / run_financials_etl / run_calendar_etl：個別 ETL ジョブ

- data.news_collector
  - fetch_rss, preprocess_text 等、RSS 取得と記事の前処理（URL 正規化、トラッキング除去、ID 生成）

- ai.news_nlp
  - score_news(conn, target_date, api_key=None): 銘柄ごとのニュースセンチメントを OpenAI に投げて ai_scores に保存

- ai.regime_detector
  - score_regime(conn, target_date, api_key=None): ETF 1321 の MA200 乖離とマクロセンチメントを合成して market_regime に保存

- data.quality
  - run_all_checks: 欠損・重複・スパイク・日付不整合チェックを実行し QualityIssue を返す

- data.audit
  - init_audit_schema / init_audit_db: 監査ログ用テーブル群を初期化（signal_events, order_requests, executions 等）

- research.*
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize（クロスセクション Z スコア化）

- config
  - Settings クラスで環境変数をラップし .env 自動読込（プロジェクトルート検出）を行う

---

## セットアップ手順

前提
- Python 3.10 以上（型記法に | を使用）
- DuckDB を使用（ローカル DB）
- OpenAI API を利用する場合は OpenAI の API キーが必要
- J-Quants API のリフレッシュトークンが必要（ETL で利用）

1. リポジトリをクローンし、開発環境にインストール（パッケージ化されている前提）
   ```
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   ```

2. 必要パッケージ（例）
   ```
   pip install duckdb openai defusedxml
   ```
   （実際のプロジェクトでは requirements.txt / pyproject.toml を利用してください）

3. 環境変数の設定
   - プロジェクトルートに .env（および必要なら .env.local）を配置すると自動で読み込まれます（config.py による自動ロード）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（必須 / ETL 用）
   - OPENAI_API_KEY：OpenAI API キー（ai モジュールを使う場合に必須）
   - KABU_API_PASSWORD：kabuステーション API のパスワード（実取引連携用）
   - KABU_API_BASE_URL：kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID：通知用（任意）
   - DUCKDB_PATH：DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH：SQLite（監視用）パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV：development / paper_trading / live（デフォルト development）
   - LOG_LEVEL：DEBUG/INFO/...（デフォルト INFO）
   - 各種監視パラメータ（PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT 等）

4. データベース初期化（監査ログの例）
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_schema

   conn = duckdb.connect("data/kabusys.duckdb")
   init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（簡易ガイド）

以下は代表的な操作例です。実際にはロガー設定や例外処理を組み込んでください。

- DuckDB 接続を作成
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（today を対象）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=None, id_token=None)
  print(result.to_dict())
  ```

- ニュースセンチメントをスコア化して DB に保存
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  n_written = score_news(conn, target_date=date(2026,3,19), api_key=None)  # api_key None -> env OPENAI_API_KEY を使用
  print("written:", n_written)
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026,3,19), api_key=None)
  ```

- ファクター計算（研究用途）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  t = date(2026,3,19)
  mom = calc_momentum(conn, t)
  val = calc_value(conn, t)
  vol = calc_volatility(conn, t)
  ```

- 監査 DB を新規初期化（専用ファイル）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- config の利用例
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

注意点:
- OpenAI を利用する関数は api_key を引数で注入可能（テスト向け）。引数に None を渡すと環境変数 OPENAI_API_KEY が使われます。
- ETL / ニュース収集 / AI 呼び出しは外部 API を叩くため、API キー・ネットワークの準備を行ってください。
- ETL 実行時は J-Quants の利用規約、レート制限に注意してください（jquants_client はレート制御を実装しています）。

---

## .env の例（主要項目）

以下をプロジェクトルートの .env に設定してください（例）。

KabuSys は .env/.env.local をプロジェクトルートから自動読み込みします（.git か pyproject.toml のあるディレクトリを root として探索）。

.example（説明付き）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# OpenAI
OPENAI_API_KEY=sk-...

# kabuステーション（任意）
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境 / ログ
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## ディレクトリ構成（主なファイル）

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
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research.__init__.py にて research API を再エクスポート

（上記は現コードベースに含まれる主要モジュールです。 strategy / execution / monitoring 等はパッケージ __all__ で想定されていますが、実装は別箇所にある可能性があります）

---

## 注意事項 / 実運用メモ

- センチメント・レジーム系は OpenAI API を利用します。API のレスポンス/コストについて運用上の管理を行ってください。
- J-Quants の ID トークンは自動でリフレッシュされる仕組みがありますが、rate limit（120 req/min）や API 側のレート制御を尊重してください。
- DuckDB を使用しているため、大量データ運用時はファイル配置・I/O に注意してください。
- ニュース収集は外部 URL を取得するため、SSRF 対策・レスポンスサイズ制限などの実装がありますが、運用環境のネットワーク・プロキシポリシーを確認してください。
- テスト時に .env の自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 参考

- 主要 API:
  - kabusys.data.pipeline.run_daily_etl
  - kabusys.ai.news_nlp.score_news
  - kabusys.ai.regime_detector.score_regime
  - kabusys.data.jquants_client.*（fetch / save 系）
  - kabusys.data.audit.init_audit_schema / init_audit_db

不明点や README に加えたい使用例があれば、具体的なユースケース（ETL の自動化、バッチ運行、戦略連携など）を教えてください。追加のサンプルや運用手順を用意します。