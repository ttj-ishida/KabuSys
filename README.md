# KabuSys

日本株向けの自動売買システム用ライブラリ（パイプライン・研究・戦略・監査ログ基盤）

概要
- KabuSys は日本株のデータ取得・ETL、特徴量生成、戦略シグナル生成、ニュース収集、監査ログなどを含む内部ライブラリ群です。
- DuckDB をデータストアとして利用し、J-Quants API から市場データ／財務データ／カレンダーを取得します。
- 研究（research）・データ（data）・戦略（strategy）・発注/監査（execution/audit）の階層を分離した設計になっています。

主な機能
- データ取得・保存
  - J-Quants API クライアント（jquants_client）: 日足・財務・市場カレンダーのページネーション取得、トークン自動更新、リトライ・レート制限。
  - Raw → Processed → Feature レイヤーを想定した DuckDB スキーマ定義と初期化（init_schema）。
  - 差分ETL パイプライン（data.pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）。
- ニュース収集
  - RSS フィードから記事収集・前処理・重複排除・記事 → 銘柄紐付け（news_collector）。
  - SSRF・XML攻撃・巨大レスポンス対策、トラッキングパラメータ除去、記事IDは正規化URLのSHA-256先頭32文字。
- 研究・特徴量
  - ファクター計算（research.factor_research: momentum / volatility / value）。
  - 将来リターン計算・IC（Spearman）・ファクターサマリ（research.feature_exploration）。
  - 共通統計ユーティリティ（data.stats: zscore_normalize）。
- 戦略
  - 特徴量構築（strategy.feature_engineering.build_features）: research で算出した生ファクターを正規化・合成して features テーブルへ保存。
  - シグナル生成（strategy.signal_generator.generate_signals）: features と ai_scores を統合して BUY/SELL シグナルを作成、signals テーブルへ保存。Bear レジーム判定、エグジット判定（ストップロス等）対応。
- 監査 / 実行
  - DuckDB 上に監査用テーブル群（signal_events / order_requests / executions ...）を定義するモジュール（data.audit）。
  - Execution 層のスキーマ（schema.py）により、orders/trades/positions/portfolio 関連を管理。
- カレンダー管理
  - JPX カレンダーの夜間差分更新 / 営業日判定 / 前後営業日探索（data.calendar_management）。

動作環境と依存
- Python 3.10 以降（型ヒントで PEP 604 の表記（|）を利用しているため）
- 必要な Python パッケージ（例）
  - duckdb
  - defusedxml
- これらはプロジェクトの pyproject.toml / requirements.txt によってインストールしてください。最小例:
  - pip install duckdb defusedxml

セットアップ手順（開発用）
1. リポジトリをクローン／チェックアウト
2. 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存をインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （任意）pip install -e . など（pyproject.toml があれば）
4. DuckDB スキーマ初期化（例）
   - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   - デフォルトのデータベースパスは環境変数 DUCKDB_PATH で変更可能（デフォルト: data/kabusys.duckdb）

重要な環境変数
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン（Slack 統合がある場合）
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネルID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化

例: .env（プロジェクトルートに置く）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

使い方（代表的な API）
- DuckDB スキーマ初期化
  - from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")

- ETL を実行（日次）
  - from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn)
    print(result.to_dict())

- 特徴量構築（戦略レイヤー）
  - from kabusys.strategy import build_features
    from datetime import date
    cnt = build_features(conn, date(2024, 1, 1))
    print(f"built features: {cnt}")

- シグナル生成
  - from kabusys.strategy import generate_signals
    from datetime import date
    total = generate_signals(conn, date(2024, 1, 1))
    print(f"signals generated: {total}")

- ニュース収集ジョブ
  - from kabusys.data.news_collector import run_news_collection
    results = run_news_collection(conn, known_codes={'7203','6758'})  # known_codes を渡すと銘柄紐付けを行う
    print(results)

- JPX カレンダー更新（夜間ジョブ）
  - from kabusys.data.calendar_management import calendar_update_job
    saved = calendar_update_job(conn)
    print(f"calendar saved: {saved}")

設計上の注意 / ポイント
- ルックアヘッドバイアス対策:
  - 各処理は target_date 時点で利用可能なデータのみを参照するよう設計されています（fetched_at 等でトレーサビリティを担保）。
- 冪等性:
  - DB への保存は基本的に ON CONFLICT / INSERT ... DO UPDATE / DO NOTHING を用いて重複を防ぎます。ETL や特徴量構築・シグナル挿入は日付単位で置換（DELETE + INSERT）することで冪等性を確保しています。
- レート制御・リトライ:
  - J-Quants クライアントは固定間隔スロットリング（120 req/min）と指数バックオフリトライを備え、401 時にはトークン自動更新を試みます。
- セキュリティ:
  - RSS 収集では SSRF 検出、private IP ブロック、XML インジェクション防止（defusedxml）、受信サイズ制限などの防御策を実装しています。

ディレクトリ構成（主要ファイル・モジュール）
- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py          — RSS 収集・記事保存・銘柄抽出
    - schema.py                  — DuckDB スキーマ定義と init_schema
    - stats.py                   — 統計ユーティリティ（zscore_normalize）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py     — カレンダー更新・営業日ロジック
    - audit.py                   — 監査ログ用スキーマ
    - features.py                — data.stats の再エクスポート
  - research/
    - __init__.py
    - factor_research.py         — momentum / volatility / value の計算
    - feature_exploration.py     — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py     — features テーブル作成
    - signal_generator.py        — signals の作成ロジック
  - execution/                   — 実行/ブローカー連携（将来的な拡張）
  - monitoring/                  — 監視・メトリクス（将来的な拡張）

開発・拡張のヒント
- DuckDB をインメモリで使う場合は db_path を ":memory:" に指定して init_schema を呼ぶことでテストが容易になります。
- news_collector.fetch_rss や jquants_client._request のような I/O 部分はモック可能に設計されているため、ユニットテストで置き換えて検証できます。
- settings（kabusys.config.settings）を直接参照して運用環境に応じた分岐（is_live / is_paper / is_dev）を行えます。
- strategy の重み（generate_signals の weights）や閾値は引数で上書き可能です。

ライセンス・貢献
- 本リポジトリ内の LICENSE / CONTRIBUTING ファイル（存在する場合）を参照してください。初期セットアップや外部 API の利用には各サービスの利用規約に従ってください。

その他
- 追加のセットアップ（CI / デプロイ / コンテナ化 / 実際の発注連携）は運用要件により必要です。kabuステーション（証券会社）や Slack の実運用統合は安全面（秘密情報の管理、テスト用口座）を十分考慮してください。

ご要望があれば、README にサンプル .env.example、Dockerfile、簡易デプロイ手順、または具体的な使い方（スクリプト化例）を追記します。