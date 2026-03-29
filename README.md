# KabuSys

KabuSys は日本株向けの自動売買（データプラットフォーム・リサーチ・AI 評価・監査ログ）を目的とした Python ライブラリ群です。  
このリポジトリにはデータ取得（J-Quants）、ETL、ニュース収集・NLP、マーケットカレンダー管理、ファクター計算、監査ログ（発注→約定のトレーサビリティ）などの主要機能が含まれます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API の例）
- 環境変数 / 設定
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下の目的に沿って設計されたモジュール群です。

- J-Quants API からの株価・財務・カレンダー等の差分 ETL（DuckDB に保存）
- RSS ベースのニュース収集と前処理（SSRF / XML 攻撃や巨大レスポンスへの対策あり）
- OpenAI（gpt-4o-mini）を用いたニュースのセンチメント付与（銘柄ごと、マクロセンチメント）
- 市場レジーム判定（ETF 1321 の MA とマクロセンチメントを合成）
- リサーチ用ファクター計算（モメンタム / ボラティリティ / バリュー 等）と特徴量解析（IC 等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution のトレースを保証するテーブル群）
- 設定の .env 自動読み込み（プロジェクトルート検出ベース）

設計方針の一部:
- ルックアヘッドバイアス防止（関数内部で datetime.today()/date.today() を直接参照しない等）
- DuckDB を中心としたローカル分析・ETL（本番発注 API とは分離）
- 冪等性（DB 書き込みは ON CONFLICT で安全化）
- 外部 API 呼び出しに対するリトライ・レート制御・フェイルセーフ

---

## 機能一覧

主な機能（モジュール）:
- kabusys.config
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得ラッパー
- kabusys.data
  - pipeline: 日次 ETL（prices, financials, calendar）実行 run_daily_etl
  - jquants_client: J-Quants API ラッパ（認証、ページネーション、保存関数）
  - news_collector: RSS 取得・前処理・raw_news 保存
  - calendar_management: 営業日判定 / next/prev_trading_day / calendar_update_job
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログテーブルの初期化・DB 作成ユーティリティ
  - stats: zscore_normalize 等の汎用統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄単位ニュースセンチメント付与（ai_scores テーブルへ保存）
  - regime_detector.score_regime: ETF MA とマクロセンチメントを合成して market_regime に保存
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- 監視・発注・ストラテジー関連（パッケージインターフェースに含まれるが、この README で提供されているコードスニペットは上記が中心）

セキュリティ / 信頼性上の配慮:
- J-Quants のレート制御（120 req/min）を守る RateLimiter 実装
- HTTP レスポンスのサイズ上限（RSS 取得時の MAX_RESPONSE_BYTES）
- リダイレクト時のホスト検証（SSRF 対応）
- OpenAI 呼び出しに対するリトライとフェイルセーフ（失敗時は 0.0 フォールバック 等）

---

## セットアップ手順

最低限必要な Python バージョン: 3.10 以上（型注釈で | ユニオンを使用）

1. リポジトリをクローン
   git clone <repo_url>
   cd <repo_dir>

2. Python 仮想環境の作成（任意）
   python -m venv .venv
   source .venv/bin/activate  # Unix
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   pip install duckdb openai defusedxml

   （必要に応じて他パッケージを追加する。requirements.txt がある場合はそれを使用してください。）

4. 環境変数の設定
   プロジェクトルートに .env または .env.local を作成すると、自動で読み込まれます（既定で .env → .env.local の順で読み込み）。
   自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   必須の環境変数（後述）を .env に設定してください。

5. DuckDB（データベース）と監査ログ DB の初期化（例）
   - アプリ内から init を呼ぶことで DB ファイルを作成・スキーマ適用できます（例は下記の使い方参照）。

---

## 環境変数 / 設定

主に以下を使用します（必須は README 内で明記）:

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- KABU_API_PASSWORD: kabu ステーション API を使う場合のパスワード
- SLACK_BOT_TOKEN: Slack 通知を使用する場合の Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先のチャンネル ID

OpenAI 関連:
- OPENAI_API_KEY: kabusys.ai.* モジュールが使用（score_news, score_regime）。関数に api_key を渡すことも可能。

データベース / ログ:
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用途の SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

自動 .env 読み込み:
- .env / .env.local はプロジェクトルート（.git または pyproject.toml の親ディレクトリ）で探索され、自動で読み込まれます。

.env の例（最小）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（主要 API の例）

以下では簡単な Python スニペットを示します。実行前に環境変数（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN など）を設定してください。

- DuckDB 接続の作成:
  from pathlib import Path
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

- 監査ログ DB の初期化:
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # または既存接続にスキーマを適用:
  # from kabusys.data.audit import init_audit_schema
  # init_audit_schema(conn, transactional=True)

- 日次 ETL の実行:
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  res = run_daily_etl(conn, target_date=date(2026,3,20))
  print(res.to_dict())

- ニュースセンチメント（銘柄ごと）スコア付与:
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # None→環境変数 OPENAI_API_KEY
  print(f"scored {n_written} codes")

- 市場レジーム判定:
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20), api_key=None)

- ファクター計算／リサーチ:
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  fwd = calc_forward_returns(conn, date(2026,3,20), horizons=[1,5,21])

- データ品質チェック:
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)

注意点:
- OpenAI の呼び出しはモデル gpt-4o-mini を想定し JSON mode にて厳密な出力を期待しています。API レスポンスの不正や例外発生時はフェイルセーフでスコアを 0.0 に置換するなどの設計です。
- J-Quants クライアントはレート制御・リトライ・401 自動リフレッシュ等を実装しています。

---

## ディレクトリ構成

主要ファイル / ディレクトリ（src/kabusys ベース）

- kabusys/
  - __init__.py
  - config.py                      - 環境変数・設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                   - ニュースセンチメント（銘柄単位）処理
    - regime_detector.py            - 市場レジーム判定（ma200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py             - J-Quants API クライアント（取得/保存）
    - pipeline.py                   - ETL パイプラインと run_daily_etl
    - etl.py                        - ETLResult の公開
    - news_collector.py             - RSS ニュース収集と前処理
    - calendar_management.py        - マーケットカレンダー管理 / 営業日判定
    - quality.py                    - データ品質チェック群
    - stats.py                      - 汎用統計（zscore_normalize）
    - audit.py                      - 監査ログスキーマ初期化（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py            - Momentum/Value/Volatility 等の計算
    - feature_exploration.py        - 将来リターン / IC / 統計サマリー
  - research のユーティリティで data.stats を参照

（その他）
- monitoring, strategy, execution などの名前はパッケージの __all__ に含まれますが、詳細実装はこの README のコード一覧外です。

---

## 補足 / 運用上の注意

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を親に持つディレクトリ）を起点に行われます。CI やテストで自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB を使用する際の executemany の空パラメータ等、DuckDB のバージョン差分に依存する注意点がコード中に反映されています（空の executemany 呼び出しを避ける実装など）。
- ニュース収集、OpenAI 呼び出し、J-Quants API 等は外部接続を伴うため、運用時は API レート制限やコスト管理に注意してください。
- 本ライブラリの多くの関数は「ルックアヘッドバイアス」対策として target_date を明示的に受け取り、内部で現在時刻を参照しない設計となっています（バックテスト用途で重要）。

---

もし README に追加したい具体的な情報（例: CI / テスト実行方法、requirements.txt、ライセンス表記、具体的な運用手順のテンプレートなど）があれば教えてください。必要に応じて README を拡張します。