KabuSys
=======

概要
----
KabuSys は日本株向けの自動売買・データ基盤・研究フレームワークです。  
DuckDB をデータストアとして用い、J-Quants API や RSS ニュースを取り込み、特徴量作成 → シグナル生成 → バックテスト といったワークフローを提供します。  
設計上、発注実行層（kabuステーション等）や本番資金を直接操作するモジュールと研究（research）モジュールは分離されており、ルックアヘッドバイアスを避けるため「対象日時点で利用可能なデータのみ」を使う方針で実装されています。

主な機能
--------
- データ取得・保存
  - J-Quants API クライアント（株価、財務、マーケットカレンダー） — レート制限・リトライ・トークンリフレッシュ対応
  - RSS ニュース収集（SSRF/サイズ上限対策、URL 正規化、銘柄抽出、冪等保存）
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- データ品質・ETL
  - 差分取得ベースの ETL パイプライン（バックフィル対応、品質チェック連携）
- 研究・特徴量
  - ファクター計算（Momentum / Volatility / Value / Liquidity）
  - 特徴量正規化（Z スコア）
  - 研究用の解析（Forward returns, IC, 統計サマリー）
- 戦略ロジック
  - 特徴量合成（feature_engineering.build_features）
  - シグナル生成（signal_generator.generate_signals） — 最終スコア算出、Bear レジーム抑制、BUY/SELL 判定、冪等な signals 書き込み
- バックテスト
  - ポートフォリオシミュレータ（スリッページ・手数料モデル、約定ロジック）
  - バックテストエンジン（DB をコピーしてインメモリで回す、日次ループ）
  - バックテスト用 CLI（python -m kabusys.backtest.run）
  - 評価指標（CAGR, Sharpe, Max Drawdown, Win rate, Payoff ratio）

動作環境・依存
--------------
- Python >= 3.10（型注釈に | 演算子を使用）
- 必要な主なパッケージ（例）:
  - duckdb
  - defusedxml
- 標準ライブラリの urllib 等を多用しているため外部 HTTP ライブラリは必須ではありませんが、環境に応じてインストールしてください。

環境変数
--------
自動で .env / .env.local をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。主に次の変数が利用されます:

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（execution 層用）
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意 / デフォルトあり
- KABUSYS_ENV — 開発モード等 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 環境作成（推奨: 仮想環境）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （任意）pip install -e . などパッケージ化している場合はプロジェクトのインストール
4. DuckDB スキーマ初期化
   - Python REPL から:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
   - ":memory:" を指定するとインメモリ DB が作成されます（テスト用）。
5. 環境変数を設定
   - プロジェクトルートに .env を作成（.env.example を参照して必要な値を設定）
   - 例（必須のみ）:
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
6. （オプション）J-Quants トークン取得や ETL を実行してデータを取得

使い方（代表的な例）
-------------------

- DuckDB スキーマ初期化（再掲）
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- J-Quants から株価取得 → 保存
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  records = fetch_daily_quotes(date_from=..., date_to=...)
  save_daily_quotes(conn, records)

- 特徴量作成（build_features）
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features
  conn = duckdb.connect("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024, 1, 31))
  print(f"features upserted: {n}")

- シグナル生成
  from datetime import date
  import duckdb
  from kabusys.strategy import generate_signals
  conn = duckdb.connect("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024, 1, 31))
  print(f"signals generated: {total}")

- バックテスト（CLI）
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db data/kabusys.duckdb

  主要オプション:
  - --start / --end : バックテスト期間
  - --cash : 初期資金（JPY）
  - --slippage / --commission : スリッページ・手数料率
  - --max-position-pct : 1銘柄あたりの最大比率
  - --db : DuckDB ファイルパス（必須）

- ETL の実行（例: 価格差分 ETL）
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_prices_etl
  conn = duckdb.connect("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  print(f"fetched={fetched} saved={saved}")

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数読み込み・設定管理（.env 自動ロード）
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py      — RSS 収集・前処理・DB 保存
  - schema.py              — DuckDB スキーマ定義と init_schema
  - stats.py               — 共通統計ユーティリティ（zscore_normalize等）
  - pipeline.py            — ETL パイプライン（差分取得／品質チェック）
- research/
  - __init__.py
  - factor_research.py     — ファクター計算（momentum/volatility/value）
  - feature_exploration.py — 研究用解析（forward returns / IC / summary）
- strategy/
  - __init__.py
  - feature_engineering.py — 特徴量作成 / 正規化・フィルタリング
  - signal_generator.py    — シグナル生成ロジック（final_score 計算、BUY/SELL）
- backtest/
  - __init__.py
  - engine.py              — バックテストエンジン（データコピー＆日次ループ）
  - simulator.py           — ポートフォリオシミュレータ（約定・時価評価）
  - metrics.py             — バックテスト評価指標計算
  - run.py                 — CLI エントリポイント（python -m kabusys.backtest.run）
  - clock.py               — 模擬時計（将来拡張用）
- execution/               — 発注・実行層（kabuステーション連携等の実装場所）
- monitoring/              — 監視・アラート周り（SQLite など）

設計上の注意点 / ベストプラクティス
-----------------------------------
- ルックアヘッドバイアス防止: 戦略・研究コードは target_date 時点で利用可能なデータのみを参照する設計です。過去日データを参照するときは注意してください。
- 冪等性: DB への挿入は ON CONFLICT / トランザクションで冪等化されるよう実装されています。ETL を複数回実行しても重複しないように設計されています。
- 環境変数の自動ロード: config.py はプロジェクトルート（.git または pyproject.toml を探索）から .env/.env.local を自動読み込みします。テスト時や特殊用途では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- テストとモック: ネットワークアクセス部分（RSS の _urlopen、J-Quants のリクエスト等）はモックしやすいように設計されています。

貢献
----
バグ報告・機能追加は Issue / Pull Request で歓迎します。コードスタイルやテストの追加は特に助かります。

ライセンス
---------
（本 README ではライセンス情報を記載していません。プロジェクトに合わせて LICENSE を追加してください。）

（この README はリポジトリ内のコードと docstring を元に自動生成的に作成しています。具体的な使用法や運用ルールはプロジェクトのドキュメント（DataPlatform.md, StrategyModel.md, BacktestFramework.md 等）があればそちらを優先してください。）