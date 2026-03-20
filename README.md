# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）  
このリポジトリは、データ収集（J‑Quants）→ ETL → 特徴量生成 → シグナル生成 → 発注／監査までを想定したモジュール群を提供します。研究（research）と本番（execution）を分離し、DuckDB を中心に冪等性・トレーサビリティ・Look‑ahead バイアス対策を考慮して設計されています。

注意：この README はソースコードから生成した実装上の仕様要点をまとめたドキュメントです。実運用前に十分なテストと設定確認を行ってください。

---

## 概要

主な目的
- J‑Quants API からの株価・財務・カレンダー取得（差分取得・ページネーション対応・リトライ/レート制御）
- DuckDB によるデータストレージ（Raw / Processed / Feature / Execution 層）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 戦略用特徴量正規化（Z スコア）とシグナル生成（BUY/SELL）
- RSS ベースのニュース収集と銘柄紐付け
- カレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（signal → order → execution のトレース）

設計方針の要点
- 冪等（INSERT ... ON CONFLICT / RETURNING 等）を重視
- ルックアヘッドバイアス回避（対象日時点のデータのみ使用、fetched_at 記録）
- 外部依存は最小限（DuckDB / defusedxml 等を使用）
- ETL は差分更新（最終日＋バックフィル）で効率運用

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_* 等）
- Data（kabusys.data）
  - jquants_client: J‑Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
  - schema: DuckDB スキーマ定義と初期化（Raw, Processed, Feature, Execution 層）
  - pipeline: 日次 ETL（prices / financials / calendar）と品質チェック連携
  - news_collector: RSS 収集・前処理・DB 保存・銘柄抽出（SSRF 対策、gzip/サイズ制限）
  - calendar_management: market_calendar 管理、営業日計算ユーティリティ
  - stats: Z スコア正規化などの統計ユーティリティ
  - audit: 発注〜約定の監査ログスキーマ
- Research（kabusys.research）
  - factor_research: Momentum / Value / Volatility / Liquidity 等の計算
  - feature_exploration: 将来リターン計算・IC（Spearman）・統計サマリ等
- Strategy（kabusys.strategy）
  - feature_engineering.build_features: research の raw factor を統合・フィルタ・正規化して features テーブルへ保存
  - signal_generator.generate_signals: features + ai_scores を統合して final_score を算出し BUY/SELL シグナルを signals テーブルへ保存
- Execution（kabusys.execution）
  - 発注／注文管理のインターフェース（パッケージ化済み。実実装は発展に依存）
- Monitoring（kabusys.monitoring）
  - 監視用 DB/Slack 連携等（コード参照）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 環境作成（推奨: venv）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - 必須（ソースで参照されている主なパッケージ）
     - duckdb
     - defusedxml
   - サンプルインストールコマンド:
     - pip install duckdb defusedxml
   - （パッケージ化されている場合は）pip install -e . または pip install -r requirements.txt

4. 環境変数設定
   - プロジェクトルートに `.env`（およびローカル上書き用 `.env.local`）を用意できます。
   - 必須例（.env）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
   - 任意:
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1  # 自動 .env 読み込みを無効化する場合
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
   - 注意: config.Settings は環境変数が未設定だと ValueError を投げます（必須項目を確認してください）。

5. DuckDB スキーマ初期化
   - Python で実行例:
     - python -c "from kabusys.config import settings; from kabusys.data.schema import init_schema; init_schema(settings.duckdb_path)"
   - これにより DuckDB ファイルとテーブル群が作成されます（:memory: も使用可能）。

---

## 使い方（主要ユースケース例）

以下は最小限の Python スニペット例です。実運用ではロギングやエラーハンドリングを適切に追加してください。

- DuckDB 初期化（先述）
  - from kabusys.config import settings
    from kabusys.data.schema import init_schema
    conn = init_schema(settings.duckdb_path)

- 日次 ETL 実行
  - from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_daily_etl
    conn = init_schema(settings.duckdb_path)
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- 特徴量構築（build_features）
  - from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.strategy import build_features
    conn = duckdb.connect(settings.duckdb_path)
    n = build_features(conn, target_date=date(2025,1,1))
    print("upserted features:", n)

- シグナル生成（generate_signals）
  - from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.strategy import generate_signals
    conn = duckdb.connect(settings.duckdb_path)
    total = generate_signals(conn, target_date=date.today(), threshold=0.6)
    print("signals generated:", total)

- ニュース収集ジョブ
  - from kabusys.data.news_collector import run_news_collection
    conn = duckdb.connect(settings.duckdb_path)
    known_codes = {"7203","6758", ...}  # 既知の銘柄コードセット
    results = run_news_collection(conn, known_codes=known_codes)
    print(results)

- カレンダー更新ジョブ
  - from kabusys.data.calendar_management import calendar_update_job
    conn = duckdb.connect(settings.duckdb_path)
    saved = calendar_update_job(conn)
    print("calendar saved:", saved)

- J‑Quants から手動でデータ取得して保存
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
    conn = duckdb.connect(settings.duckdb_path)
    records = fetch_daily_quotes(date_from=..., date_to=...)
    saved = save_daily_quotes(conn, records)

注意点
- generate_signals / build_features は DuckDB 内の特定テーブル（prices_daily, raw_financials, features, ai_scores, positions 等）を前提に動作します。ETL → 前処理 → feature 作成 の順で準備してください。
- .env 自動読み込み: パッケージはプロジェクトルート（.git もしくは pyproject.toml を基準）から .env/.env.local を読み込みます。自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主なファイルと簡単な説明です。

- kabusys/
  - __init__.py  (パッケージ公開, __version__)
  - config.py    (環境変数と Settings クラス、自動 .env ロード)
  - execution/
    - __init__.py (execution 層パッケージ)
  - strategy/
    - __init__.py (build_features, generate_signals を公開)
    - feature_engineering.py  (research の raw factor を統合→features テーブルへ)
    - signal_generator.py     (features + ai_scores → final_score → signals テーブル)
  - research/
    - __init__.py
    - factor_research.py      (mom, value, volatility, liquidity の計算)
    - feature_exploration.py  (将来リターン、IC、統計サマリ)
  - data/
    - __init__.py
    - jquants_client.py       (J‑Quants API クライアント、fetch/save ユーティリティ)
    - news_collector.py       (RSS 収集、前処理、保存、銘柄抽出)
    - schema.py               (DuckDB スキーマ定義と init_schema)
    - stats.py                (zscore_normalize 等の統計ユーティリティ)
    - pipeline.py             (ETL パイプライン: run_daily_etl 等)
    - calendar_management.py  (market_calendar 管理、営業日ユーティリティ)
    - features.py             (data.stats の再エクスポート)
    - audit.py                (監査ログスキーマ)
  - monitoring/               (監視・通知関連: Slack 等の連携実装想定)

ソース内ドキュメント（各モジュールの docstring）にアーキテクチャ設計意図や参照すべき仕様（例: StrategyModel.md, DataPlatform.md, DataSchema.md）への言及があります。実運用前に対応する設計ドキュメントを確認してください。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J‑Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意, デフォルト: development) — 有効値: development, paper_trading, live
- LOG_LEVEL (任意, デフォルト: INFO) — DEBUG|INFO|WARNING|ERROR|CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意) — 自動 .env 読み込みを無効化（値は任意、存在すれば無効）

---

## 開発／運用上の注意事項

- DuckDB のバージョンによっては外部キーや一部機能の扱いが異なる場合があります（コード内にも注意書きがあります）。使用する DuckDB バージョンを合わせてください。
- ネットワーク I/O（RSS / J‑Quants）にはリトライ・サイズ制限・SSRF 対策などを実装していますが、実運用ではネットワークや API 仕様変更に注意してください。
- AI スコアやニューススコア等を組み込む際は、データのタイムスタンプ（fetched_at / date）を適切に使い、ルックアヘッドを生まないようにしてください。
- 本コードは発注（実際の送信）や証券会社レスポンスとの統合については汎用的な監査スキーマを提供しますが、ブローカー固有の実装は別途必要です。

---

フィードバックやドキュメント改善ポイントがあれば教えてください。README の利用シナリオに合わせてサンプルスクリプトや CI/デプロイ手順を追加できます。