# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム用ライブラリです。データ収集（J‑Quants など）、ETL、特徴量エンジニアリング、シグナル生成、ニュース収集、データベーススキーマ／監査ログなど、戦略の研究〜運用までを支えるコンポーネント群を提供します。

---

## 主な特徴（機能一覧）

- データ取得
  - J‑Quants API クライアント（株価日足・財務・市場カレンダー）
  - RSS ベースのニュース収集（URL 正規化、SSRF 対策、gzip 制限）
- ETL / データ管理
  - 差分取得 / バックフィル可能な日次 ETL（run_daily_etl）
  - DuckDB ベースのスキーマ定義と初期化（init_schema）
  - 市場カレンダー管理（営業日判定・次/前営業日取得等）
  - 品質チェック連携（quality モジュールを呼び出す、別途実装想定）
- 研究（Research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Spearman）や統計サマリー
  - Z スコア正規化ユーティリティ
- 戦略（Strategy）
  - 特徴量生成（build_features）：research で得た生ファクターを正規化／フィルタ適用して features テーブルへ保存
  - シグナル生成（generate_signals）：features と ai_scores を統合して BUY/SELL シグナルを生成・保存
- 発注・監査（Execution / Audit）
  - 実行層のテーブル定義（signals / signal_queue / orders / trades / positions 等）
  - 監査ログ（signal_events / order_requests / executions）によるトレーサビリティ設計
- 汎用ユーティリティ
  - 統計関数（zscore_normalize 等）
  - 環境変数管理（.env 自動読み込み、必須項目チェック）

---

## セットアップ手順

前提: Python 3.10+（typing の一部表記に合わせることを推奨）、ネットワークアクセス（J‑Quants 等）。

1. リポジトリをクローン／チェックアウト
   - 例: git clone ...

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存ライブラリのインストール（最低限）
   - pip install duckdb defusedxml
   - プロジェクトに requirements.txt があれば: pip install -r requirements.txt
   - パッケージを editable インストール:
     - pip install -e .

4. 環境変数設定 (.env)
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可能）。
   - 必須環境変数（config.Settings 参照）:
     - JQUANTS_REFRESH_TOKEN — J‑Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用 bot トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
   - 任意／デフォルト:
     - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると自動で .env を読み込みません
     - KABUSYS_ENABLE...（その他プロジェクト独自のフラグは追加可能）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

   - サンプル .env（プロジェクトルート/.env.example）
     - JQUANTS_REFRESH_TOKEN=your_refresh_token
     - KABU_API_PASSWORD=your_kabu_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - KABUSYS_ENV=development
     - LOG_LEVEL=INFO

5. データベース初期化（DuckDB）
   - Python REPL またはスクリプトから:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
   - ":memory:" を指定するとインメモリ DB を使用できます（テスト用途）。

---

## 基本的な使い方（コード例）

- DuckDB の初期化（1回だけ実行）

  - Python スクリプト例:
    - from kabusys.data.schema import init_schema
    - conn = init_schema("data/kabusys.duckdb")

- 日次 ETL（市場カレンダー / 株価 / 財務 の差分取得 + 品質チェック）

  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # target_date を省略すると今日（必要に応じて調整される）
  - print(result.to_dict())

- 特徴量の構築（research のファクターを正規化して features テーブルへ保存）

  - from kabusys.strategy import build_features
  - from datetime import date
  - n = build_features(conn, date(2025, 1, 31))
  - print(f"upserted features: {n}")

- シグナル生成（features と ai_scores を統合して signals テーブルへ保存）

  - from kabusys.strategy import generate_signals
  - from datetime import date
  - total_signals = generate_signals(conn, date(2025, 1, 31))
  - print(f"generated signals: {total_signals}")

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）

  - from kabusys.data.news_collector import run_news_collection
  - results = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
  - print(results)

- J‑Quants の生データ取得（低レベル API）

  - from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  - token = get_id_token()  # settings.jquants_refresh_token を参照
  - rows = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

注意: 例は同期 API を想定。実運用ではエラーハンドリング・リトライの制御・ログ管理が必要です。

---

## 主要モジュール / ディレクトリ構成

（リポジトリ内の src/kabusys 配下。抜粋）

- kabusys/
  - __init__.py  — パッケージ定義（__version__ 等）
  - config.py    — 環境変数 / 設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py       — J‑Quants API クライアント（取得＋保存）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - schema.py              — DuckDB スキーマ定義 & init_schema
    - news_collector.py      — RSS 取得・前処理・DB 保存・銘柄抽出
    - calendar_management.py — 市場カレンダー更新・営業日判定ユーティリティ
    - features.py            — zscore_normalize の公開ラッパ
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログ用スキーマ DDL（signal_events 等）
    - quality.py (想定)      — 品質チェック（pipeline から呼ばれる想定）
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Volatility / Value の計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — build_features (features テーブル生成)
    - signal_generator.py    — generate_signals (signals テーブル生成)
  - execution/
    - __init__.py            — 発注・実行層（テーブル定義は schema.py / audit.py に含む）
  - monitoring/ (参照用: __all__ にあるが実装は省略されている場合あり)
  - その他: docs/*.md（設計ドキュメント参照: StrategyModel.md / DataPlatform.md / DataSchema.md 等）

---

## 注意点 / 実運用メモ

- 環境変数の自動ロード:
  - config モジュールはプロジェクトルート（.git または pyproject.toml を探索）から .env/.env.local を自動で読み込みます。テストで無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- トークン・認証:
  - J‑Quants の id_token は自動リフレッシュを実装しています（401 受信時にリフレッシュして再試行）。
- レート制限:
  - jquants_client には固定間隔（120 req/min）での rate limiter と指数バックオフ付きのリトライが組み込まれています。
- 冪等性:
  - 生データ保存（raw_*）や一部保存処理は ON CONFLICT/DO UPDATE または DO NOTHING で冪等性を確保しています。
- Look‑ahead バイアス対策:
  - 特徴量・シグナル生成は target_date 時点で「既知の」データのみを使用する設計です（fetched_at や target_date の扱いに配慮）。
- セキュリティ:
  - ニュース収集（RSS）では SSRF 対策、gzip サイズ制限、XML パースの防護（defusedxml）などの対策を実装しています。

---

## 開発者向け補足

- ログレベルは環境変数 LOG_LEVEL で制御できます（config.Settings.log_level）。
- DuckDB のスキーマ変更は schema.py の DDL を編集し、init_schema を再実行してください。既存テーブルはスキップされるため安全に呼べますが、DDL の互換性に注意してください。
- strategy / research の関数は DuckDB 接続を受け取り SQL を直接実行します。テストでは in‑memory DB (":memory:") を使うと便利です。

---

この README はコードベースの主要機能と典型的な使い方を簡潔にまとめたものです。詳細な設計仕様や運用ルール（StrategyModel.md / DataPlatform.md / DataSchema.md）がプロジェクト内に用意されていればそちらを参照してください。質問や追加したいセクション（例: CI/CD、デプロイ手順、監視設定など）があれば教えてください。