# KabuSys

KabuSys は日本株向けの自動売買／リサーチ基盤ライブラリです。  
DuckDB をデータストアとして利用し、ファクター計算 → 特徴量構築 → シグナル生成 → （バックテスト / 実運用）というワークフローをコードで提供します。モジュールは研究用（research）、データ収集（data）、戦略（strategy）、ポートフォリオ構築（portfolio）、バックテスト（backtest）などに分かれており、再現性・冪等性・Look-ahead バイアス対策を重視した実装になっています。

主な想定用途:
- 研究環境でのファクター探索・IC 計算
- 日次バッチでの features / signals 生成
- DuckDB を用いたバックテスト
- J-Quants / RSS からのデータ収集（ETL）
- ポートフォリオ構築ロジック（サイジング / セクター制限 / レジーム対応）

---

## 機能一覧

- データ取得・ETL
  - J-Quants API クライアント（ページネーション、リトライ、トークン自動更新、レート制御）
  - RSS ニュース収集（SSRF 対策、トラッキングパラメータ除去、記事ID ハッシュ化）
  - raw_* テーブルへの冪等保存関数
- 研究（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
- 特徴量構築（strategy.feature_engineering）
  - ファクターの正規化・クリッピング・ユニバースフィルタ適用・features テーブルへの UPSERT
- シグナル生成（strategy.signal_generator）
  - features + ai_scores を統合して final_score を計算
  - Bear レジーム抑制、BUY/SELL 生成、signals テーブルへの冪等書込
- ポートフォリオ（portfolio）
  - 候補選択、等金額/スコア分配、リスクベースサイジング、セクターキャップ適用、レジーム乗数
- バックテスト（backtest）
  - インメモリ DuckDB へのデータコピーを含むバックテストエンジン
  - ポートフォリオシミュレータ（スリッページ・手数料・部分約定対応）
  - 評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio 等）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- 設定管理
  - .env / 環境変数自動読み込み（プロジェクトルート検出、.env → .env.local 読み込み順）
  - 必須環境変数チェック

---

## セットアップ手順

前提: Python 3.10 以上を推奨（typing の使用に伴う）。  
以下は開発環境での例です。

1. リポジトリをクローンして依存をインストール
   - 例:
     - git clone <repo>
     - cd <repo>
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -e ".[dev]" または最低限:
       - pip install duckdb defusedxml

   （requirements / pyproject.toml がある場合はそちらに従ってください）

2. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` を置くと自動で読み込まれます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（必須）:
   - JQUANTS_REFRESH_TOKEN  — J-Quants 用リフレッシュトークン（fetch API 用）
   - KABU_API_PASSWORD      — kabuステーション API パスワード（実行時に必要）
   - SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン（通知機能を使う場合）
   - SLACK_CHANNEL_ID       — Slack チャンネル ID

   任意 / デフォルトあり:
   - DUCKDB_PATH            — データファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH            — 監視用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_ENV            — environment: development | paper_trading | live（デフォルト development）
   - LOG_LEVEL              — ログレベル（DEBUG/INFO/...）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=xxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. DuckDB スキーマ初期化
   - 本プロジェクトではスキーマ初期化関数（例: kabusys.data.schema.init_schema）を通じて DB を初期化する設計です。実行前に必要なテーブル（prices_daily, raw_prices, raw_financials, features, signals, positions, market_calendar, stocks, ai_scores など）を用意してください。
   - サンプル: Python REPL / スクリプトで init_schema を呼ぶ
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     # 必要なら初期データロード処理を実行
     conn.close()
     ```

4. J-Quants / RSS を用いる場合
   - J-Quants の API を利用するには JQUANTS_REFRESH_TOKEN を設定してください。
   - ニュース収集を使う場合はインターネットアクセスと defusedxml が必要です。

---

## 使い方

主な利用例をいくつか示します。

- バックテスト（CLI）
  - provided CLI: python -m kabusys.backtest.run
  - 例:
    ```
    python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2024-12-31 \
      --cash 10000000 --db data/kabusys.duckdb \
      --allocation-method risk_based --lot-size 100
    ```
  - オプション:
    - --start / --end: YYYY-MM-DD（必須）
    - --db: DuckDB ファイルパス（必須）
    - --cash / --slippage / --commission / --max-position-pct / --allocation-method 等は help を参照

- 特徴量構築（feature engineering）
  - DuckDB コネクションを渡して日次の features を構築します:
    ```python
    import duckdb
    from kabusys.strategy.feature_engineering import build_features
    conn = duckdb.connect("data/kabusys.duckdb")
    from datetime import date
    count = build_features(conn, target_date=date(2024, 1, 31))
    conn.close()
    print(f"upserted {count} features")
    ```

- シグナル生成
  - features / ai_scores / positions を参照して signals テーブルを更新します:
    ```python
    from kabusys.strategy.signal_generator import generate_signals
    conn = duckdb.connect("data/kabusys.duckdb")
    num = generate_signals(conn, target_date=date(2024,1,31), threshold=0.6)
    conn.close()
    print(f"generated {num} signals")
    ```

- バックテストを Python API として実行
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest
  from datetime import date
  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  conn.close()
  # result.history, result.trades, result.metrics を参照
  ```

- ニュース収集の一括ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection
  conn = init_schema("data/kabusys.duckdb")
  known_codes = set(["7203", "6758", ...])  # stocks マスタから取得する想定
  results = run_news_collection(conn, known_codes=known_codes)
  ```

注意:
- J-Quants など外部 API を使う関数はネットワーク、認証トークン、レート制限に依存します。API トークンやリクエスト制御に注意してください。
- DuckDB へはモジュール内の関数が直接 SQL を実行します。スキーマが想定通りであることを事前に確認してください。

---

## 設定 / 環境変数（まとめ）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意 / デフォルト:
- DUCKDB_PATH  (default: data/kabusys.duckdb)
- SQLITE_PATH  (default: data/monitoring.db)
- KABUSYS_ENV  (development | paper_trading | live) default: development
- LOG_LEVEL    (DEBUG | INFO | ...) default: INFO

自動読み込み:
- プロジェクトルートにある .env と .env.local を自動で読み込みます（OS 環境変数が優先）。
- 無効化: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（抜粋）

以下はパッケージの主なファイル / モジュールと役割の一覧です（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み・Settings クラス
  - data/
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - news_collector.py     — RSS 収集・前処理・DB 保存
    - (schema.py, calendar_management などは実装想定)
  - research/
    - factor_research.py    — モメンタム/ボラティリティ/バリュー等の計算
    - feature_exploration.py— IC / forward returns / 統計サマリ
  - strategy/
    - feature_engineering.py— features の作成（正規化・フィルタ・UPSERT）
    - signal_generator.py   — final_score 計算、BUY/SELL 生成、signals 保存
  - portfolio/
    - portfolio_builder.py  — 候補選定・重み計算（select/calc_*）
    - position_sizing.py    — 株数計算、aggregate cap、lot rounding
    - risk_adjustment.py    — セクターキャップ、レジーム乗数
  - backtest/
    - engine.py             — バックテストの全体ループ
    - simulator.py          — 擬似約定・ポートフォリオ管理
    - metrics.py            — バックテスト評価指標計算
    - run.py                — CLI エントリポイント
    - clock.py              — 将来用の模擬時計クラス
  - execution/ (プレースホルダ)
  - monitoring/ (プレースホルダ)
  - portfolio/ __init__.py  — API エクスポート

この README では主要ファイルのみ抜粋しています。詳細な実装や SQL スキーマはソースを参照してください。

---

## 開発上の注意 / ベストプラクティス

- Look-ahead バイアス回避のため、feature/signal の計算は常に target_date 以前のデータのみを使用する設計です。DuckDB のテーブル更新や ETL 順序には注意してください。
- バックテストでは本番 DB の signals / positions を汚染しないため、エンジンがインメモリのコピーを作成します。実行時には十分なメモリを確保してください。
- 実運用（live）では KABUSYS_ENV を `live` に設定し、発注周り（execution 層）を十分にテストしてください（本リポジトリの execution はプレースホルダの場合あり）。

---

必要に応じて README を拡張します。ドキュメント化したい特定の関数やセットアップ手順（例: schema の初期化 SQL、Docker コンテナ化、CI ワークフロー等）があれば教えてください。