# KabuSys

日本株向けの自動売買／研究プラットフォーム（KabuSys）のコードベース README。  
このリポジトリはデータ収集（J-Quants）、ETL、特徴量生成、シグナル生成、バックテスト、ニュース収集、簡易ポートフォリオシミュレーションなどを含むモジュール群で構成されています。

## プロジェクト概要
KabuSys は以下を目的としたコンポーネント群を提供します。

- J-Quants API からの株価・財務・カレンダー等の取得と DuckDB への保存（冪等）
- RSS を用いたニュース収集と記事 ↔ 銘柄紐付け
- 研究（research）で算出した生ファクターを正規化・合成して戦略用特徴量（features）を作成
- features と AI スコアを統合して売買シグナルを生成
- signals を用いたバックテスト（インメモリ DuckDB を利用）
- バックテスト用の約定モデル・ポートフォリオシミュレータ・評価指標の計算

設計上の特徴:
- DuckDB をデータレイク/DB として利用（ファイルまたはインメモリ）
- 冪等な保存ロジック（ON CONFLICT / INSERT ... DO UPDATE / DO NOTHING）
- ルックアヘッドバイアス対策（target_date ベースでデータ参照）
- ネットワーク処理や RSS 収集にセキュリティ対策（SSRF対策、XML 防御、レスポンス上限など）

---

## 機能一覧
主要な機能（モジュール単位）

- data/
  - jquants_client.py: J-Quants API クライアント（レート制限・リトライ・トークン自動リフレッシュ・保存関数）
  - news_collector.py: RSS フィードから記事取得・前処理・DB 保存・銘柄抽出
  - schema.py: DuckDB スキーマ定義と初期化（テーブル群の作成）
  - pipeline.py: ETL パイプライン（差分取得・バックフィル・品質チェックの補助）
  - stats.py: Z スコア正規化など統計ユーティリティ
- research/
  - factor_research.py: モメンタム/ボラティリティ/バリュー等ファクター計算
  - feature_exploration.py: 将来リターン計算・IC（スピアマン）・統計サマリーなど
- strategy/
  - feature_engineering.py: 生ファクターを正規化・合成して features テーブルに保存
  - signal_generator.py: features + ai_scores を統合して BUY/SELL シグナルを生成（signals テーブルへ）
- backtest/
  - engine.py: バックテストの全体ループ（本番 DB からインメモリへコピーして実行）
  - simulator.py: 約定ロジック・ポートフォリオ状態管理（スリッページ・手数料モデル）
  - metrics.py: バックテスト評価指標（CAGR, Sharpe, MaxDD, 勝率 等）
  - run.py: CLI エントリポイント（python -m kabusys.backtest.run）
- execution/, monitoring/
  - 発注実装や監視関連のエントリポイント（将来的な拡張領域）
- config.py: 環境変数・設定管理（.env / .env.local の自動読み込みロジックを含む）

---

## セットアップ手順

前提
- Python 3.10 以上（コードは | 型注釈等を使用）
- Git リポジトリのルートまたは pyproject.toml がある階層で作業することを推奨

1. リポジトリをクローン
   - git clone ... （省略）

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 必要パッケージのインストール（最低限）
   - pip install duckdb defusedxml
   - （追加で開発用に logging 等は標準ライブラリで足ります）
   - 実運用では HTTP 周りやリトライ・API モジュールに依存ライブラリを追加する場合があります。

   参考の最小 requirements:
   - duckdb
   - defusedxml

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと、自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN=<あなたの J-Quants リフレッシュトークン>
     - KABU_API_PASSWORD=<kabu ステーション API パスワード>
     - SLACK_BOT_TOKEN=<Slack bot token>
     - SLACK_CHANNEL_ID=<通知先 Slack チャンネル ID>
   - 任意:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト INFO
     - DUCKDB_PATH (例: data/kabusys.duckdb) — data.schema.init_schema の既定値も同様
     - SQLITE_PATH (監視用 DB パス)
   - サンプル (.env.example に倣って)：
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=secret
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```

5. DuckDB スキーマ初期化
   - Python REPL / スクリプトでスキーマを作成します:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```
   - またはインメモリでテストする場合:
     ```python
     conn = init_schema(":memory:")
     ```

---

## 使い方（主要コマンド・コード例）

以下は代表的な利用例です。

1. バックテスト（CLI）
   - リポジトリの仮想環境で次を実行:
     ```
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --cash 10000000 --db data/kabusys.duckdb
     ```
   - 出力にバックテスト結果（CAGR, Sharpe, MaxDD 等）が表示されます。
   - オプション: --slippage, --commission, --max-position-pct

2. 特徴量構築（Python スクリプト例）
   ```python
   from datetime import date
   from kabusys.data.schema import init_schema, get_connection
   from kabusys.strategy import build_features

   conn = init_schema("data/kabusys.duckdb")
   cnt = build_features(conn, date(2024, 1, 31))
   print(f"features upserted: {cnt}")
   conn.close()
   ```

3. シグナル生成（Python）
   ```python
   from datetime import date
   from kabusys.data.schema import get_connection
   from kabusys.strategy import generate_signals
   import duckdb

   conn = duckdb.connect("data/kabusys.duckdb")
   n = generate_signals(conn, date(2024,1,31))
   print(f"signals written: {n}")
   conn.close()
   ```

4. ニュース収集（RSS）と保存
   ```python
   import duckdb
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   conn = duckdb.connect("data/kabusys.duckdb")
   # known_codes は銘柄抽出に使う有効コードセット（例: {"7203","6758",...}）
   res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
   print(res)
   conn.close()
   ```

5. J-Quants からの差分 ETL（株価）
   - pipeline.run_prices_etl や pipeline の他ジョブを利用して差分取得 → 保存 → 品質チェックを実行できます（コード内の API 呼出し/保存関数を利用）。
   - 例（概略）:
     ```python
     from datetime import date
     import duckdb
     from kabusys.data.pipeline import run_prices_etl

     conn = duckdb.connect("data/kabusys.duckdb")
     fetched, saved = run_prices_etl(conn, target_date=date.today())
     conn.close()
     ```

6. 開発用 / テスト用にインメモリ DB を使ったバックテスト
   - backtest.engine.run_backtest は source_conn からインメモリ DB にコピーして実行するので、既存の本番 DB を汚さずにテストできます。

---

## 重要な環境変数（summary）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用の refresh token
- KABU_API_PASSWORD (必須) — kabu API 接続パスワード
- SLACK_BOT_TOKEN (必須) — Slack 通知用
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH（任意、default: data/kabusys.duckdb）
- SQLITE_PATH（任意、default: data/monitoring.db）
- KABUSYS_ENV（development | paper_trading | live）
- LOG_LEVEL（DEBUG, INFO, ...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化

config.Settings クラスを通して設定値にアクセスできます（例: from kabusys.config import settings; settings.jquants_refresh_token）。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要ファイルと概要です。

- kabusys/
  - __init__.py
  - config.py              — 環境変数・設定管理（.env 自動ロード含む）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント / 保存関数
    - news_collector.py     — RSS 取得・前処理・保存・銘柄抽出
    - schema.py             — DuckDB スキーマ定義 / init_schema
    - pipeline.py           — ETL パイプライン補助・差分更新ヘルパー
    - stats.py              — zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py    — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py— 将来リターン, IC, 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py— features の構築・正規化・保存
    - signal_generator.py   — final_score 計算、BUY/SELL シグナル生成、signals 保存
  - backtest/
    - __init__.py
    - engine.py             — バックテスト全体ループ（run_backtest）
    - simulator.py          — 約定モデル・PortfolioSimulator
    - metrics.py            — バックテスト評価指標
    - clock.py              — SimulatedClock（将来拡張用）
    - run.py                — CLI ラッパー（python -m kabusys.backtest.run）
  - execution/
    - __init__.py           — 発注・execution 層（拡張領域）
  - monitoring/             — 監視・通知用コード（拡張領域）

---

## 開発メモ / 注意点
- DuckDB のバージョン差異により一部の外部キーや ON DELETE 挙動の扱いがコメントに残っています（schema.py を参照）。
- ネットワーク/外部 API 呼び出しはリトライやレート制御、Token refresh を実装済みですが、実運用ではレート制御や retry の調整が必要です。
- ルックアヘッドバイアス防止のため、ほとんどの計算・シグナル生成は target_date 時点のデータのみ参照します。データの fetched_at 等をトレースする運用が推奨されます。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索して行います。テスト時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って無効化できます。

---

必要であれば、README に追加したい内容（例: 開発フロー、CI 設定、より詳細な API 使用例、.env.example の実体など）を教えてください。