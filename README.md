# KabuSys

日本株向けの自動売買システム用ライブラリ（バックテスト・データパイプライン・特徴量/シグナル生成など）。

このリポジトリは、データ収集（J-Quants）、データ整形・スキーマ管理（DuckDB）、リサーチ用のファクター計算、特徴量正規化、シグナル生成、バックテストエンジン、ニュース収集などを含むモジュール群で構成されています。

---

## 特徴（機能一覧）

- データ収集
  - J-Quants API クライアント（株価日足・財務データ・市場カレンダー）
  - RSS ベースのニュース収集（トラッキングパラメータ除去、SSRF対策、gzip/サイズ制限）
- データ基盤
  - DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
  - ETL パイプライン（差分取得、バックフィル、品質チェック）
- リサーチ / ファクター
  - Momentum / Volatility / Value ファクター計算（prices_daily / raw_financials）
  - 将来リターン計算、IC（Spearman）や統計サマリー
  - Zスコア正規化ユーティリティ
- 戦略（Strategy）
  - 特徴量作成（正規化・ユニバースフィルタ・クリッピング） -> features テーブルへ保存
  - シグナル生成（ファクター・AIスコア統合、Bear フィルタ、BUY/SELL 判定） -> signals テーブルへ保存
- バックテスト
  - 日次ループベースのバックテストエンジン（擬似約定、スリッページ・手数料モデル、ポジション管理）
  - パフォーマンス指標計算（CAGR、Sharpe、Max Drawdown、勝率、Payoff Ratio）
  - CLI 実行エントリポイント（python -m kabusys.backtest.run）
- ユーティリティ
  - 設定管理（.env 読み込み、自動ロード）
  - ログレベル・環境モード（development / paper_trading / live）

---

## 必要条件・依存パッケージ

主に標準ライブラリで実装されていますが、以下が必要です：

- Python 3.10 以上（型アノテーションの union 演算子（A | B）を使用）
- 外部パッケージ（最低限）:
  - duckdb
  - defusedxml

インストール例（仮に requirements.txt があれば）:
```
pip install duckdb defusedxml
```

プロジェクトに requirements ファイルがある場合はそれを利用してください。

---

## 環境変数（設定）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

主な環境変数:

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須)
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (省略時: http://localhost:18080/kabusapi)
- Slack 通知
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- DB パス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
- システム
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

コード内の `kabusys.config.settings` 経由で取得できます。必須値がない場合は起動時に ValueError が発生します。

---

## セットアップ手順（ローカルでの最小セットアップ）

1. リポジトリをクローン・チェックアウト
2. 仮想環境を作成して依存をインストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   ```
3. `.env` を作成（`.env.example` を参照して必要な環境変数を設定）
   - 最低限 JQUANTS_REFRESH_TOKEN / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID / KABU_API_PASSWORD を設定
4. DuckDB スキーマの初期化（Python REPL またはスクリプトで）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```
   - `db_path` に `:memory:` を渡すとインメモリ DB になります
5. （任意）J-Quants トークンや API を用いてデータ収集・ETL を実行

---

## 使い方（主要な実行例）

- DuckDB スキーマ初期化（プログラム例）
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  # 以降 conn を使って ETL / シグナル生成 / バックテスト等を実行
  conn.close()
  ```

- J-Quants から日次株価を取得して保存（概念例）
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  saved = jq.save_daily_quotes(conn, records)
  conn.close()
  ```

- ETL パイプラインの実行（パイプライン関数例）
  - パイプラインモジュールは差分取得や品質チェックを行います。典型的には以下のように呼び出します（実際の関数シグネチャはモジュール内を参照してください）。
  ```python
  from kabusys.data.pipeline import run_prices_etl
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  prices_fetched, prices_saved = run_prices_etl(conn, target_date=..., id_token=None)
  conn.close()
  ```

- シグナル生成（戦略）
  ```python
  from kabusys.strategy import build_features, generate_signals
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # features を構築
  build_features(conn, target_date=...)
  # signals を生成
  generate_signals(conn, target_date=...)
  conn.close()
  ```

- バックテスト CLI
  ```
  python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2023-12-31 \
      --cash 10000000 --db data/kabusys.duckdb
  ```
  オプション:
  - --slippage（デフォルト 0.001）
  - --commission（デフォルト 0.00055）
  - --max-position-pct（デフォルト 0.20）

- プログラムからバックテストを呼ぶ
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest

  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=..., end_date=..., initial_cash=10_000_000)
  print(result.metrics)
  conn.close()
  ```

---

## 注意点 / 実装上のポイント

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）から行われます。テストや明示的制御が必要な場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants クライアントは内部で固定間隔のレートリミッタ、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ等を実装しています。
- News Collector は SSRF 対策・レスポンスサイズ制限・gzip 対応・トラッキングパラメータ除去など堅牢性を考慮しています。
- DuckDB スキーマ初期化は冪等（既存テーブルは上書きしない）。`:memory:` を使ってバックテスト用にインメモリ DB を構築します。
- 戦略モジュールはルックアヘッドバイアス防止のため target_date 時点のデータのみを参照する設計です。
- いくつかの仕様（例: トレーリングストップ、時間決済）は実装注釈として保留されています（コード中にコメントあり）。

---

## ディレクトリ構成（主要ファイル）

以下は主要モジュールの一覧（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - backtest/
    - __init__.py
    - engine.py
    - simulator.py
    - metrics.py
    - clock.py
    - run.py
  - execution/
    - __init__.py
  - monitoring/  (実装ファイルは別途配置)

（上記はリポジトリの主要ファイル/モジュールを抜粋したものです。詳しい内部ドキュメントは各モジュールの docstring を参照してください。）

---

## 開発者向け情報

- ローカルでの単体テストやモックを使った検証がしやすいように、API トークンなどは関数引数で注入可能になっています（例: jquants_client の id_token 引数など）。
- DuckDB 接続は init_schema / get_connection で管理してください。バックテスト時は元 DB から必要なテーブルをコピーしてインメモリ DB を使うことで本番データを汚染しません。
- ログは標準 logging を使用しています。環境変数 LOG_LEVEL で制御可能です。

---

必要であれば、README に以下の追記が可能です：
- 具体的な .env.example のテンプレート
- より詳細な ETL / CLI の使用例
- テスト方法（ユニットテストの実行手順）
- 開発時のワークフロー（データの初回ロード順など）

追記希望があれば教えてください。