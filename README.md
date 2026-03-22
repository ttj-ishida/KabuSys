KabuSys — 日本株自動売買システム (README)
=========================================

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買システムのコアライブラリです。  
データ取得（J‑Quants 等）、データ加工（DuckDB スキーマ・ETL）、特徴量生成、シグナル生成、バックテスト、ニュース収集までの主要コンポーネントを備え、戦略開発や検証に必要な基盤処理を提供します。  
設計上のポイントは以下です：
- ルックアヘッドバイアスを防ぐデータ設計（fetched_at や日付制約）
- DuckDB を利用したローカル DB（軽量かつ高速な列指向 DB）
- 冪等性（DB 保存は ON CONFLICT で上書き等）
- テストしやすい設計（関数に接続やトークンを注入可能）

機能一覧
--------
- データ取得 / 保存
  - J‑Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - RSS ベースのニュース収集（SSRF対策、トラッキング除去、記事→銘柄紐付け）
  - DuckDB スキーマ定義・初期化（init_schema）
- データ加工 / ETL
  - 差分更新を考慮した ETL パイプライン（run_prices_etl 等）
  - 品質チェックフレームワークとの連携（quality モジュール想定）
- 研究・特徴量
  - ファクター計算（モメンタム / ボラティリティ / バリュー等）
  - クロスセクション Z スコア正規化
  - ファクター探索用ユーティリティ（Forward returns / IC / summary）
- 戦略
  - 特徴量生成（build_features）
  - シグナル生成（generate_signals） — 複数コンポーネントを重み付けして final_score を算出、BUY/SELL を生成
- バックテスト
  - ポートフォリオシミュレータ（スリッページ・手数料モデル対応）
  - バックテスト実行エンジン（run_backtest）
  - 評価指標計算（CAGR, Sharpe, MaxDD, Win rate, Payoff ratio）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- 実行・監視（パッケージ内に名前空間を準備。発注等は execution 層で拡張）

セットアップ手順
--------------
前提
- Python 3.10 以上を推奨（型アノテーションや union 型（|）を利用）
- Git, ネットワーク接続（J‑Quants や RSS へアクセスする場合）

簡易セットアップ
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境の作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （実運用では他に requests 等を追加する場合あり。requirements.txt があればそちらを使用してください）
4. DuckDB ファイル初期化（例）
   - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

環境変数
- 自動的にプロジェクトルートの .env / .env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- 主な必須環境変数（.env に設定）
  - JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン
  - KABU_API_PASSWORD: kabu API 用パスワード（execution 層を使う場合）
  - SLACK_BOT_TOKEN: Slack 通知用トークン
  - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- データベースパス（任意）
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視用 DB 等、デフォルト: data/monitoring.db)
- 実行環境指定
  - KABUSYS_ENV: development / paper_trading / live
- ログレベル
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

使い方（代表例）
----------------

1) DuckDB スキーマ初期化
- 初回はテーブルを作る必要があります。
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")
  - conn.close()

2) J‑Quants からデータ取得 → 保存（例）
- from kabusys.data import jquants_client as jq
- data = jq.fetch_daily_quotes(date_from=..., date_to=...)
- conn = init_schema("data/kabusys.duckdb")
- jq.save_daily_quotes(conn, data)

3) ETL（差分）パイプライン
- from kabusys.data.pipeline import run_prices_etl, ETLResult
- result = run_prices_etl(conn, target_date=date.today())
- result.to_dict() で実行結果の要約が取得可能

4) 特徴量構築
- from kabusys.strategy import build_features
- from kabusys.data.schema import init_schema
- conn = init_schema("data/kabusys.duckdb")
- build_features(conn, target_date=date(2024,1,1))

5) シグナル生成
- from kabusys.strategy import generate_signals
- generate_signals(conn, target_date=date(2024,1,1), threshold=0.6)

6) バックテスト（CLI）
- python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb
  - 主要オプション: --cash, --slippage, --commission, --max-position-pct

7) ニュース収集（RSS）
- from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
- conn = init_schema("data/kabusys.duckdb")
- run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set_of_codes)

API（ライブラリ利用例）
- DuckDB 接続 + 機能呼び出しは次のように簡単に行えます：
  - from kabusys.data.schema import init_schema
  - from kabusys.strategy import build_features
  - conn = init_schema("data/kabusys.duckdb")
  - build_features(conn, target_date)
  - conn.close()

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュールとその役割の概要です。

- __init__.py
  - パッケージのトップレベル宣言（version 等）

- config.py
  - 環境変数読み込み・検証（.env 自動ロード、必須キーチェック、環境判定）

- data/
  - jquants_client.py — J‑Quants API クライアント（fetch / save / rate limiting / retry / token refresh）
  - news_collector.py — RSS 取得・前処理・raw_news 保存・銘柄抽出
  - pipeline.py — ETL 差分処理フロー（run_prices_etl 等）
  - schema.py — DuckDB スキーマ定義・初期化（init_schema）
  - stats.py — zscore_normalize 等の統計ユーティリティ

- research/
  - factor_research.py — momentum / volatility / value 等のファクター計算（prices_daily/raw_financials を参照）
  - feature_exploration.py — forward returns / IC / factor summary（研究用ユーティリティ）

- strategy/
  - feature_engineering.py — 生ファクターの統合・Zスコア正規化・features テーブルへの保存
  - signal_generator.py — features と ai_scores を統合して final_score を計算、BUY/SELL を生成

- backtest/
  - engine.py — run_backtest（本番 DB からインメモリへコピーして日次ループを実行）
  - simulator.py — PortfolioSimulator（約定ロジック、mark_to_market、TradeRecord/ snapshot）
  - metrics.py — バックテスト評価指標計算
  - run.py — CLI エントリポイント

- execution/
  - （発注・実行に関する実装を配置するための名前空間）

- monitoring/
  - （監視・通知周りの実装を配置するための名前空間）

注意事項 / 運用上のヒント
------------------------
- データ整合性: DuckDB のスキーマは多くの CHECK/NOT NULL を設定しているため、ETL では欠損・不正値の検出に注意してください。
- 冪等性: save_* 系関数は ON CONFLICT を利用しているため、再実行しても安全なことが想定されています。ただしスキーマ変更や後方互換性に注意。
- 認証情報: トークン等は .env ファイルに保存する場合、アクセス権限を適切に管理してください。
- テスト: モジュールは接続や ID トークンを注入できる設計です。単体テストではモック注入を活用してください（例: news_collector._urlopen の差し替え等）。

ライセンス / 貢献
-----------------
（プロジェクトのライセンス・貢献ルールをここに記載してください）

最後に
-------
この README はコードベースの主要部分に基づく導入ドキュメントです。詳細な設計仕様（StrategyModel.md, DataPlatform.md, BacktestFramework.md など）が別途ある前提で作られています。実運用・デプロイ前に設定値、API レート制限、取引ルール（kabu API）等の追加確認を行ってください。