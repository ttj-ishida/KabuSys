# KabuSys

日本株向けの自動売買およびバックテスト用ライブラリ / フレームワークです。  
特徴量計算、シグナル生成、ポートフォリオ構築、擬似約定によるバックテスト、J-Quants / RSS ベースのデータ収集など、研究〜本番までのワークフローを想定したモジュール群を提供します。

---

## プロジェクト概要

KabuSys は次の要素を提供します。

- DuckDB を用いた時系列データ / メタデータの管理（prices, financials, features, signals, positions 等）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量（features）作成、AI スコア（ai_scores）との統合によるシグナル生成
- ポートフォリオ構築（候補選定、重み計算、リスク調整、ポジションサイジング）
- バックテスト用シミュレータ（スリッページ・手数料モデル、日次スナップショット・トレード記録）
- J-Quants API クライアント（日足・財務・上場銘柄・カレンダー取得）
- RSS ニュース収集（raw_news / news_symbols への保存、簡易銘柄抽出）
- 設定管理（.env / 環境変数）

設計方針として「ルックアヘッドバイアス回避」「冪等性」「単一責務の純粋関数化」を重視しています。

---

## 主な機能一覧

- Data
  - J-Quants API クライアント（認証、レート制御、リトライ）
  - RSS ニュース収集（SSRF対策、トラッキング除去、前処理）
  - DuckDB への冪等保存ユーティリティ
- Research
  - モメンタム / ボラティリティ / バリューのファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - Z スコア正規化ユーティリティ
- Strategy
  - 特徴量構築（build_features）
  - シグナル生成（generate_signals：BUY/SELL を features と ai_scores から生成）
- Portfolio
  - 候補選定（select_candidates）
  - 重み計算（等配分・スコア加重）
  - リスク調整（セクター上限、レジーム乗数）
  - ポジションサイジング（risk_based / equal / score）
- Backtest
  - ポートフォリオシミュレータ（擬似約定、スリッページ・手数料反映）
  - バックテストエンジン（期間ループ、データのインメモリ複製、結果出力）
  - メトリクス計算（CAGR, Sharpe, MaxDD, WinRate, PayoffRatio 等）
  - CLI ランナー（python -m kabusys.backtest.run）
- その他
  - 環境変数・.env 自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - ログレベル制御、環境（development / paper_trading / live）判定

---

## 要件（推奨）

- Python 3.10+
- 必須パッケージ例（明示的な requirements.txt が無い場合の最低限）
  - duckdb
  - defusedxml

実際の開発・実行環境では pyproject.toml / poetry / pipenv 等で依存管理してください。

---

## セットアップ手順

1. リポジトリをクローンして開発環境を作成します。

   ```
   git clone <repo-url>
   cd <repo-dir>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストールします（例）:

   ```
   pip install duckdb defusedxml
   ```

   pyproject.toml / requirements.txt があればそちらを利用してください。

3. 環境変数を準備します。プロジェクトルートに `.env`（および必要なら `.env.local`）を作成してください。最低限必要なキー：

   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（本番接続時）
   - SLACK_BOT_TOKEN: 通知用 Slack ボットトークン（通知機能を使う場合）
   - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID
   - DUCKDB_PATH: DuckDB ファイルパス（例: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite ファイルパス（例: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（省略時: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（省略時: INFO）

   例 (.env):

   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   自動読み込みを無効にする場合（テスト等）:

   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

4. DuckDB スキーマの初期化（スキーマ用ユーティリティが提供されている想定）:

   （注）リポジトリ内に schema 初期化関数が参照されています。実運用ではスキーマ初期化関数（kabusys.data.schema.init_schema）を使って DB を作成してください。

   例（概念）:

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

5. データ取得（J-Quants から日足・財務・上場銘柄・カレンダーを取得して保存）:

   例（概念）:

   ```python
   from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   token = get_id_token()
   records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
   save_daily_quotes(conn, records)
   conn.close()
   ```

   実際は API レート制限・ページネーション・fetched_at を考慮したバッチ処理を行ってください。

---

## 使い方（代表的なワークフロー）

1. 特徴量の構築（features テーブルへ UPSERT）
   - モジュール: kabusys.strategy.feature_engineering.build_features
   - 使い方（Python）:

     ```python
     from datetime import date
     import duckdb
     from kabusys.strategy import build_features
     from kabusys.data.schema import init_schema

     conn = init_schema("data/kabusys.duckdb")
     n = build_features(conn, target_date=date(2024, 1, 31))
     print(f"features updated: {n}")
     conn.close()
     ```

2. シグナル生成（features + ai_scores → signals テーブル）
   - モジュール: kabusys.strategy.signal_generator.generate_signals

     ```python
     from datetime import date
     from kabusys.strategy import generate_signals
     conn = init_schema("data/kabusys.duckdb")
     total = generate_signals(conn, target_date=date(2024,1,31))
     print(f"signals generated: {total}")
     conn.close()
     ```

3. バックテストの実行（CLI）
   - 提供 CLI: python -m kabusys.backtest.run

   例:

   ```
   python -m kabusys.backtest.run \
     --start 2023-01-01 --end 2024-12-31 \
     --cash 10000000 --db data/kabusys.duckdb \
     --allocation-method risk_based --max-positions 10
   ```

   上記は DuckDB に予め prices_daily, features, ai_scores, market_regime, market_calendar が整備されていることが前提です。

4. ニュース収集（RSS）
   - モジュール: kabusys.data.news_collector.run_news_collection
   - 概念コード:

     ```python
     from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     known_codes = set(...)  # stocks.code のセット
     results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
     conn.close()
     print(results)
     ```

---

## 注意点 / 運用上のヒント

- ルックアヘッドバイアス:
  - 戻り値の計算やシグナル生成は target_date 時点までのデータのみを使用するよう設計されています。バックテストでも同様にデータを整備してください。
- 環境変数の自動読み込み:
  - パッケージインポート時にプロジェクトルート（.git または pyproject.toml を探索）を見て `.env` / `.env.local` を自動で読み込みます。テスト時などで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API:
  - レート制限（120 req/min）や 401 自動リフレッシュ、リトライロジックを組み込んでいます。大量データ取得はバッチ化して実行してください。
- 単元株・丸め:
  - ポジションサイジング / 約定は lot_size（デフォルト 100）に基づく丸めを行います。将来的に銘柄別単元対応の拡張が示唆されています。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / .env 読み込み
  - data/
    - jquants_client.py               — J-Quants API クライアント（取得・保存）
    - news_collector.py               — RSS ニュース収集・保存
    - ...（schema, calendar_management 等が想定される）
  - research/
    - factor_research.py              — ファクター計算（momentum, volatility, value）
    - feature_exploration.py          — 将来リターン / IC / summary
  - strategy/
    - feature_engineering.py          — features 作成（正規化・クリップ・保存）
    - signal_generator.py             — シグナル生成（BUY/SELL）
  - portfolio/
    - portfolio_builder.py            — 候補選定・重み付け
    - position_sizing.py              — 発注株数計算（risk_based 等）
    - risk_adjustment.py              — セクターキャップ、レジーム乗数
  - backtest/
    - engine.py                       — バックテスト主ループ（run_backtest）
    - simulator.py                    — 擬似約定・ポートフォリオ状態管理
    - metrics.py                      — バックテスト評価指標
    - run.py                          — CLI エントリポイント
    - clock.py
  - execution/                         — 発注（空の __init__ が存在）
  - portfolio/                         — 上述のポートフォリオ関連
  - monitoring/                        — 監視 / 通知用モジュール（想定）
  - ...（その他ユーティリティ群）

---

## 開発者向け情報 / 貢献

- 型ヒント（Python 3.10 の | 表記）を使用しています。ローカルでの実行は Python 3.10 以上を推奨します。
- テストや CI、E2E 用のダミー DB 作成・シードスクリプトを用意すると開発効率が向上します。
- 大きな外部依存（J-Quants、ネットワーク）にアクセスする部分は抽象化/モックしやすい設計を心がけています。ユニットテストではネットワーク呼び出しをモックしてください。

---

## 参考コマンドまとめ

- バックテスト（CLI）:

  ```
  python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb
  ```

- Python REPL で特徴量計算・シグナル生成（例）:

  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features, generate_signals

  conn = init_schema("data/kabusys.duckdb")
  build_features(conn, date(2024,1,31))
  generate_signals(conn, date(2024,1,31))
  conn.close()
  ```

---

README に記載の操作は、環境によって事前準備（DB スキーマ定義・初期データ投入）が必要です。具体的な ETL や schema の初期化スクリプトは別途用意して運用してください。必要であれば README を拡張してスキーマ初期化手順やサンプル .env.example を作成しますので、追加で指示ください。