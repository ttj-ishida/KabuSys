# KabuSys

日本株向けの自動売買システム基盤（ライブラリ）。データ取得・ETL、ファクター計算、特徴量作成、シグナル生成、バックテスト、ニュース収集などの機能を提供します。

主な設計方針は「ルックアヘッドバイアスの排除」「冪等性」「テスト容易性」「軽量な依存」です。DuckDBを主要なオンディスクDBとして利用し、外部API呼び出しはモジュール化されています。

---

## 主な機能

- データ取得・保存
  - J-Quants API クライアント（株価日足・財務・マーケットカレンダー）
  - raw データの DuckDB への冪等保存（ON CONFLICT）
- ETL / パイプライン
  - 差分更新、バックフィル、品質チェックフレームワーク
- 特徴量・ファクター
  - momentum / volatility / value 等のファクター計算（研究用モジュール）
  - クロスセクション Z スコア正規化
  - features テーブルへの日付単位の UPSERT（冪等）
- シグナル生成
  - features と ai_scores を統合して final_score を算出
  - Bear レジーム抑制、BUY / SELL シグナルの生成と signals テーブルへの保存
- ニュース収集
  - RSS フィード取得、前処理、raw_news / news_symbols への保存（SSRF対策・サイズ制限・トラッキング除去）
- バックテストフレームワーク
  - インメモリ DuckDB を用いた安全なバックテスト（本番DB汚染なし）
  - ポートフォリオシミュレータ（スリッページ・手数料モデル）、評価指標計算（CAGR・Sharpe・MaxDD 等）
- ユーティリティ
  - 市場カレンダー管理、統計ユーティリティ、スキーマ初期化ユーティリティ等

---

## 前提条件 / 推奨環境

- Python 3.10 以上（typing の union 型 `X | Y` を使用）
- 必要な外部パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants, RSS フィード）を行うための環境

（プロジェクト配布時は requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローン／配置

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージのインストール（例）
   - pip install duckdb defusedxml
   - （パッケージ化されている場合）pip install -e .

4. 環境変数設定
   - ルートに `.env` または `.env.local` を作成して必要なキーを設定するか、OS 環境変数として設定します。
   - 自動読み込みはデフォルトで有効（プロジェクトルートを .git または pyproject.toml で検出）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. データベース初期化（DuckDB のスキーマ作成）
   - Python で:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - またはインメモリ:
     conn = init_schema(":memory:")

---

## 必須／主な環境変数

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- DUCKDB_PATH — デフォルトの DuckDB パス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)(デフォルト: INFO)

settings は kabusys.config.settings から取得できます。

---

## 使い方（代表的な操作）

以下は主要なユースケースの簡単な例です。各 API は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。

1) スキーマ初期化（DB 作成）
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイルを作成してすべてのテーブルを作る

2) J-Quants からデータ取得・保存（概念）
   from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
   token = get_id_token()  # settings.jquants_refresh_token を用いて取得
   records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
   saved = save_daily_quotes(conn, records)

3) ETL（差分 ETL の一部）
   from kabusys.data.pipeline import run_prices_etl
   # run_prices_etl は取得→保存→品質チェックのヘルパを提供（詳細はモジュール参照）
   fetched, saved = run_prices_etl(conn, target_date=date.today())

4) 特徴量作成（features テーブル作成）
   from kabusys.strategy import build_features
   n = build_features(conn, target_date=date(2024, 1, 31))
   # target_date の行はまず削除され、その後インサートされる（冪等）

5) シグナル生成
   from kabusys.strategy import generate_signals
   total = generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)

6) ニュース収集ジョブ（RSS）
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})

7) バックテスト（CLI）
   - 提供されている CLI:
     python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb
   - オプション:
     --cash --slippage --commission --max-position-pct
   - 内部では本番 DB から必要データをインメモリにコピーし、日次ループで generate_signals → 約定模擬 → マークツーマーケットを行います。

8) バックテスト（プログラム API）
   from kabusys.backtest.engine import run_backtest
   result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
   # result.history / result.trades / result.metrics を参照

---

## ログ・実行モード

- 環境変数 `KABUSYS_ENV` により実行モード（development / paper_trading / live）を切替可能。
- `LOG_LEVEL` でログ出力レベルを制御（DEBUG/INFO/...）。
- settings は kabusys.config.Settings で提供されています。

---

## ディレクトリ構成（主要ファイルと説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込みと settings（自動 .env 読み込みロジックを含む）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント、保存ユーティリティ（raw_prices / raw_financials / market_calendar 等）
    - news_collector.py — RSS 取得・前処理・raw_news / news_symbols への保存
    - pipeline.py — ETL パイプライン（差分更新・バックフィル・品質チェック）
    - schema.py — DuckDB スキーマ定義と init_schema / get_connection
    - stats.py — Z スコア正規化等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — momentum / value / volatility のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ等の研究ユーティリティ
  - strategy/
    - __init__.py
    - feature_engineering.py — 生ファクターを正規化して features テーブルへ保存
    - signal_generator.py — features と ai_scores を統合して BUY/SELL を生成
  - backtest/
    - __init__.py
    - engine.py — run_backtest の実装。インメモリコピー、日次ループ、ポジション書き戻し等
    - simulator.py — PortfolioSimulator（擬似約定、履歴・取引記録）
    - metrics.py — バックテスト評価指標計算
    - run.py — CLI エントリポイント
    - clock.py — 将来拡張用の模擬時計（簡易）
  - execution/
    - __init__.py
    - （発注・ステータス管理・kabuステーション連携等の実装を想定）
  - monitoring/
    - （監視・アラート機能、Slack 通知等を想定）
- pyproject.toml / setup.cfg 等（プロジェクトルートに存在することが想定される）

---

## 開発メモ / 注意点

- 自動 `.env` 読み込みはプロジェクトルート（.git または pyproject.toml）を起点に行います。テスト時に自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API クライアントはレート制限（120 req/min）・リトライ・トークン自動リフレッシュ等を実装しています。
- ニュース収集は SS R F 対策、サイズ制限、トラッキングパラメータ除去、記事IDのハッシュ化などを行い冪等性を確保します。
- バックテストは本番 DB の signals/positions を汚染しないために、必要なテーブルを期間でフィルタしてインメモリ DB にコピーして実行します。
- DuckDB のバージョンや SQL 構文差異に注意してください（外部キー制約や ON DELETE 挙動についてソースにコメントあり）。

---

この README はコードベースの主要な使用法と構造の概要を示しています。各モジュールの詳細な使い方・引数仕様・例はソースコード内の docstring を参照してください。必要であれば、具体的なユースケース（ETL の実行スクリプト例やバックテスト分析ノート）を追加します。