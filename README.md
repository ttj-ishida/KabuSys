# KabuSys

日本株向けの自動売買 / 研究プラットフォーム。データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、バックテスト、ニュース収集などを含むモジュール群を備えています。

---

## プロジェクト概要

KabuSys は日本株の定量投資ワークフローを支援するライブラリです。主な目的は以下です。

- J-Quants API 等から株価・財務・カレンダー・ニュースを取得して DuckDB に保存（差分更新・冪等保存）
- 研究用ファクター計算（momentum / volatility / value など）
- 特徴量の正規化・合成（features テーブルへの保存）
- シグナル生成（final_score に基づいた BUY / SELL 判定）
- バックテスト（擬似約定・ポートフォリオシミュレーション・評価指標）
- RSS からのニュース収集と銘柄紐付け

設計上の特徴：
- DuckDB をデータストアに使用（軽量かつ分析向け）
- ETL / 保存処理は冪等（ON CONFLICT / トランザクション）を意識
- ルックアヘッドバイアス防止のため時点指定（target_date）での計算
- 外部 API 呼び出しは限定的に分離（テストしやすい設計）

---

## 機能一覧

主な機能（モジュール別）：

- kabusys.config
  - .env / 環境変数読込、必須設定の検証
- kabusys.data.jquants_client
  - J-Quants API クライアント（レートリミット・リトライ・トークン自動リフレッシュ）
  - データ保存: raw_prices / raw_financials / market_calendar などへの保存関数
- kabusys.data.schema
  - DuckDB スキーマ定義と初期化（init_schema）
- kabusys.data.pipeline
  - 差分 ETL 処理（run_prices_etl 等のジョブ）
- kabusys.data.news_collector
  - RSS フィード取得・前処理・raw_news 保存・銘柄抽出
- kabusys.research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 分析ユーティリティ（forward returns, IC, summary）
- kabusys.strategy
  - build_features: ファクターの正規化・features テーブル保存
  - generate_signals: features と ai_scores を統合してシグナル生成
- kabusys.backtest
  - run_backtest: インメモリ DB コピーによる日次ループのバックテスト
  - PortfolioSimulator / metrics: 約定シミュレーションと評価指標
- kabusys.data.news_collector
  - RSS の安全な取得（SSRF対策、サイズ制限、gzip 対応）と DB 保存

---

## セットアップ手順

前提
- Python 3.10 以上（タイプヒントに | を使用）
- DuckDB を使用するためネイティブ拡張が必要（pip で duckdb をインストール）

例: 仮想環境作成とインストール（リポジトリに requirements.txt がない場合の参考）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate
2. 必要パッケージをインストール
   - pip install duckdb defusedxml

（プロジェクトで使用する追加パッケージがある場合は requirements.txt を用意して pip install -r requirements.txt）

環境変数 / .env
- 自動でプロジェクトルート（.git または pyproject.toml を基準）下の `.env` および `.env.local` を読み込みます。
- 自動ロードを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数（Settings にて _require される）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabu API 用パスワード
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack チャンネル ID

任意 / デフォルト:
- KABUS_API_BASE_URL : デフォルト http://localhost:18080/kabusapi
- DUCKDB_PATH        : デフォルト data/kabusys.duckdb
- SQLITE_PATH        : デフォルト data/monitoring.db
- KABUSYS_ENV        : development / paper_trading / live（デフォルト development）
- LOG_LEVEL          : DEBUG/INFO/…（デフォルト INFO）

DB 初期化
- DuckDB スキーマを作成:
  - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
  - もしくは :memory: テスト用接続: init_schema(":memory:")

---

## 使い方

以下は代表的な操作例です。

1) DuckDB の初期化
- ファイル DB を作成してスキーマを生成:
  - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

2) データ取得（J-Quants）と保存
- J-Quants から株価・財務を取得して保存するフロー（スクリプトやジョブ内で実行）:
  - from kabusys.data import jquants_client as jq
  - from kabusys.data.schema import get_connection
  - conn = get_connection('data/kabusys.duckdb')
  - records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  - jq.save_daily_quotes(conn, records)

- 実運用では data.pipeline モジュールの差分 ETL ジョブ（run_prices_etl 等）を用いる想定です。

3) 特徴量作成
- DuckDB 接続と日付を与えて features を構築:
  - from kabusys.strategy import build_features
  - build_features(conn, target_date)

4) シグナル生成
- features と ai_scores を統合して signals テーブルへ書き出す:
  - from kabusys.strategy import generate_signals
  - generate_signals(conn, target_date, threshold=0.6, weights=None)

5) バックテスト実行（CLI）
- 用意した DB を使って期間指定でバックテストを実行:
  - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb
- オプション:
  - --cash, --slippage, --commission, --max-position-pct

6) ニュース収集
- RSS からニュースを収集して DB に保存:
  - from kabusys.data.news_collector import run_news_collection
  - run_news_collection(conn, sources=None, known_codes=set_of_codes)

7) ライブラリ的な利用（REPL）
- duckdb 接続を取得して関数を呼ぶだけで各処理が実行できます。各関数はトランザクション管理や冪等性を考慮して実装されています。

注意点
- generate_signals / build_features 等は target_date 時点のデータのみを使う設計です。ルックアヘッドバイアスに注意してください。
- jquants_client はレート制限・リトライ・トークン更新を実装しています。大量リクエスト時は設定に従ってください。

---

## ディレクトリ構成（主なファイルと説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env 読み込み・設定オブジェクト settings
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント、save_* 関数
    - news_collector.py
      - RSS 取得・前処理・raw_news 保存・銘柄抽出
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py
      - ETL 差分更新ロジック（run_prices_etl 等）
    - stats.py
      - zscore_normalize などの統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_volatility / calc_value
    - feature_exploration.py
      - forward returns / IC / factor_summary
  - strategy/
    - __init__.py
    - feature_engineering.py
      - build_features: ファクター正規化と features への保存
    - signal_generator.py
      - generate_signals: final_score 計算と signals への保存
  - backtest/
    - __init__.py
    - engine.py
      - run_backtest（インメモリ DB コピー、日次ループ）
    - simulator.py
      - PortfolioSimulator、約定/時価評価ロジック
    - metrics.py
      - バックテスト評価指標算出（CAGR, Sharpe, MaxDD 等）
    - run.py
      - CLI エントリポイント（python -m kabusys.backtest.run）
    - clock.py
      - SimulatedClock（将来的な用途）
  - execution/
    - __init__.py
    - （発注 / execution 層はこれからの実装想定）
  - monitoring/
    - （監視系・Slack 通知などを置く想定）

---

## 開発・運用上の注意

- 環境変数は .env / .env.local に保存して運用するのが簡単です。機密情報（トークン等）は適切に管理してください。
- DuckDB のファイルはバックアップやバージョン管理対象にしないでください（大容量になり得ます）。
- テスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env ロードを抑止できます。
- ニュース収集は外部 HTTP を伴うため、SSRF や巨大レスポンス等の安全対策を実装済みですが、プロキシやネットワーク環境での検証を推奨します。

---

## 参考コマンド一覧

- スキーマ初期化:
  - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
- バックテスト実行:
  - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb
- REPL で機能呼び出しの例:
  - python - <<'PY'
    from kabusys.data.schema import get_connection
    from kabusys.strategy import build_features, generate_signals
    from datetime import date
    conn = get_connection('data/kabusys.duckdb')
    build_features(conn, date(2024,1,31))
    generate_signals(conn, date(2024,1,31))
    conn.close()
    PY

---

README に載せきれない詳細（API 引数や内部実装の注意点）は各モジュールの docstring を参照してください。必要であれば README に追加すべき使い方や例を追記しますので、目的（ETL ジョブ手順、CI 用コマンド、デプロイ手順 等）を教えてください。