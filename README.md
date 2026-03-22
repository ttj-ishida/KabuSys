KabuSys
=======

日本株向けの自動売買 / 研究プラットフォームのモジュール群です。  
DuckDB をデータレイクとして用い、データ収集（J-Quants）、特徴量作成、シグナル生成、バックテスト、ニュース収集などをワンパッケージで提供します。

主な特長
--------
- DuckDB ベースのスキーマ定義・初期化機能（冪等）
- J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
- ETL パイプライン（差分取得・バックフィル、品質チェック）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 特徴量エンジニアリング（Z スコア正規化、ユニバースフィルタ）
- シグナル生成（ファクター + AI スコア統合、BUY/SELL 判定）
- バックテストフレームワーク（擬似約定、スリッページ・手数料モデル、評価指標）
- ニュース収集（RSS 収集、記事正規化、銘柄抽出、DB 保存）
- 設定は環境変数 / .env で管理（自動ロード機能あり）

必要条件
--------
- Python 3.10+
- duckdb
- defusedxml

（上記以外に運用時は J-Quants のリフレッシュトークンや kabu API の認証情報などが必要になります）

セットアップ
-----------
1. 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要なパッケージをインストール
   ```
   pip install duckdb defusedxml
   ```
   - プロジェクトをパッケージとして配布している場合は `pip install -e .` 等でインストールしてください。

3. DuckDB スキーマを初期化（例: data/kabusys.duckdb を作成）
   ```py
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")
   ```
   または CLI から:
   ```
   python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   ```

環境変数 / 設定
----------------
パッケージ起動時にプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動読み込みします。自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須（Settings で参照される主要環境変数）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API のパスワード
- SLACK_BOT_TOKEN       : Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID      : Slack チャンネル ID

オプション（デフォルトあり）
- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL : DEBUG/INFO/...（デフォルト: INFO）
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）

基本的な使い方
--------------

1) DuckDB 接続の作成
```py
from kabusys.data.schema import init_schema, get_connection

# 新規 DB を初期化
conn = init_schema("data/kabusys.duckdb")

# 既存 DB へ接続（スキーマ初期化は行わない）
# conn = get_connection("data/kabusys.duckdb")
```

2) J-Quants からデータ取得 (例)
```py
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

3) ETL（差分更新）モジュールの利用例
```py
from kabusys.data.pipeline import run_prices_etl
# run_prices_etl(conn, target_date, id_token=None, date_from=None, backfill_days=3)
```
（pipeline モジュールは差分取得・保存・品質チェックを統合した高レベル関数群を提供します）

4) 特徴量作成
```py
from datetime import date
from kabusys.strategy import build_features
# conn は DuckDB 接続
n = build_features(conn, target_date=date(2024,1,31))
```

5) シグナル生成
```py
from kabusys.strategy import generate_signals
count = generate_signals(conn, target_date=date(2024,1,31))
```

6) バックテスト（提供されている CLI 例）
```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2024-12-31 \
  --cash 10000000 --db data/kabusys.duckdb
```
内部ではデータを in-memory の DuckDB にコピーして日次ループでシミュレーションを実行します（擬似約定・スリッページ・手数料等を適用）。

主要モジュール / API まとめ
-------------------------
- kabusys.config
  - settings: 環境変数読み取り用（必須変数のバリデーションを含む）
- kabusys.data
  - schema.init_schema(db_path) / get_connection: DB スキーマ初期化・接続
  - jquants_client: J-Quants API クライアント、fetch_* / save_* 関数
  - pipeline: ETL ワークフロー（run_prices_etl 等）
  - news_collector: RSS 取得・DB 保存、extract_stock_codes
  - stats.zscore_normalize: 正規化ユーティリティ
- kabusys.research
  - calc_momentum / calc_volatility / calc_value: ファクター計算
  - calc_forward_returns / calc_ic / factor_summary: 研究用解析関数
- kabusys.strategy
  - build_features(conn, target_date): features テーブル作成（Z スコア正規化・ユニバースフィルタ）
  - generate_signals(conn, target_date, ...): signals の生成（BUY/SELL）
- kabusys.backtest
  - run_backtest(conn, start_date, end_date, ...): バックテスト実行
  - backtest.simulator.PortfolioSimulator: 擬似約定ロジック
  - backtest.metrics.calc_metrics: バックテスト評価指標計算
  - backtest.run: CLI エントリポイント

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py                    — パッケージ定義
- config.py                      — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py             — J-Quants API クライアント + 保存関数
  - news_collector.py             — RSS 取得・記事抽出・保存
  - schema.py                     — DuckDB スキーマ定義・初期化
  - pipeline.py                   — ETL パイプライン
  - stats.py                      — Z スコア等の統計ユーティリティ
- research/
  - __init__.py
  - factor_research.py            — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py        — 将来リターン / IC / サマリー
- strategy/
  - __init__.py
  - feature_engineering.py        — features テーブル作成
  - signal_generator.py           — final_score 計算・シグナル生成
- backtest/
  - __init__.py
  - engine.py                     — バックテストエンジン（run_backtest）
  - simulator.py                  — 擬似約定・ポートフォリオ管理
  - metrics.py                    — 評価指標計算
  - run.py                        — CLI ラッパー
- data/pipeline.py, data/jquants_client.py, ...（上記参照）

運用上の注意 / 補足
------------------
- Settings は必須の環境変数が未設定の場合に ValueError を投げます。デプロイ前に .env を作成するか、環境変数を設定してください。
- jquants_client は API レート制限やリトライ、401 のトークンリフレッシュを実装しています。大量取得時は RateLimiter の挙動に注意してください（120 req/min）。
- ニュース収集は SSRF 対策、受信サイズ制限、XML パースの安全化（defusedxml）などを実装しています。
- バックテストは本番 DB を汚染しないように in-memory にデータをコピーして実行しますが、事前に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）を用意しておく必要があります。
- ユニットテストや CI 実行時には KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると .env の自動読み込みを抑制できます。

貢献
----
バグ報告・機能要望・プルリクエスト歓迎です。プロジェクトルートに CONTRIBUTING.md や issue テンプレートがあればそちらに従ってください。

ライセンス
---------
プロジェクトに付随するライセンスファイルをご確認ください（ここでは指定していません）。

以上が主要な README 内容です。必要であれば、README にサンプルワークフロー（ETL → build_features → generate_signals → run_backtest）や .env.example のテンプレート、よくあるトラブルシューティングを追加できます。どの追加情報が必要か教えてください。