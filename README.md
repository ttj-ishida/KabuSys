# KabuSys

KabuSys は日本株のデータ取得・品質管理・AI を用いたニュースセンチメント解析・市場レジーム判定・監査ログ管理などを備えた日本株自動売買（リサーチ/実行基盤）向けのライブラリ群です。

この README はリポジトリ内のコードベースに基づき、プロジェクト概要、機能一覧、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下の要素を統合したプラットフォーム用ライブラリです。

- J-Quants API からの株価・財務・カレンダーの差分 ETL（取得 → DuckDB 保存）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）とニュースの NLP（OpenAI）による銘柄単位センチメントスコアリング
- 市場レジーム判定（ETF MA とマクロニュースの LLM センチメントの合成）
- 研究（ファクター計算、将来リターン、IC、Z-score 正規化等）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化ユーティリティ
- 環境変数/設定管理（.env 自動ロード機能を備えた settings API）

設計上の共通方針として、ルックアヘッドバイアス回避（内部で datetime.today()/date.today() を不用意に参照しない）、DuckDB を用いたローカルデータ管理、外部 API 呼び出しに対する堅牢なリトライやフェイルセーフを重視しています。

---

## 主な機能一覧

- data（kabusys.data）:
  - J-Quants クライアント（取得・保存・ページネーション・トークンリフレッシュ・レートリミット）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（is_trading_day / next_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS 取得、前処理、raw_news への保存）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）

- ai（kabusys.ai）:
  - ニュース NLP（score_news: 銘柄別センチメントを ai_scores テーブルへ保存）
  - 市場レジーム判定（score_regime: ETF 200日MA乖離とマクロニュースを合成）

- research（kabusys.research）:
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）

- 設定（kabusys.config）:
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - settings オブジェクト経由で環境変数を型付きで参照

---

## 前提・依存関係

- Python 3.10+
  - ソースで union 型（X | Y）を使用しているため 3.10 以上を想定しています。
- 主要依存パッケージ（例）:
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
  - その他標準ライブラリ（urllib, json, datetime, logging 等）

実際の環境では pyproject.toml / requirements.txt に記載された依存関係を使用してください（本リポジトリに依存一覧ファイルがある場合はそちらを優先）。

---

## 環境変数（主なもの）

kabusys.config.Settings から参照される主な環境変数：

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN (必須) : J-Quants のリフレッシュトークン（get_id_token に使用）
- kabu ステーション（注文連携）
  - KABU_API_PASSWORD (必須) : kabu API のパスワード
  - KABU_API_BASE_URL : デフォルト "http://localhost:18080/kabusapi"
- OpenAI / AI
  - OPENAI_API_KEY : OpenAI API キー（score_news / score_regime で使用）
- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- データベースパス（デフォルト値あり）
  - DUCKDB_PATH : 例 "data/kabusys.duckdb"
  - SQLITE_PATH : 監視用 DB 例 "data/monitoring.db"
- 監視 / 実行プロセス
  - PID_FILE_PATH (default data/execution.pid)
  - KILL_FLAG_PATH (default data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0 or 1)
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- システム設定
  - KABUSYS_ENV : "development" / "paper_trading" / "live"（デフォルト development）
  - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env` と `.env.local` を順に読み込みます。
- OS 環境変数が優先され、.env.local は .env より優先して上書きします。
- 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（例）

1. リポジトリをクローンしてプロジェクトルートへ移動

   git clone <repo-url>
   cd <repo>

2. Python 仮想環境を作成（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール

   - もし pyproject.toml / requirements.txt があればそれを使うのが最善です。
   例（pip）:
     pip install -U pip
     pip install duckdb openai defusedxml

   - 開発インストール:
     pip install -e .

   （プロジェクト配布の仕方により Poetry を使う場合は poetry install を使用）

4. 環境変数（.env）を作成

   プロジェクトルートに `.env`（および必要なら `.env.local`）を作り、必要な環境変数を設定します。
   最小例（実運用では必須値を設定してください）:

     JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
     OPENAI_API_KEY=あなたの_openai_api_key
     KABU_API_PASSWORD=あなたの_kabu_api_password
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

5. データディレクトリを作成（必要であれば）

     mkdir -p data

---

## 基本的な使い方（コード例）

以下は Python REPL やスクリプト内で利用する簡単な例です。各例では duckdb の接続を作成し、settings を利用しています。

- settings の利用（環境変数参照）

  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.env)

- DuckDB 接続の作成

  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))

- ETL を日次実行（run_daily_etl）

  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())

- ニュースセンチメントスコア（AI）を計算して保存

  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY は環境変数で設定されていれば api_key を省略可能
  written_count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written_count}")

- 市場レジーム判定

  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ用 DB（監査専用）を初期化

  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  # settings.duckdb_path を使うか別 DB を指定可能
  audit_conn = init_audit_db(settings.duckdb_path)
  # これで監査用テーブル（signal_events, order_requests, executions）等が作成されます

- 研究用ユーティリティ（ファクター計算）

  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  # momentum は dict のリスト

メモ:
- OpenAI を使う処理は OPENAI_API_KEY（あるいは score_* に直接 api_key を渡す）を必要とします。
- J-Quants 関連は JQUANTS_REFRESH_TOKEN を必ず設定してください。

---

## 提案される運用フロー（簡易）

1. データ取得:
   - 日次バッチで run_daily_etl を実行して prices / financials / calendar を更新。
2. 品質チェック:
   - run_daily_etl 内で品質チェックを実行（設定により有効/無効）。
   - 問題があればアラートやログで運用側に通知。
3. ニュース集約・スコアリング:
   - news_collector で RSS を収集 → raw_news に保存。
   - score_news を実行して銘柄別 ai_scores を更新。
4. レジーム判定:
   - score_regime を実行して market_regime を更新。
5. 戦略 → 発注（監査ログ）:
   - 戦略層は監査テーブル (signal_events / order_requests / executions) を用いて発注のトレーサビリティを保持。

---

## ディレクトリ構成（主要ファイルと役割）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数/.env 管理、Settings オブジェクトを提供
  - ai/
    - __init__.py
    - news_nlp.py
      - raw_news → ai_scores（OpenAI を用いる銘柄別センチメント）
    - regime_detector.py
      - ETF (1321) MA とニュースセンチメントを合成して market_regime に書き込み
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・トークン管理・レートリミット）
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl, ...）
    - calendar_management.py
      - market_calendar 管理・営業日判定ユーティリティ・calendar_update_job
    - news_collector.py
      - RSS 取得・前処理・raw_news への保存ロジック（SSRF 対策・XML セキュリティ等）
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付整合性）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログテーブル DDL / init_audit_schema / init_audit_db
    - etl.py
      - ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム・ボラティリティ・バリュー等の計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリ、rank 等
  - monitoring, execution, strategy（パッケージ名として __all__ に記載されているが実装は別途）
    - （本リポジトリでは主要な data/ ai/ research が中心）

---

## 注意事項・運用上のポイント

- ルックアヘッドバイアス対策が各所で施されています。ETL/解析関数は内部で現在時刻を不用意に参照しない設計になっています。バックテスト等で利用する際は、過去時点で入手可能なデータのみを使う運用を徹底してください。
- OpenAI/外部 API 呼び出しはリトライとフェイルセーフ（デフォルトスコア 0.0 等）で回復可能に設計されていますが、コスト・レート制限に注意してください。
- news_collector は SSRF 防止や XML の安全パースを行いますが、外部フィードの品質・文字コード等は実運用で起こりうる特殊ケースを考慮して下さい。
- DuckDB のバージョン特性（executemany の空リストなど）に対応する実装上の注意がコード内にあります。運用時は利用する DuckDB のバージョン互換性を確認してください。

---

## 参考（トラブルシューティング）

- .env が読み込まれない場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認
  - プロジェクトルートが .git または pyproject.toml によって検出されることを確認
- OpenAI エラー時:
  - OPENAI_API_KEY を再確認
  - API レート制限やクォータを確認
- J-Quants API 401 エラー:
  - JQUANTS_REFRESH_TOKEN を確認（get_id_token は自動リフレッシュ処理あり）

---

必要であれば、この README をベースにより導入手順（Docker compose 例、systemd サービス化、定期バッチ cron/airflow のサンプル）、CI 設定やテストの書き方（単体テストでの OpenAI/J-Quants 呼び出しのモック例）なども追加できます。どの情報を優先して追加しますか？