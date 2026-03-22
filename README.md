README
======

概要
----
KabuSys は日本株向けの自動売買／データプラットフォームのライブラリです。本プロジェクトは次の層を備えています。

- データ取得・加工（J-Quants API からの株価・財務データ取得、RSS ニュース収集）
- データベーススキーマ（DuckDB）定義・初期化
- リサーチ用ファクター計算・特徴量生成
- シグナル生成（スコア統合・BUY/SELL 判定）
- バックテストフレームワーク（シミュレータ・メトリクス）
- ETL パイプライン・品質チェック（差分更新・バックフィル対応）

設計方針としては「ルックアヘッドバイアス回避」「冪等性」「明示的な依存の分離」「DB への日付単位置換（トランザクション）」を重視しています。

主な機能
--------
- J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
- DuckDB スキーマの初期化・接続ヘルパー（init_schema / get_connection）
- 生データ保存（raw_prices / raw_financials / raw_news 等）と冪等保存関数
- RSS からのニュース収集（トラッキングパラメータ除去・SSRF 対策・gzip・XML 安全パーシング）
- リサーチ: モメンタム・ボラティリティ・バリューなどのファクター計算
- 特徴量エンジニアリング: 正規化（Z スコア）・ユニバースフィルタ・features テーブルへの UPSERT
- シグナル生成: 各要素スコアの重み付け統合、Bear レジーム抑制、BUY/SELL の冪等書き込み
- バックテスト: 日次ループによる擬似約定（スリッページ・手数料モデル）、パフォーマンス指標（CAGR, Sharpe, MaxDD 等）
- ETL パイプライン: 差分取得・バックフィル・品質チェック・市場カレンダー先読み

システム要件
------------
- Python 3.10 以上（型注釈に | を使っているため）
- 必須パッケージ（代表例）:
  - duckdb
  - defusedxml

（上記は最低限。プロジェクトを拡張している場合は追加ライブラリが必要となる可能性があります）

環境変数（主なもの）
-------------------
README に合わせた主要な環境変数は以下の通りです（config.Settings 参照）。

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN       : Slack ボットトークン（必須）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL             : ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）

自動で .env / .env.local をロードします。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

セットアップ手順
----------------
1. リポジトリをクローンする
   - git clone <repo-url>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

4. パッケージとしてインストール（任意、開発用）
   - pip install -e .

5. 環境変数を設定
   - プロジェクトルートに .env または .env.local を作成
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

6. DuckDB スキーマを初期化
   - Python REPL / スクリプト内で:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()

使い方（よく使う操作例）
-----------------------

DB 初期化（1 回）
- 例:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  conn.close()

J-Quants からデータ取得して保存（簡易例）
- 価格データ取得 → raw_prices に保存:
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  jq.save_daily_quotes(conn, records)
  conn.close()

RSS ニュース収集ジョブ実行（ニュースの収集と銘柄紐付け）
- 例:
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203","6758", ...}  # 有効な銘柄コードセット
  run_news_collection(conn, known_codes=known_codes)
  conn.close()

特徴量生成（features テーブル作成）
- 例:
  import duckdb
  from kabusys.strategy import build_features
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2024,1,31))
  conn.close()

シグナル生成（signals テーブル作成）
- 例:
  import duckdb
  from kabusys.strategy import generate_signals
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024,1,31))
  conn.close()

バックテスト（CLI）
- モジュール実行形式で簡単にバックテストが可能:
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2024-12-31 \
    --cash 10000000 --db data/kabusys.duckdb

- 上記は内包の run_backtest を呼び、DuckDB のデータをインメモリにコピーして日次シミュレーションを実行します。
- 戻り値として履歴・トレード・各種メトリクスが得られます（CLI 実行時は要約が stdout に出力されます）。

軽量 API 例（Python スクリプト内でのバックテスト）
- 例:
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest
  from datetime import date
  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  conn.close()
  print(result.metrics)

注意点 / 運用メモ
-----------------
- ファクター計算・特徴量生成・シグナル生成は「target_date 時点で利用可能なデータのみ」を前提として実装されています（ルックアヘッドバイアス対策）。
- raw データの保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）となっているため、差分取得・再実行に適しています。
- News collector は SS RF 対策・XML の安全パース・コンテンツ上限などの防御を備えています。
- config モジュールはプロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動読み込みします。テストで自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

主要ディレクトリ構成
-------------------
(抜粋: src/kabusys 以下)

- kabusys/
  - __init__.py                         : パッケージ定義（version 等）
  - config.py                           : 環境変数 / 設定管理（.env 自動読み込み、Settings）
  - data/
    - __init__.py
    - jquants_client.py                  : J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py                  : RSS ニュース収集 / 前処理 / DB 保存
    - pipeline.py                        : ETL 差分更新ロジック（バックフィル・品質チェック）
    - schema.py                          : DuckDB スキーマ定義・初期化（init_schema）
    - stats.py                           : zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py                 : momentum / volatility / value ファクター計算
    - feature_exploration.py             : forward returns / IC / summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py             : features 作成（正規化・ユニバースフィルタ）
    - signal_generator.py                : final_score 計算・BUY/SELL 生成
  - backtest/
    - __init__.py
    - engine.py                          : run_backtest（DB コピー + 日次ループ）
    - simulator.py                       : PortfolioSimulator（擬似約定・履歴管理）
    - metrics.py                         : バックテスト評価指標計算
    - run.py                             : CLI エントリポイント
    - clock.py                           : SimulatedClock（将来拡張用）
  - execution/                           : 発注関連（空の __init__ 等、実装箇所あり）
  - monitoring/                          : 監視・アラートロジック（別途実装想定）
  - その他: tests/（無ければ追加）など

貢献
----
バグ報告・機能改善のプルリクエスト歓迎します。変更を加える際はテストを追加し、既存の設計方針（ルックアヘッド回避・冪等性）への影響を考慮してください。

補足
----
この README はコードベースの実装から抜粋して要点をまとめたものです。詳細な仕様（StrategyModel.md, DataPlatform.md, BacktestFramework.md 等）が存在する想定のため、実運用前にはそれら設計ドキュメントも参照してください。