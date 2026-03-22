# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォームです。J-Quants から市場データ・財務データ・カレンダー・ニュースを収集し、DuckDB 上で加工・特徴量生成・シグナル生成・バックテスト・シミュレーションを行うことを目的としたモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（計算は target_date 時点のデータのみを使用）
- DuckDB を中心とした軽量なデータレイヤ
- ETL/研究/戦略/実行/バックテストの分離
- 冪等性（DB への保存は ON CONFLICT 等で上書き・スキップ）

---

## 主要機能（機能一覧）

- データ収集
  - J-Quants API クライアント（株価、財務、マーケットカレンダー）
  - RSS ベースのニュース収集（重複排除・記事正規化・銘柄抽出）
- データ基盤
  - DuckDB スキーマ定義と初期化（init_schema）
  - ETL パイプライン（差分取得、品質チェックを想定）
- 研究・特徴量
  - ファクター計算（モメンタム/バリュー/ボラティリティ/流動性）
  - クロスセクション Z スコア正規化ユーティリティ
  - ファクター探索（将来リターン計算、IC、統計サマリー）
- 戦略
  - 特徴量合成（features テーブルへ保存）
  - シグナル生成（ai_scores を併用し final_score に基づく BUY/SELL 判定）
- バックテスト
  - 日次シミュレータ（スリッページ・手数料モデル）
  - バックテストエンジン（generate_signals と組合せた日次ループ）
  - メトリクス計算（CAGR、Sharpe、Max Drawdown、勝率等）
  - CLI 実行エントリポイント（python -m kabusys.backtest.run）
- 実行層（骨組み）
  - signals / orders / trades / positions 等のスキーマ定義（発注フローの下地）

---

## 必要環境

- Python 3.10+（typing の一部記法が使用されています）
- パッケージ（例）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API、RSS フィード取得のため）

実際のプロジェクトでは pyproject.toml / requirements.txt を用意してください（本リポジトリはコードのみを示します）。

---

## セットアップ手順

1. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトに requirements を用意している場合は `pip install -r requirements.txt`）

3. パッケージを開発モードでインストール（任意）
   - pip install -e .

4. DuckDB スキーマ初期化
   - Python REPL で:
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")
   - またはスクリプト内で同関数を呼び出して DB を作成します。
   - デフォルトのファイルパスは settings.duckdb_path（デフォルト "data/kabusys.duckdb"）。

---

## 環境変数（.env）

設定値は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。

主要な環境変数（Settings）:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン（fetch / token refresh に使用）
- KABU_API_PASSWORD (必須)
  - kabuステーション API パスワード（発注用）
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意, デフォルト: development)
  - 有効値: development | paper_trading | live
- LOG_LEVEL (任意, デフォルト: INFO)
  - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

例（.env）
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG

---

## 使い方（基本的な例）

以下は主要な操作の簡単な使い方例です。

- DuckDB スキーマ初期化（簡単なワンライナー）
  python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

- J-Quants から日足を取得して保存（概念）
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema
  conn = init_schema('data/kabusys.duckdb')
  records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  jq.save_daily_quotes(conn, records)
  conn.close()

- ニュース収集（RSS → raw_news）
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema
  conn = init_schema('data/kabusys.duckdb')
  known_codes = {'7203', '6758', ...}  # 任意。銘柄紐付けに使用
  run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  conn.close()

- 特徴量ビルド（features テーブルに書き込む）
  from kabusys.strategy import build_features
  from kabusys.data.schema import init_schema
  from datetime import date
  conn = init_schema('data/kabusys.duckdb')
  n = build_features(conn, target_date=date(2024, 1, 31))
  conn.close()
  print(f"features updated: {n}")

- シグナル生成（signals テーブルに書き込む）
  from kabusys.strategy import generate_signals
  conn = init_schema('data/kabusys.duckdb')
  total = generate_signals(conn, target_date=date(2024,1,31), threshold=0.6)
  conn.close()
  print(f"signals written: {total}")

- バックテスト（CLI）
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db data/kabusys.duckdb

  上の CLI は DB に事前に prices_daily, features, ai_scores, market_regime, market_calendar が用意されている必要があります。

- バックテスト（Python API）
  from kabusys.backtest.engine import run_backtest
  from kabusys.data.schema import init_schema
  conn = init_schema('data/kabusys.duckdb')
  result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
  # result.history / result.trades / result.metrics を参照
  conn.close()

---

## 注意点・運用メモ

- 自動環境変数読み込みは .git または pyproject.toml があるプロジェクトルートを探索して行われます。CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを止められます。
- J-Quants API のレート制限（120 req/min）・リトライロジック・トークン自動リフレッシュが組み込まれています。
- NewsCollector では SSRF や XML Bomb 対策（defusedxml、リダイレクト検査、受信サイズ上限）を実装しています。
- DuckDB のスキーマは init_schema() で一括初期化できます。既存テーブルは保持されるように冪等的に作成されます。
- 実運用（live）モードでは設定・API キーの管理に特に注意してください（KABUSYS_ENV=is_live の挙動分岐あり）。

---

## ディレクトリ構成（概要）

以下は src/kabusys 配下の主要ファイルと役割（抜粋）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数設定管理（Settings）
  - data/
    - __init__.py
    - schema.py           : DuckDB スキーマ定義と init_schema
    - jquants_client.py   : J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py   : RSS 取得・記事保存・銘柄抽出
    - pipeline.py         : ETL パイプライン（差分更新、品質チェックの想定）
    - stats.py            : zscore_normalize 等の共通統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py  : mom/value/volatility 等のファクター計算
    - feature_exploration.py : 将来リターン計算、IC、サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py : features の構築（正規化・フィルタ）
    - signal_generator.py    : final_score 計算と BUY/SELL の生成
  - backtest/
    - __init__.py
    - engine.py            : run_backtest（バックテスト全体ループ）
    - simulator.py         : PortfolioSimulator, 約定ロジック
    - metrics.py           : バックテスト評価指標計算
    - run.py               : CLI エントリポイント
    - clock.py             : 模擬時計（将来拡張用）
  - execution/             : 発注/監視用モジュール群（骨組み）
  - monitoring/            : 監視・メトリクス収集用（骨組み）

（README に記載した以外にも補助モジュールが含まれます。上は主要な公開 API と責務の一覧です。）

---

## 開発・貢献

- リポジトリにテスト・CI を追加することを推奨します。特に ETL・API クライアント・RSS のネットワーク処理はモック化したユニットテストが重要です。
- 実際の取引に接続する際は「paper_trading」モードで挙動を確認した上で、アクセス制御・ログ管理・監査を徹底してください。

---

必要であれば、README に具体的なコマンド例（.env.example、CI 用のセットアップ手順、Docker イメージ化手順など）を追記します。どの部分を詳細化したいか教えてください。