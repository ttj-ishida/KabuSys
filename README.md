# KabuSys

日本株の自動売買プラットフォーム向けユーティリティ群（データ ETL / ニュース NLP / リサーチ / 監査ログ 等）

このリポジトリは、J-Quants や各種 RSS / OpenAI を利用したデータパイプライン、ニュースセンチメント評価、ファクター計算、取引監査テーブル生成などを提供する Python モジュール群です。バックテストや本番実行の基盤として利用できます。

重要: 本 README はソースコードコメントと実装に基づいて作成しています。実際に運用する前に設定・権限・API 料金などを十分に確認してください。

## 概要

- ETL（J-Quants からの株価・財務・カレンダーの差分取得・保存）
- ニュース収集（RSS → raw_news）と NLP による銘柄センチメント算出（OpenAI）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM スコアを統合）
- リサーチ用ファクター計算（モメンタム / ボラティリティ / バリュー 等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal_events / order_requests / executions）スキーマ初期化ユーティリティ
- 設定管理（.env / 環境変数の自動読み込み、Settings API）

## 主な機能一覧

- kabusys.data
  - ETL パイプライン: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（差分取得・ページネーション・リトライ・レート制御）
  - ニュース収集: RSS 取得、前処理、raw_news への保存ロジック（SSRF 対策、サイズ制限）
  - カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - データ品質チェック: check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
  - 監査ログ初期化: init_audit_schema / init_audit_db
  - 統計ユーティリティ: zscore_normalize
- kabusys.ai
  - ニュース NLP: score_news（OpenAI を使って銘柄ごとにセンチメント）
  - レジーム判定: score_regime（ETF 1321 の MA とマクロニュース LLM を統合）
- kabusys.research
  - ファクター計算: calc_momentum / calc_value / calc_volatility
  - 特徴量探索: calc_forward_returns / calc_ic / factor_summary / rank
- 設定管理
  - kabusys.config.settings: 必要な環境変数を型付きプロパティで取得
  - .env 自動ロード（プロジェクトルート検出: .git または pyproject.toml）

## セットアップ手順

以下は一般的な開発 / 実行手順の例です。実行環境や依存パッケージ（duckdb / openai / defusedxml 等）は適宜インストールしてください。

1. Python 仮想環境作成（例: Python 3.9+ 推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 開発中であればローカルインストール:
     - pip install -e .

   必要になりそうな主要パッケージ（例）
   - duckdb
   - openai
   - defusedxml

3. 環境変数 / .env ファイル
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（読み込み順: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

   代表的な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD : kabuステーション API のパスワード（発注連携がある場合）
   - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID : Slack チャンネル ID
   - OPENAI_API_KEY : OpenAI API キー（ai.score_news / score_regime で使用）

   任意 / デフォルト値あり
   - KABUSYS_ENV : development / paper_trading / live（デフォルト development）
   - LOG_LEVEL : DEBUG / INFO / ...（デフォルト INFO）
   - KABU_API_BASE_URL : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH : SQLite（監視用）パス（デフォルト data/monitoring.db）

4. API キーや DB ファイルの配置・権限を確認してください。

## 使い方（コード例）

以下は代表的なユースケースの最小コード例です。実行前に必要な環境変数・DB スキーマ準備を行ってください。

- DuckDB 接続の取得（例）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア（OpenAI 必須）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY を環境変数で設定するか、api_key 引数で渡す
  written = score_news(conn, target_date=date(2026,3,20))
  print(f"書込み銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ DB 初期化（監査専用 DB を作る場合）
  ```python
  from kabusys.data.audit import init_audit_db

  conn_audit = init_audit_db("data/audit.duckdb")
  # conn_audit は監査テーブルが作成済み
  ```

- ファクター計算（研究用途）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  target = date(2026,3,20)
  mom = calc_momentum(conn, target)
  val = calc_value(conn, target)
  vol = calc_volatility(conn, target)
  ```

注意:
- AI 関連関数は外部 API（OpenAI）を呼びます。API コール制限や利用料金に注意してください。
- バックテスト時の Look-ahead バイアスに関する実装上の配慮（コード内コメント）を必ず確認してください（多くの関数が date を明示的に受け取り、datetime.today() を使わないよう設計されています）。

## ディレクトリ構成

（ソースは `src/kabusys` に格納されています。代表的なファイル/モジュールは次の通り）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境設定読み込み（.env 自動ロード、Settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースセンチメント（score_news）
    - regime_detector.py             — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETL 結果クラス再エクスポート
    - jquants_client.py              — J-Quants API クライアント（fetch/save・認証・レート制御）
    - news_collector.py              — RSS 収集と前処理
    - calendar_management.py         — マーケットカレンダー管理
    - quality.py                     — データ品質チェック
    - stats.py                       — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                       — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py             — ファクター計算（momentum/value/volatility）
    - feature_exploration.py         — 将来リターン / IC / summary 等
  - research/*（上記に続く）
  - その他モジュール（将来の strategy / execution / monitoring 用に __all__ に定義あり）

## 設定と注意点

- .env の自動読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）を探索し `.env` / `.env.local` を読み込みます。
  - OS 環境変数が優先され、.env は上書きしません。.env.local は上書き用（override=True）。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- 環境（KABUSYS_ENV）
  - 有効値: `development`, `paper_trading`, `live`
  - Settings.is_live / is_paper / is_dev で判定可能

- OpenAI / J-Quants の API 呼び出し
  - J-Quants クライアントにはレート制限（120 req/min）とリトライ・401 自動リフレッシュロジックがあります。
  - OpenAI 呼び出しは gpt-4o-mini を想定し、JSON Mode を利用しています。API エラー時はフェイルセーフ（多くの場合 0.0 にフォールバック）やリトライロジックが組み込まれています。
  - AI 系処理は外部 API を利用するため、API キーの設定・料金・レートに注意してください。

- Look-ahead bias（先見性バイアス）
  - コード中に明示されている設計方針として、バックテストやスコア計算で datetime.today() を参照しない、target_date より未来のデータを使わないようにしています。バックテスト用途ではこの設計に従ってください。

## 開発・テスト

- モジュール内のプライベートな API コール（例: News/OpenAI 呼び出し）はテストでモックする設計になっています（_call_openai_api などを unittest.mock.patch で差し替え可能）。
- DuckDB を用いるため、単体テストでは `:memory:` の接続を使うことでディスクを汚染せずに実行できます。
- .env の自動読み込みはテストの隔離のため無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

## ライセンス / 貢献

このドキュメントではライセンスは明示していません。実際のリポジトリでは LICENSE ファイルを設置してください。貢献や issue、PR はリポジトリのプルリクエストルールに従ってください。

---

README に記載されたコード例や設定はサンプルです。実運用前に十分な確認（テスト、シミュレーション、権限管理、API 使用量確認）を行ってください。質問や追加説明が必要であれば、具体的な目的（ETL 実行 / OpenAI のテスト方法 / 監査スキーマ初期化 など）を教えてください。