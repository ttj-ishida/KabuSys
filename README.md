# KabuSys

日本株の自動売買システム（ライブラリ／研究・ETL・バックテスト基盤）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象にしたデータ収集、特徴量作成、シグナル生成、バックテストを行うためのモジュール群です。  
主な用途は次のとおりです。

- J-Quants API からの株価・財務データ取得と DuckDB への保存（差分更新・冪等保存）
- RSS ベースのニュース収集と記事 → 銘柄紐付け
- 研究用ファクター計算（モメンタム／ボラティリティ／バリュー等）
- 特徴量の正規化・保存（features テーブル）
- シグナル生成（final_score に基づく BUY/SELL）
- バックテストフレームワーク（シミュレータ、メトリクス、CLI）
- DuckDB スキーマ定義・初期化ユーティリティ
- 設定管理（.env 自動読み込み・環境変数）

設計方針として「ルックアヘッドバイアスの排除」「DB 更新の冪等性」「外部 API 呼び出しのレート制御・リトライ」「テスト容易性」を重視しています。

---

## 機能一覧（モジュール別ハイライト）

- kabusys.config
  - 環境変数 / .env 自動読み込み
  - 必須設定の取得ユーティリティ（settings）

- kabusys.data
  - jquants_client: J-Quants API クライアント（認証・ページング・リトライ・レート制御）
  - news_collector: RSS 取得・正規化・DB 保存、銘柄コード抽出
  - schema: DuckDB スキーマ定義 / init_schema()
  - stats: zscore_normalize 等の統計ユーティリティ
  - pipeline: ETL（差分更新、品質チェック、保存処理）の実装

- kabusys.research
  - factor_research: モメンタム／ボラティリティ／バリュー計算
  - feature_exploration: 将来リターン、IC、統計サマリ

- kabusys.strategy
  - feature_engineering.build_features: 生ファクターの正規化・features テーブルへの保存
  - signal_generator.generate_signals: features・ai_scores を統合して シグナル（signals テーブル）を生成

- kabusys.backtest
  - engine.run_backtest: バックテストのメインループ（DB -> in-memory コピー、日次シミュレーション）
  - simulator.PortfolioSimulator: 約定ロジック（スリッページ・手数料考慮）と時価評価
  - metrics.calc_metrics: バックテスト評価指標（CAGR, Sharpe, MaxDD, WinRate）
  - 実行用 CLI: python -m kabusys.backtest.run

- kabusys.data.news_collector
  - RSS フェッチ（SSRF対策、gzip チェック、XML パース保護）
  - raw_news / news_symbols への冪等保存

その他、execution / monitoring 用のスケルトンが含まれています。

---

## 要件

- Python 3.10+
- 必要なパッケージ（最低限）
  - duckdb
  - defusedxml
- 標準ライブラリ（urllib 等）は使用

（プロジェクトで使用する他のライブラリがある場合は requirements.txt を参照してください）

インストール例:

    python -m venv .venv
    source .venv/bin/activate
    pip install duckdb defusedxml

もしパッケージとして使う場合:

    pip install -e .

---

## セットアップ手順

1. リポジトリをクローン／展開する

2. 仮想環境を作成して依存をインストール

3. 環境変数（.env）を用意する  
   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動ロード無効化可）。  
   最低限必要な環境変数例:

    JQUANTS_REFRESH_TOKEN=（J-Quants の refresh token）
    KABU_API_PASSWORD=（kabu API パスワード、必要な場合）
    SLACK_BOT_TOKEN=（通知用の Slack Bot Token）
    SLACK_CHANNEL_ID=（通知先 Slack チャネルID）
    DUCKDB_PATH=data/kabusys.duckdb  # 任意（デフォルト）
    SQLITE_PATH=data/monitoring.db    # 任意（デフォルト）
    KABUSYS_ENV=development|paper_trading|live
    LOG_LEVEL=INFO|DEBUG|...

   注意: settings が必要変数を参照するため、実行前に設定してください。

4. DuckDB スキーマ初期化

    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")
    conn.close()

   :memory: を指定すればインメモリ DB を作成できます。

---

## 使い方

以下に代表的なワークフローとサンプルコード/コマンドを示します。

1) データ取得（ETL）例（株価差分取得、財務、カレンダーなど）:

    from datetime import date
    import duckdb
    from kabusys.data.schema import init_schema, get_connection
    from kabusys.data.pipeline import run_prices_etl, run_news_collection

    conn = init_schema("data/kabusys.duckdb")
    target = date.today()
    # run_prices_etl 等は ETLResult を返す（詳細は pipeline モジュール参照）
    fetched, saved = run_prices_etl(conn, target_date=target)
    # ニュース収集
    known_codes = {"7203", "6758", "9984"}  # 事前に有効銘柄一覧を準備
    res = run_news_collection(conn, known_codes=known_codes)

2) 特徴量生成（feature engineering）:

    import duckdb
    from datetime import date
    from kabusys.strategy import build_features

    conn = duckdb.connect("data/kabusys.duckdb")
    n = build_features(conn, target_date=date(2024, 01, 15))
    print(f"features upserted: {n}")

3) シグナル生成:

    from kabusys.strategy import generate_signals
    generated = generate_signals(conn, target_date=date(2024, 1, 15), threshold=0.6)
    print(f"signals written: {generated}")

4) バックテスト（CLI）:

    python -m kabusys.backtest.run \
        --start 2023-01-01 --end 2024-12-31 \
        --cash 10000000 --db data/kabusys.duckdb

   あるいは Python API:

    from kabusys.backtest.engine import run_backtest
    from kabusys.data.schema import init_schema
    from datetime import date

    conn = init_schema("data/kabusys.duckdb")
    result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
    print(result.metrics)

5) 研究用ユーティリティ（IC 計算や将来リターン）:

    from kabusys.research import calc_forward_returns, calc_ic, factor_summary
    fwd = calc_forward_returns(conn, target_date=date(2024,1,15), horizons=[1,5,21])
    ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")

---

## 設定（環境変数）

主な環境変数（settings で参照）:

- JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUS_API_BASE_URL: kabu API のベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（モニタリング用）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動読み込みを無効にする（テスト用）

.env の自動読み込みは、プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` → `.env.local` の順で行われます。`.env.local` は OS 環境変数を上書きします。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - pipeline.py
  - schema.py
  - stats.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- strategy/
  - __init__.py
  - feature_engineering.py
  - signal_generator.py
- backtest/
  - __init__.py
  - engine.py
  - metrics.py
  - simulator.py
  - clock.py
  - run.py  (CLI)
- execution/ (空の __init__ や発注周りの実装領域)
- monitoring/ (監視関連の実装領域)

（README に含まれるものは上記抜粋です。実際のリポジトリで追加ファイルが存在する場合があります）

---

## 開発・貢献

- コードスタイル: ログ出力とエラーハンドリングを重視。トランザクション（DuckDB）では BEGIN/COMMIT/ROLLBACK を使用。
- テスト: 各外部依存（ネットワーク・API）はモック可能な設計（例: jquants_client の id_token 注入、news_collector._urlopen の差し替え）。
- 実運用時は KABUSYS_ENV を適切に設定し、live モードでの誤発注を防ぐ仕組みを組み合わせてください。

---

## 注意事項

- Python 3.10 以降を推奨（`X | Y` 形式の型注釈を使用）。
- J-Quants のレート制限（120 req/min）に従う実装が組み込まれていますが、運用時は API 利用上限を確認してください。
- DuckDB のバージョンや機能差異により外部キーや ON DELETE の挙動に制約があります（コード内に注釈あり）。
- 実際の発注・ライブ運用を行う場合は、十分な検証とリスク管理を必ず行ってください。

---

必要であれば、README に含める具体的な .env.example、requirements.txt、実行例の詳細（モジュール API レベルのサンプル）や API レート制御やログ出力設定のガイドを追加で作成します。どの部分を詳細化しましょうか？