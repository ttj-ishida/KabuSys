# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を使用したセンチメント）、研究用ファクター計算、監査ログ（約定トレース）などを備えたモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計された内部ライブラリ群です。主な目的は以下です。

- J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に保存する ETL。
- RSS ニュース収集と OpenAI を用いた銘柄別ニュースセンチメント生成（ai_scores）。
- マーケットレジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成）。
- 研究用途のファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ。
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ生成。
- データ品質チェック（欠損、重複、スパイク、日付不整合）。

設計上の特徴：
- ルックアヘッドバイアスを避ける（内部で date.today() に依存しない設計が多く組み込まれています）。
- DuckDB を主データストアとして利用、冪等保存（ON CONFLICT）で安全に更新。
- 外部 API 呼び出しはリトライ・バックオフやレートリミット機構を備える。
- OpenAI 呼び出しは JSON Mode を利用して厳密な機械可読出力を期待します。

---

## 機能一覧（主なモジュールと役割）

- kabusys.config
  - 環境変数ロード（.env / .env.local を自動ロード。無効化フラグあり）
  - settings オブジェクトでアプリ設定を提供（J-Quants トークン、OpenAI、DB パス等）
- kabusys.data
  - jquants_client: J-Quants API クライアント（fetch / save 関数、認証・リトライ・レート制御）
  - pipeline: 日次 ETL 実行（run_daily_etl, run_prices_etl, ...）と ETLResult
  - news_collector: RSS 収集・前処理・保存（SSRF 防御・gzip リミットなど）
  - calendar_management: 市場カレンダー（is_trading_day, next_trading_day, calendar_update_job）
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit: 監査ログ（signal_events / order_requests / executions）スキーマ初期化
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- kabusys.ai
  - news_nlp.score_news: ニュースを OpenAI でスコア化して ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA200 とマクロニュースで市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility など
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

設計方針として、ETL・研究モジュールは発注や実際の口座操作にはアクセスしないように分離されています。

---

## セットアップ手順

前提：
- Python 3.9+（typing の新しい機能を使用しているため推奨）
- ネットワーク接続（J-Quants / OpenAI / RSS ソース へのアクセス）

1. リポジトリをクローン（またはパッケージに含めてインストール）
   - 開発時: pip editable install
     ```
     git clone <repo-url>
     cd <repo>
     pip install -e ".[dev]"   # もし setup/pyproject に extras を用意している場合
     ```
   - シンプルに必要パッケージをインストール:
     ```
     pip install duckdb openai defusedxml
     ```
     （openai は OpenAI SDK、defusedxml は安全な XML パース用）

2. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（使用する場合）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（使用する場合）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（execution 関連）
     - OPENAI_API_KEY: OpenAI 呼び出しに使用（score_news / score_regime）
   - オプション（デフォルト値あり）:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / ...
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB、デフォルト data/monitoring.db）
   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

3. データベースディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

4. DuckDB のスキーマ初期化などはアプリ側の初期化ロジックを使うか、kabusys.data.audit.init_audit_db などを使用して作成できます。

---

## 使い方（代表的な例）

以下は簡単な Python からの呼び出し例です。

- DuckDB 接続と日次 ETL 実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア生成（OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数で指定）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions のテーブルが作成されます
  ```

- 研究用のファクター計算
  ```python
  from kabusys.research import calc_momentum, calc_value
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  ```

注意点:
- OpenAI 呼び出しはレート・コストが発生します。テストではモック化（unittest.mock.patch）を想定しています。
- run_daily_etl などは外部 API に依存するため、適切な認証環境（J-Quants トークン等）が必要です。
- ETL の各ステップは独立してエラーハンドリングされ、部分失敗しても可能な範囲で継続する設計です。戻り値の ETLResult で問題の有無を確認してください。

---

## よく使う設定 / 環境変数一覧

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（get_id_token の元）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector）
- SLACK_BOT_TOKEN — Slack 通知を行う場合の Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- KABU_API_PASSWORD — kabu API のパスワード（発注連携時）

任意 / デフォルトあり:
- KABUSYS_ENV — development / paper_trading / live（default: development）
- LOG_LEVEL — ログレベル（default: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（default: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys）

- __init__.py
  - パッケージメタ情報（__version__ 等）
- config.py
  - .env 自動読み込み、settings オブジェクト（環境変数アクセス）
- ai/
  - __init__.py
  - news_nlp.py — ニュースを OpenAI でスコア化して ai_scores に保存
  - regime_detector.py — ETF 1321 の MA200 とマクロニュースで市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save, 認証, リトライ, rate limiter）
  - pipeline.py — ETL 日次パイプライン（run_daily_etl 等）と ETLResult
  - news_collector.py — RSS 取得・前処理・raw_news 保存（SSRF 対策・gzip 保護）
  - calendar_management.py — market_calendar 管理、営業日判定
  - quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - audit.py — 監査ログスキーマ定義と初期化ユーティリティ
  - etl.py — pipeline.ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py — calc_momentum, calc_value, calc_volatility
  - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank

---

## 設計上の注意・補足

- Look-ahead Bias 対策
  - 多くのモジュールは意図的に date.today() を直接使わず、関数呼び出し側が target_date を明示することでバックテスト時のルックアヘッドを回避しています。
  - データ取得時は fetched_at を UTC で記録して「いつデータが得られたか」を追跡できるようにしています。
- 冪等性
  - J-Quants から取得したデータは DuckDB 側で ON CONFLICT DO UPDATE により冪等に保存します。
- 外部 API
  - J-Quants, OpenAI, RSS 取得の各所でリトライ・バックオフ・レート制御・安全対策（SSRF, gzip 限度, defusedxml）を実装しています。
- テスト
  - OpenAI 呼び出し等はモック可能なように内部呼び出し関数が分離されています（例: _call_openai_api はパッチ可能）。

---

必要であれば、セットアップのための requirements.txt / pyproject.toml のサンプルや、CI 用のテスト実行手順、実運用での監視・通知・ロギング設定例などの README 拡張を作成します。どの情報を追加しますか？