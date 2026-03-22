# KabuSys

日本株向けの自動売買システム基盤（ライブラリ / ツール群）。

目的：
- J-Quants 等のデータソースから市場データ・財務データ・ニュースを取得して DuckDB に保存
- 研究用ファクター（momentum / volatility / value 等）を計算して特徴量を作成
- 正規化済み特徴量 + AI スコアを用いて売買シグナルを生成
- バックテスト用フレームワークで戦略を検証
- ニュース収集・紐付け、ETL パイプライン、実取引（kabuステーション）統合の基盤を提供

※ このリポジトリはモジュール群の実装例（設計ドキュメント参照の前提）です。

---

## 主な機能（抜粋）

- data/
  - J-Quants API クライアント（認証リフレッシュ・レート制御・リトライ）
  - RSS ベースのニュース収集（SSRF対策・トラッキング除去・記事ID生成）
  - DuckDB スキーマ初期化（init_schema）と冪等的保存関数
  - ETL パイプライン（差分取得・バックフィル）
  - 汎用統計ユーティリティ（Zスコア正規化 等）
- research/
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（将来リターン計算、IC、統計サマリー）
- strategy/
  - 特徴量生成（build_features: raw factor → normalized features）
  - シグナル生成（generate_signals: features＋AIスコア → BUY/SELL シグナル）
  - Bear レジーム抑止、重み/閾値の取り扱い、エグジット判定（ストップロス等）
- backtest/
  - ポートフォリオシミュレータ（スリッページ・手数料モデル）
  - バックテストエンジン（run_backtest）
  - バックテストメトリクス（CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- execution/
  - 発注/モニタリング関連のスコープ（発注実装は階層として分離）

---

## 要件

- Python 3.10 以上（型記法に `X | None` を使用）
- 必要な Python パッケージ（主なもの）
  - duckdb
  - defusedxml

（実行環境に応じて追加パッケージが必要になる場合があります）

---

## 環境変数 / 設定

このパッケージは .env / OS 環境変数から設定を読み取ります（kabusys.config.Settings）。

自動読み込み:
- プロジェクトルート（.git または pyproject.toml）を探し、`.env` → `.env.local` の順に読み込みます。
- OS 環境変数が優先され、`.env.local` は `.env` を上書きします。
- 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（必須は README 内で明示）:

- J-Quants
  - JQUANTS_REFRESH_TOKEN (必須)
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- Slack 通知
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- DB パス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
- システム
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト INFO

例（.env の簡易テンプレート）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（ローカル）

1. リポジトリをクローンする
   - git clone <repository-url>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install "duckdb" "defusedxml"
   - （必要に応じて開発用に poetry/requirements.txt を用意してください）

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、OS環境変数を設定してください。
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトから:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
   - またはバックテスト実行時に init_schema を呼び出すことも可能です。

---

## 使い方（代表的な操作例）

- DuckDB スキーマ初期化
  - Python:
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")
    conn.close()

- J-Quants から株価を差分取得して保存（ETL の一部）
  - pipeline.run_prices_etl を利用（例）:
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_prices_etl
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")
    fetched, saved = run_prices_etl(conn, target_date=date.today())
    conn.close()

- ニュース収集
  - run_news_collection を呼び出して RSS を取得して保存:
    from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")
    known_codes = {"7203", "6758", ...}  # 既知銘柄コードセット（任意）
    results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
    conn.close()

- 特徴量構築（features テーブルへ書き込み）
  - build_features(conn, target_date)
    from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.strategy import build_features
    conn = init_schema("data/kabusys.duckdb")
    n = build_features(conn, date.today())
    conn.close()

- シグナル生成（signals テーブルへ書き込み）
  - generate_signals(conn, target_date, threshold=0.6, weights=None)
    from kabusys.strategy import generate_signals
    generate_signals(conn, target_date=date.today())

- バックテスト（CLI）
  - コマンド例:
    python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2023-12-31 \
      --cash 10000000 --db data/kabusys.duckdb
  - 主要オプション:
    --start / --end: 開始/終了日 (YYYY-MM-DD)
    --cash: 初期資金
    --slippage: スリッページ率（例 0.001）
    --commission: 手数料率（例 0.00055）
    --max-position-pct: 1銘柄あたりの最大保有比率（例 0.20）
    --db: DuckDB ファイルパス

- バックテストを Python から呼ぶ例:
    from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.backtest.engine import run_backtest
    conn = init_schema("data/kabusys.duckdb")
    result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
    conn.close()
    print(result.metrics)

---

## 注意点 / 設計上のポイント

- ルックアヘッドバイアス対策:
  - ファクター・シグナル生成・バックテストは target_date 時点のデータのみ参照するように設計されています。
  - J-Quants の取得時は fetched_at を記録し「いつそのデータが利用可能になったか」を追跡可能にしています。

- 冪等性:
  - API 保存関数は ON CONFLICT 等を用いて冪等にデータを保存します（raw -> processed 層の差分更新を想定）。

- エラーハンドリング:
  - ネットワークリトライ（指数バックオフ）、401 の自動リフレッシュ、RSS の SSRF/サイズ制限等の安全策を備えています。

- テスト容易性:
  - _urlopen 等はモック可能に設計されています（テスト用の差し替え）。

---

## ディレクトリ構成（主要ファイルと簡単な説明）

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py — RSS ニュース取得 / 正規化 / DB 保存
    - schema.py — DuckDB スキーマ定義と init_schema()
    - pipeline.py — ETL パイプライン（差分更新等）
    - stats.py — Z スコア正規化等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — momentum/volatility/value 等のファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー等（研究用）
  - strategy/
    - __init__.py
    - feature_engineering.py — raw ファクターから features テーブルを作成
    - signal_generator.py — features/ai_scores を統合して売買シグナル生成
  - backtest/
    - __init__.py
    - engine.py — バックテストループ / run_backtest
    - simulator.py — ポートフォリオシミュレータ（約定・評価）
    - metrics.py — バックテスト評価指標計算
    - run.py — CLI エントリポイント
    - clock.py — 将来拡張用の模擬時計
  - execution/
    - __init__.py — 発注・モニタリング関連の置き場（将来的実装）

---

## よくある質問（FAQ）

- Q: DB の初回ロード用データは何を使えばよいですか？
  - A: J-Quants からの株価データと財務データ（fetch_daily_quotes / fetch_financial_statements）を差分取得して raw_prices / raw_financials に保存してください。market_calendar も重要です。

- Q: 自動売買で実際に発注を出せますか？
  - A: execution レイヤーの実装次第です。kabuステーション API の連携部分（認証・発注）は別途実装が必要です。config には KABU_API_PASSWORD / KABU_API_BASE_URL の設定があります。

- Q: テスト用に API 呼び出しを行いたくない場合は？
  - A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして .env の自動読み込みを無効化したり、jquants_client のネットワーク呼び出し部分をモックしてください。バックテスト用には init_schema(":memory:") を使えます。

---

## 貢献・拡張

- 新しいファクターやシグナルロジックの追加は research/ または strategy/ に実装し、features テーブルや signals テーブルの仕様に従ってください。
- 実取引連携（kabu API）や Slack 通知、監視ダッシュボード等は execution/ と monitoring 層に実装する想定です。

---

この README はコードベースの概要と代表的使用法をまとめたものです。詳細な設計仕様・数式等はリポジトリ内の設計ドキュメント（例: StrategyModel.md、DataPlatform.md、BacktestFramework.md）がある前提で参照してください。