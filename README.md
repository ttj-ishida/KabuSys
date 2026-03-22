KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買基盤のプロトタイプ実装です。  
主な目的はデータ取得（J-Quants）、ETL、特徴量作成、シグナル生成、バックテスト、ニュース収集までのワークフローを一貫して提供することです。  
設計は以下の点を重視しています。

- ルックアヘッドバイアスの排除（target_date 時点のデータのみ使用）
- DuckDB を用いた軽量で高速なローカルデータ管理
- 冪等性（INSERT ... ON CONFLICT 等で重複挿入を抑止）
- ネットワーク安全性（RSS の SSRF 対策等）
- テスト容易性（id_token 注入やインメモリ DB 対応）

主な機能
--------
- データ取得 / 保存
  - J-Quants API クライアント（株価、財務、マーケットカレンダー）
  - 差分 ETL パイプライン（backfill を考慮）
  - DuckDB スキーマ定義 / 初期化（init_schema）
- データ処理 / 特徴量
  - ファクター計算（Momentum / Volatility / Value）
  - クロスセクション Z スコア正規化
  - features テーブルへの書き出し（冪等）
- シグナル生成
  - features と AI スコアを統合して final_score を算出
  - Bear レジーム抑制、BUY/SELL 判定、signals テーブルへの書き込み（冪等）
- ニュース収集
  - RSS フィードの収集・前処理・記事保存（raw_news）
  - 記事ID の正規化（URL 正規化 → SHA-256 の先頭 32 文字）
  - 銘柄コード抽出と news_symbols への紐付け
- バックテスト
  - PortfolioSimulator による擬似約定（スリッページ・手数料モデル）
  - run_backtest() による日次ループ、ポジション管理、シグナル適用
  - バックテスト指標算出（CAGR, Sharpe, MaxDrawdown, WinRate, Payoff 等）
  - CLI エントリポイント: python -m kabusys.backtest.run
- その他
  - 設定管理（環境変数/.env の自動ロード）
  - DB 品質チェック（パイプラインで quality モジュールを参照）

セットアップ手順
----------------
前提
- Python 3.10 以上（PEP 604 の union 型（|）を利用）
- Git, インターネット接続（J-Quants API 使用時）

1. リポジトリをクローン
   - git clone <repo_url>
   - cd <repo_root>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール
   本プロジェクトでは最小限の外部依存のみ使用しています：
   - duckdb（データベース）
   - defusedxml（安全な XML パース、RSS）
   例:
   - pip install duckdb defusedxml

   （パッケージを requirements.txt にまとめている場合は pip install -r requirements.txt を使用してください）

4. パッケージをインストール / 開発モード
   - pip install -e .

5. 環境変数（.env）を作成
   プロジェクトルートに .env または .env.local を配置すると自動で読み込まれます（デフォルト）。
   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_api_password
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意
   - SLACK_BOT_TOKEN=your_slack_bot_token
   - SLACK_CHANNEL_ID=your_slack_channel_id
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...
   自動ロードを無効化する場合:
   - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

6. DuckDB スキーマ初期化
   Python REPL かスクリプトから:
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()

使い方
------
以下は代表的な操作例です。

1. J-Quants から株価を取得して DB に保存（概念）
   from datetime import date
   from kabusys.data import jquants_client as jq
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
   jq.save_daily_quotes(conn, records)
   conn.close()

2. ETL パイプライン（差分更新）
   from datetime import date
   import duckdb
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_prices_etl

   conn = init_schema("data/kabusys.duckdb")
   # target_date は通常今日の営業日
   etl_result = run_prices_etl(conn, target_date=date.today())
   conn.close()
   # ETLResult を確認
   print(etl_result.to_dict())

3. 特徴量作成
   from datetime import date
   import duckdb
   from kabusys.strategy import build_features

   conn = init_schema("data/kabusys.duckdb")
   count = build_features(conn, target_date=date(2024,12,31))
   conn.close()
   print(f"features upserted: {count}")

4. シグナル生成
   from datetime import date
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   total = generate_signals(conn, target_date=date(2024,12,31))
   conn.close()
   print(f"signals written: {total}")

5. バックテスト（CLI）
   python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --cash 10000000 --db data/kabusys.duckdb

   あるいは Python API:
   from datetime import date
   from kabusys.backtest.engine import run_backtest
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   result = run_backtest(conn, start_date=date(2023,1,4), end_date=date(2023,12,29))
   conn.close()
   print(result.metrics)

6. ニュース収集
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   results = run_news_collection(conn, known_codes={"7203","6758",...})
   conn.close()
   print(results)

設定と環境変数
----------------
設定は kabusys.config.Settings 経由で取得されます（環境変数または .env ファイル）。  
重要なキー（未設定時はエラー）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

その他はデフォルト値があるかオプションです（duckdb ファイルパス等）。

ディレクトリ構成
----------------
主要なソースツリー（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                      # 環境変数/.env の読み込みと Settings
  - data/
    - __init__.py
    - jquants_client.py            # J-Quants API クライアント（取得 + 保存）
    - news_collector.py            # RSS ニュース収集と DB 保存
    - pipeline.py                  # ETL パイプライン（差分取得等）
    - schema.py                    # DuckDB スキーマ定義と init_schema()
    - stats.py                     # zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py           # momentum/value/volatility の計算
    - feature_exploration.py       # 将来リターン・IC・統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py       # features 作成（build_features）
    - signal_generator.py          # generate_signals（BUY/SELL 判定）
  - backtest/
    - __init__.py
    - engine.py                    # run_backtest、バックテストループ
    - simulator.py                 # PortfolioSimulator（擬似約定）
    - metrics.py                   # バックテスト評価指標計算
    - clock.py                     # SimulatedClock（将来拡張用）
    - run.py                       # CLI エントリポイント
  - execution/
    - __init__.py                  # 発注/実行層は分離（実装はここに拡張）
  - monitoring/                     # 監視・アラート用モジュール（拡張想定）
  - その他のユーティリティモジュール...

注意・開発メモ
--------------
- DuckDB を使用してローカルにデータを蓄積します。init_schema() は必要なテーブルをすべて作成します。
- J-Quants API の呼び出しはレート制限やリトライ処理を内包しています。API レスポンスの形式変更等に注意してください。
- RSS フェッチは SSRF 対策や受信サイズ制限を行っていますが、信頼できる RSS ソースを指定してください。
- 実運用（ライブ取引）で使用する前に、paper_trading 環境で十分な検証を行ってください（設定 KABUSYS_ENV）。
- 本リポジトリは発注層（execution）やモニタリング、Slack通知などの統合が想定されていますが、実環境での発注 API 連携は慎重に実装してください。

ライセンス / コントリビューション
----------------------------------
（本テンプレートにライセンス情報は含まれていません。適切な LICENSE ファイルを追加してください）

補足
----
- 質問や拡張（例: ブローカー API の追加、AI スコアリング統合、Web ダッシュボードなど）については具体例を提示いただければ README に追記できます。