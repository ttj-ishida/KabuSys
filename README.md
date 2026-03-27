# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、研究用ファクター計算、監査ログ（約定トレーサビリティ）などのユーティリティをまとめて提供します。

主な設計方針の概要
- Look‑ahead バイアス対策：内部処理で datetime.today() / date.today() を直接参照しない設計（API 呼び出しやスコア算出は明示的な target_date を受け取る）。
- DuckDB を中心にデータを保持し、ETL は冪等に実行可能。
- 外部 API 呼び出しに対してリトライ・バックオフ・レート制御・フェイルセーフを備える。
- ニュース収集で SSRF / XML 攻撃対策を考慮。

## 機能一覧
- 環境設定管理（自動 .env 読み込み / settings API）
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.slack_bot_token など
- データ ETL（J-Quants 経由）
  - 日次株価（raw_prices）の差分取得・保存
  - 財務データ（raw_financials）
  - JPX マーケットカレンダー（market_calendar）
  - run_daily_etl 等の統合エントリポイント（kabusys.data.pipeline）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）→ raw_news、news_symbols への保存（SSRF・サイズ制限・前処理）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメントを ai_scores テーブルへ書き込む（kabusys.ai.news_nlp.score_news）
  - マクロニュースを使った市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- 研究用ユーティリティ（ファクター計算 / 特徴量探索）
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic 等
- 監査ログ（signal → order_request → executions）スキーマ管理、初期化（kabusys.data.audit）
- J-Quants クライアント（レート制御 / トークンリフレッシュ / 保存ユーティリティ）

## 要求環境
- Python 3.10+
- 主な依存パッケージ（プロジェクトに合わせて requirements を用意してください）
  - duckdb
  - openai
  - defusedxml
  - （その他：logging 標準、urllib 等は標準ライブラリ）

## セットアップ手順

1. リポジトリをクローンして開発環境に入る
   - 例:
     - git clone <repo-url>
     - cd <repo>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードは無効）。
   - 主要な環境変数（最低限必要なもの）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - OPENAI_API_KEY=...  （news_nlp / regime_detector を使う場合）
     - DUCKDB_PATH=data/kabusys.duckdb  （任意）
     - SQLITE_PATH=data/monitoring.db    （任意）
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...
   - .env のサンプル例（.env.example を参照して作成してください）

5. 初期 DB 作成（監査ログ等のテーブル準備）
   - 監査ログ専用 DB を初期化する例:
     - from kabusys.config import settings
       from kabusys.data.audit import init_audit_db
       conn = init_audit_db(settings.duckdb_path)
   - 既存の DuckDB 接続に監査スキーマを追加する場合は init_audit_schema を利用できます。

## 使い方（簡易サンプル）

以下は Python REPL やスクリプトでの呼び出し例です。

- 設定の取得
  - from kabusys.config import settings
  - print(settings.duckdb_path, settings.env)

- DuckDB 接続を作成
  - import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行（全体）
  - from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn)  # target_date を明示することもできます
    print(result.to_dict())

- ニュース NLP（OpenAI）で銘柄ごとのスコア計算
  - from kabusys.ai.news_nlp import score_news
    from datetime import date
    n_written = score_news(conn, date(2026, 3, 20))  # target_date を指定
    print("written:", n_written)

- 市場レジーム判定（MA200 + マクロニュース）
  - from kabusys.ai.regime_detector import score_regime
    from datetime import date
    score_regime(conn, date(2026, 3, 20))  # OpenAI API キーは環境変数で指定可能

- 監査ログ DB の初期化（別 DB に分けたい場合）
  - from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")

- 研究用ファクター計算例
  - from kabusys.research.factor_research import calc_momentum
    recs = calc_momentum(conn, date(2026, 3, 20))
    # zscore 正規化
    from kabusys.data.stats import zscore_normalize
    recs_norm = zscore_normalize(recs, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])

注意点
- OpenAI を使う処理は API キー（OPENAI_API_KEY）の設定が必要です。設定がないと ValueError が発生します。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して読み込みます。テスト時に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB 書き込みは多くの関数で BEGIN / COMMIT を使い冪等性・ロールバックに配慮しています。

## ディレクトリ構成（主要ファイル）
以下はリポジトリの主要モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュースセンチメント（OpenAI）/ score_news
    - regime_detector.py               — マクロ + MA200 によるレジーム判定 / score_regime
  - data/
    - __init__.py
    - calendar_management.py           — マーケットカレンダー管理（is_trading_day 等）
    - etl.py / pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - stats.py                         — 共通統計ユーティリティ（zscore_normalize）
    - quality.py                       — データ品質チェック
    - audit.py                         — 監査ログスキーマ初期化 / init_audit_db
    - jquants_client.py                — J-Quants API クライアント（取得・保存関数）
    - news_collector.py                — RSS 収集と前処理
    - (その他 ETL 補助モジュール)
  - research/
    - __init__.py
    - factor_research.py               — Momentum/Value/Volatility 等の計算
    - feature_exploration.py           — 将来リターン計算、IC、統計サマリー

（上記は実装済みの主要機能の一覧です。詳細はコードコメントを参照してください。）

## 設定関連（主な環境変数）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu API 用パスワード（必須）
- KABU_API_BASE_URL — kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
- OPENAI_API_KEY — OpenAI 呼び出しに必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL

## 運用上の注意 / ベストプラクティス
- 本ライブラリの ETL やニュース NLP は外部 API（J-Quants / OpenAI）に依存します。API レートや課金に注意してスケジュールしてください。
- 本番（live）環境では KABUSYS_ENV を `live` に設定し、発注関連の機能を取り扱う際の安全策（シミュレーション / 二重チェック）を必ず導入してください。
- DuckDB のスキーマ初期化・マイグレーションは呼び出し元で管理してください（audit.init_audit_db は監査スキーマを作成します）。

---

詳細な API 仕様や内部設計は各モジュールのコードコメント（docstring）を参照してください。必要であれば README を拡張して、よくある運用手順（cron の例、監視・アラート設定、バージョンアップ手順など）を追加します。