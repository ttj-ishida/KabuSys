# KabuSys

日本株向けの自動売買プラットフォーム（ライブラリ）です。  
データ収集（J-Quants）→ ETL（DuckDB保存）→ 研究用ファクター算出 → 特徴量正規化 → シグナル生成 → 発注／監査の各レイヤーのユーティリティを提供します。

主な設計思想：
- ルックアヘッドバイアス防止（対象日時点のデータのみを使用）
- 冪等性（DB保存は ON CONFLICT / UPSERT ベース）
- DuckDB を中心としたローカルデータベース設計
- 外部 API 呼び出しにはレート制御 / リトライ / トークンリフレッシュなどの堅牢性を実装

---

## 機能一覧

- 環境変数・設定管理（kabusys.config）
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込み（無効化可能）
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN 等）

- データ収集（kabusys.data.jquants_client）
  - J-Quants API から日足・財務データ・マーケットカレンダーを取得
  - RateLimiter、指数バックオフ、401時のトークンリフレッシュを実装
  - DuckDB へ冪等保存（raw_prices / raw_financials / market_calendar など）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日ベースの差分更新・backfill）
  - 日次 ETL 実行（calendar → prices → financials → 品質チェック）
  - ETL 結果を ETLResult に集約

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス作成、接続ユーティリティ

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集、URL 正規化、SSRF / XML 攻撃対策、トラッキングパラメータ除去
  - raw_news / news_symbols への冪等保存および銘柄抽出

- 研究用ファクター計算（kabusys.research.*）
  - momentum / volatility / value 等のファクター計算
  - 将来リターン計算、IC（Spearman ρ）計算、ファクターサマリー

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - 研究で算出した raw factor を統合・正規化し `features` テーブルへ保存
  - ユニバースフィルタ（最低株価・最低売買代金）適用、Zスコア正規化、クリップ

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算
  - Bear レジーム抑制、BUY/SELL の判定、signals テーブルへの冪等書き込み
  - 売り（エグジット）判定ロジック（ストップロス等）

- 統計ユーティリティ（kabusys.data.stats）
  - クロスセクションZスコア正規化など共通関数

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions などの監査テーブル定義（トレーサビリティ）

---

## 前提条件 / 必要環境

- Python 3.10 以上（PEP 604 の型記法（|）を使用しているため）
- pip, virtualenv 等
- 主要依存（最低限）:
  - duckdb
  - defusedxml

（実行環境によって追加パッケージが必要になる場合があります。requirements.txt がある場合はそちらを利用してください。）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンする
   - git clone <リポジトリURL>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml
   - （パッケージとしてプロジェクトをインストールする場合）
     - pip install -e .

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を配置するか、OSの環境変数として設定します。自動ロードはデフォルトで有効。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数（アプリケーションで参照される主要なもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）

任意・デフォルト値あり:
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_ENV — (development | paper_trading | live)、デフォルト development
- LOG_LEVEL — DEBUG/INFO/…、デフォルト INFO

---

## 初期化（DuckDB スキーマ作成）

Python REPL またはスクリプトで DuckDB スキーマを初期化します。

例:
- Python コード例
  - from kabusys.data.schema import init_schema
  - from kabusys.config import settings
  - conn = init_schema(settings.duckdb_path)
  - # conn を使って以降の操作を実行

`init_schema` は指定したパスに親ディレクトリを自動作成し、必要なテーブル・インデックスをすべて作成します。":memory:" を渡すとインメモリ DB を使用します。

---

## 主要な使い方（サンプル）

以下は代表的な操作の呼び出し例です。実運用ではログ設定や例外処理、スケジュール（cron / Airflow等）を組み合わせて運用してください。

- 日次 ETL 実行（市場カレンダー・株価・財務の差分取得）
  - from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.config import settings
    conn = init_schema(settings.duckdb_path)
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- 特徴量構築（features テーブルへの書き込み）
  - from datetime import date
    from kabusys.data.schema import get_connection
    from kabusys.strategy import build_features
    from kabusys.config import settings
    conn = get_connection(settings.duckdb_path)
    count = build_features(conn, target_date=date(2025, 1, 31))
    print(f"features upserted: {count}")

- シグナル生成
  - from datetime import date
    from kabusys.data.schema import get_connection
    from kabusys.strategy import generate_signals
    from kabusys.config import settings
    conn = get_connection(settings.duckdb_path)
    total = generate_signals(conn, target_date=date(2025, 1, 31))
    print(f"signals written: {total}")

- ニュース収集と銘柄紐付け
  - from kabusys.data.news_collector import run_news_collection
    from kabusys.data.schema import get_connection
    conn = get_connection(settings.duckdb_path)
    known_codes = {"7203", "6758", ...}  # 既知の銘柄コードセット
    results = run_news_collection(conn, known_codes=known_codes)
    print(results)

- カレンダー更新ジョブ（夜間バッチ）
  - from kabusys.data.calendar_management import calendar_update_job
    conn = get_connection(settings.duckdb_path)
    saved = calendar_update_job(conn)
    print(f"saved calendar rows: {saved}")

- J-Quants からの直接フェッチ（デバッグ等）
  - from kabusys.data import jquants_client as jq
    records = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,31))
    # 保存は jq.save_daily_quotes(conn, records)

---

## APIのエントリポイント（主な公開関数）

- kabusys.config.settings — 環境設定プロパティ（jquants_refresh_token, duckdb_path 等）
- kabusys.data.schema.init_schema(db_path) / get_connection(db_path)
- kabusys.data.pipeline.run_daily_etl(conn, target_date, ...)
- kabusys.strategy.build_features(conn, target_date)
- kabusys.strategy.generate_signals(conn, target_date, threshold, weights)
- kabusys.data.news_collector.run_news_collection(conn, sources, known_codes)
- kabusys.data.calendar_management.calendar_update_job(conn, lookahead_days)

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要モジュールの構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + 保存関数
    - schema.py                     — DuckDB スキーマ定義・初期化
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - news_collector.py             — RSS フィード収集・保存
    - calendar_management.py        — 市場カレンダー管理
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - features.py                   — features インターフェース（再エクスポート）
    - audit.py                      — 監査ログ用スキーマ
    - quality.py (別途実装想定)    — 品質チェック（pipeline で利用）
  - research/
    - __init__.py
    - factor_research.py            — momentum/volatility/value 等
    - feature_exploration.py        — IC / forward returns / summary
  - strategy/
    - __init__.py
    - feature_engineering.py        — features の構築
    - signal_generator.py           — final_score 計算と signals 書き込み
  - execution/                       — 発注・ブローカー連携層（空フォルダ / 実装次第）
  - monitoring/                      — 監視／メトリクス（存在する場合）

（実際のツリーはパッケージのバージョンや追加モジュールにより変化します）

---

## 運用上の注意 / ベストプラクティス

- secrets（API トークン等）は `.env` や環境変数で管理し、リポジトリに含めないこと。
- DuckDB ファイルは定期的にバックアップしてください（ローカルファイル破損対策）。
- ETL はスケジューラ（cron / systemd timer / Airflow 等）で定期実行することを想定しています。
- 本リポジトリは戦略ロジック・発注ロジックの雛形を提供します。実運用に使う場合は追加のリスク管理（資金管理、注文サイズ制限、接続リトライ方針、テスト）を必ず実装してください。
- 本番環境での「live」モードは KABUSYS_ENV=live を設定して有効にしてください（コード内でライブ判定に使用）。

---

## ライセンス / 貢献

（ライセンス情報や貢献ガイドがある場合はここに追記してください）

---

ご不明点や README に追記して欲しいセクション（例: サンプル .env.example、運用チェックリスト、CI設定例）があれば教えてください。必要に応じて README を拡張します。