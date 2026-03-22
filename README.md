# KabuSys

日本株向けの自動売買システム（研究・データ基盤・戦略・バックテストを含む）です。  
このリポジトリは、J-Quants API からのデータ取得、ETL、特徴量作成、シグナル生成、擬似約定を含むバックテストフレームワークを備えています。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（代表的なワークフロー）
- 環境変数と設定
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システムの基盤実装です。  
主な目的は次のとおりです。

- J-Quants 等の外部データソースからデータを取得して DuckDB に蓄積する（冪等保存、差分更新）
- 研究向けのファクター計算・探索（モメンタム・ボラティリティ・バリュー等）
- 特徴量エンジニアリング → 正規化済み features テーブルの作成
- features と AI スコアを統合したシグナル生成（BUY / SELL）
- バックテストエンジン（擬似約定・スリッページ・手数料モデル付き）
- ニュース収集（RSS）と銘柄紐付け
- DB スキーマ管理 / ETL パイプライン

設計上、戦略モジュールは発注 API に直接依存せず、ルックアヘッドバイアスを避けるよう target_date 時点のみのデータを用いるようになっています。

---

## 機能一覧

- データ取得
  - J-Quants クライアント（株価、財務、マーケットカレンダー）
  - RSS ベースのニュース収集（SSRF対策・gzip制限・トラッキング除去）
- ETL パイプライン
  - 差分取得・バックフィル（API後出し修正吸収）
  - 品質チェック（欠損・スパイク等）
- データモデル（DuckDB）
  - raw / processed / feature / execution 層のスキーマとインデックス
- 研究モジュール
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC（Spearman）や統計サマリ
- 特徴量エンジニアリング
  - Z スコア正規化、ユニバースフィルタ、日次アップサート
- シグナル生成
  - ファクター + AI スコアの統合、Bear レジーム判定、BUY/SELL 生成、冪等な signals テーブル書き込み
- バックテスト
  - インメモリ DuckDB にデータをコピーして日次シミュレーション（擬似約定、ポートフォリオ管理）
  - 評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- ニュース処理
  - 記事IDは正規化 URL の SHA-256 を利用（冪等保存）
  - 銘柄コード抽出と news_symbols への紐付け

---

## セットアップ手順

※ 以下は開発・実行の最小手順例です。プロダクション運用時はセキュリティやデプロイの追加設定が必要です。

1. 前提
   - Python 3.9+（ソースは typing | from __future__ に対応）
   - DuckDB（Python パッケージとしてインストール）
   - ネットワーク接続（J-Quants API / RSS）

2. 必要な Python パッケージをインストール（例）
   - duckdb
   - defusedxml
   - その他: 標準ライブラリのみで実装されている箇所も多いですが、実行環境によって追加依存があるかもしれません。

   例:
   pip install duckdb defusedxml

3. リポジトリをクローンしてパッケージをプロジェクト配下に置く
   - 開発環境では src/ を PYTHONPATH に追加するか、pip install -e . を用いて editable install してください。

4. 環境変数 / .env の準備
   - 必須環境変数（後述の「環境変数と設定」を参照）
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（CWD ではなくソースファイルのパスからプロジェクトルートを探索）。

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトで初期化します:

     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()

   - メモリ DB を使う場合は db_path に ":memory:" を指定できます。

6. データ取得（ETL）
   - J-Quants トークンを用意し prices / financials / market calendar を差分で取得します（pipeline モジュールの run_prices_etl 等）。
   - 例（簡単なスクリプト）:

     from datetime import date
     from kabusys.data.schema import init_schema
     from kabusys.data.pipeline import run_prices_etl

     conn = init_schema("data/kabusys.duckdb")
     result = run_prices_etl(conn, target_date=date.today())
     conn.close()

7. バックテストの実行（CLI）
   - 既に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar）が揃っていることが前提。

     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --cash 10000000 --db data/kabusys.duckdb

---

## 使い方（代表的なワークフロー）

ここでは代表的な操作の例を示します。

1. DB の初期化
   - Python:

     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()

2. ETL（株価差分取得）
   - pipeline.run_prices_etl を用いる（id_token を注入可能）:

     from datetime import date
     from kabusys.data.schema import init_schema
     from kabusys.data.pipeline import run_prices_etl

     conn = init_schema("data/kabusys.duckdb")
     fetched_count, saved_count = run_prices_etl(conn, target_date=date.today())
     conn.close()

3. ニュース収集
   - run_news_collection を使用:

     from kabusys.data.news_collector import run_news_collection
     from kabusys.data.schema import init_schema

     conn = init_schema("data/kabusys.duckdb")
     results = run_news_collection(conn, known_codes={"7203","6758"})
     conn.close()

4. 特徴量作成（feature engineering）
   - build_features を呼び出して features テーブルを作成:

     from datetime import date
     from kabusys.strategy import build_features
     from kabusys.data.schema import init_schema

     conn = init_schema("data/kabusys.duckdb")
     count = build_features(conn, target_date=date(2024,1,1))
     conn.close()

5. シグナル生成
   - generate_signals を呼び出して signals テーブルを更新:

     from datetime import date
     from kabusys.strategy import generate_signals
     from kabusys.data.schema import init_schema

     conn = init_schema("data/kabusys.duckdb")
     total = generate_signals(conn, target_date=date(2024,1,1))
     conn.close()

6. バックテスト実行（Python API）
   - run_backtest を用いる:

     from datetime import date
     from kabusys.data.schema import init_schema
     from kabusys.backtest.engine import run_backtest

     conn = init_schema("data/kabusys.duckdb")
     result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
     conn.close()

   - 結果は BacktestResult（history, trades, metrics）として返されます。

---

## 環境変数と設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます。プロジェクトルートはこのパッケージファイルの位置から `.git` または `pyproject.toml` を探索して自動検出されます。

自動ロードを無効にする場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等用）。

重要な環境変数（Settings クラスにより必須/デフォルト値あり）:

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (オプション、デフォルト: http://localhost:18080/kabusapi)
- Slack
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- DB パス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
- 実行環境
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト INFO

設定は kabusys.config.settings から参照できます。未設定の必須項目は ValueError が発生します。

---

## ディレクトリ構成（主要ファイル）

以下はソースの主要な構成です（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント & 保存ロジック
    - news_collector.py      — RSS 収集・前処理・保存
    - schema.py              — DuckDB スキーマ定義 / init_schema
    - stats.py               — zscore_normalize 等の統計ユーティリティ
    - pipeline.py            — ETL パイプライン（差分取得等）
    - quality.py?            — （品質チェックモジュール参照: pipeline から利用想定）
  - research/
    - __init__.py
    - factor_research.py     — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py — 前方リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py — features 作成（正規化・ユニバースフィルタ）
    - signal_generator.py    — final_score 計算と BUY/SELL 生成
  - backtest/
    - __init__.py
    - engine.py              — run_backtest（インメモリコピー・日次ループ）
    - simulator.py           — PortfolioSimulator（擬似約定・履歴保持）
    - metrics.py             — バックテスト評価指標計算
    - run.py                 — CLI エントリポイント（python -m kabusys.backtest.run）
    - clock.py               — SimulatedClock（将来拡張用）
  - execution/               — 発注 / 実行層（パッケージ用意済み）
  - monitoring/              — 監視・アラート（パッケージ用意済み）

（実ファイルは src/kabusys 以下を参照してください）

---

## 補足 / 注意点

- DuckDB スキーマは init_schema() で冪等に作成されます。既存データの上書きに注意してください。
- J-Quants API はレート制限（120 req/min）や 401 トークンリフレッシュ、リトライロジックを実装済みですが、実運用では API 利用規約とレート制御に注意してください。
- ニュース取得は SSRF 対策、gzip 上限、トラッキング除去など安全策を実装していますが、外部入力取り扱いは常に慎重に行ってください。
- シグナル生成およびバックテストは研究/検証目的の実装です。実資金での運用時は十分な検証とリスク管理を行ってください。

---

## 参考（開発者向け）

- 主要 API:
  - kabusys.data.schema.init_schema(db_path)
  - kabusys.data.pipeline.run_prices_etl(...)
  - kabusys.data.news_collector.run_news_collection(...)
  - kabusys.strategy.build_features(conn, target_date)
  - kabusys.strategy.generate_signals(conn, target_date)
  - kabusys.backtest.engine.run_backtest(conn, start_date, end_date, ...)

---

ご不明点や README に追加したい具体的なコマンド/スクリーンショット・環境設定の例があれば教えてください。README をより運用向けに拡張できます。