# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
研究（factor research）・ETL（J-Quants 経由の市場データ収集）・特徴量生成・シグナル生成・バックテスト・簡易ポートフォリオシミュレーションまでを含むモジュール群を提供します。

主な設計方針
- ルックアヘッドバイアス防止（各処理は target_date 時点の情報のみを使用）
- DuckDB ベースのローカル DB（init_schema でスキーマ初期化）
- API クライアントはレート制御・リトライ・トークンリフレッシュ対応
- ETL / 保存処理は冪等（ON CONFLICT / トランザクション利用）
- ニュース収集は SSRF / XML 攻撃対策を実装

バージョン: 0.1.0

---

## 機能一覧（主なモジュール）
- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出） / 必須環境変数管理
  - 環境変数で KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL を設定
- kabusys.data
  - jquants_client: J-Quants API クライアント（株価・財務・カレンダー取得、保存関数付き）
  - news_collector: RSS 取得・前処理・raw_news 保存・銘柄抽出
  - schema: DuckDB スキーマ定義と init_schema / get_connection
  - pipeline: ETL ジョブ（差分取得・保存・品質チェック等）
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.research
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー
- kabusys.strategy
  - feature_engineering.build_features: raw factor を正規化して features テーブルへ保存
  - signal_generator.generate_signals: features/ai_scores 等から BUY / SELL シグナルを生成し signals テーブルへ書き込み
- kabusys.backtest
  - engine.run_backtest: DuckDB データをコピーして日次ループでバックテストを実行
  - simulator.PortfolioSimulator: 約定・スリッページ・手数料を考慮した擬似約定
  - metrics.calc_metrics: バックテスト結果の評価指標（CAGR、Sharpe、MaxDD 等）
  - CLI: python -m kabusys.backtest.run（期間指定でバックテスト実行）

---

## 依存関係（最低限）
以下は代表的な依存パッケージ（プロジェクトに requirements.txt があればそちらを優先してください）:
- Python 3.9+
- duckdb
- defusedxml

例（pip）:
pip install duckdb defusedxml

開発環境では仮想環境を作成することを推奨します。

---

## セットアップ手順

1. リポジトリをクローン / コピー

2. 仮想環境作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 依存インストール
   ```bash
   pip install duckdb defusedxml
   # もしパッケージをローカルで editable install したい場合
   pip install -e .
   ```

4. 環境変数 (.env) の準備  
   必須環境変数（主なもの）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD : kabuステーション API パスワード（実運用時）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID : Slack 通知用
   - KABUSYS_ENV : development / paper_trading / live（省略時は development）
   - LOG_LEVEL : DEBUG/INFO/…（省略時 INFO）
   - DUCKDB_PATH / SQLITE_PATH : デフォルトは data/kabusys.duckdb / data/monitoring.db

   プロジェクトルート（.git や pyproject.toml がある場所）に `.env` / `.env.local` を置くと自動的に読み込まれます。
   自動読み込みを無効化する場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

5. DuckDB スキーマ初期化（ファイル DB の場合）
   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")
   ```
   もしくは簡単にシェルから:
   ```bash
   python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   ```

---

## 使い方（よく使う例）

- バックテスト CLI
  DuckDB ファイルが所定のテーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）で準備されていることが前提です。
  ```bash
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 \
    --slippage 0.001 \
    --commission 0.00055 \
    --max-position-pct 0.20 \
    --db data/kabusys.duckdb
  ```

- DB 初期化 + ETL（簡易例）
  J-Quants トークンを設定した状態で prices の差分 ETL を実行する（run_prices_etl は pipeline モジュールにあります）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_prices_etl, run_news_collection

  conn = init_schema("data/kabusys.duckdb")
  # 当日までの価格差分取得（例）
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  # ニュース収集（known_codes を渡すと銘柄の紐付けも試みる）
  results = run_news_collection(conn, known_codes=set(["7203", "6758"]))
  conn.close()
  ```

- 特徴量作成・シグナル生成（Python API）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features, generate_signals

  conn = init_schema("data/kabusys.duckdb")
  # features を作成（target_date 時点のファクターを計算して保存）
  n = build_features(conn, target_date=date(2024, 1, 10))
  # signals を生成（features / ai_scores / positions を参照して signals テーブルへ書き込む）
  m = generate_signals(conn, target_date=date(2024, 1, 10), threshold=0.60)
  conn.close()
  ```

- News Collector（RSS）を走らせて raw_news を保存
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  run_news_collection(conn)
  conn.close()
  ```

- DB スキーマ操作
  - init_schema(db_path) : スキーマ作成・接続返却
  - get_connection(db_path) : 既存 DB へ接続（スキーマ初期化はしない）

---

## 重要な設計・運用上のポイント

- 自動ロードされる環境変数:
  - プロジェクトルートの `.env` → `.env.local`（`.env.local` は上書き）を自動読み込みします。テスト時や CI で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ID トークン管理:
  - jquants_client はリフレッシュトークンから id_token を取得し、トークン失効時は自動リフレッシュと 1 回の再試行を行います。
- レート制御:
  - J-Quants API へは内部で固定間隔スロットリング（120 req/min）とリトライ（指数バックオフ）を実装済みです。
- 冪等性:
  - save_* 関数は ON CONFLICT / トランザクションを使用して重複や途中失敗に耐える設計です。
- セキュリティ:
  - news_collector では SSRF 対策（ホスト検査、リダイレクト検査）や XML パースに defusedxml を利用して安全性を高めています。
- ルックアヘッドバイアス防止:
  - 研究 / 特徴量・シグナル生成は target_date 時点で利用可能な情報のみを使用する方針です。

---

## ディレクトリ構成（主要ファイル）
（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
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
    - run.py
    - clock.py
  - execution/  (発注・実行関連のプレースホルダ)
  - monitoring/ (監視用モジュール等のプレースホルダ)

各モジュールには docstring に主要な挙動・前提条件・設計方針が記載されています。詳細は各ファイルのヘッダコメントを参照してください。

---

## 開発・貢献
- コードはドキュメント化（関数 docstring）されており、ユニットテストや CI を追加することで品質向上が可能です。
- 新しい ETL ソースや戦略を追加する場合は、DuckDB スキーマと既存の ETL ワークフローとの整合性に注意してください。

---

## 参考（よくあるコマンドまとめ）
- 仮想環境作成: python -m venv .venv
- 依存インストール: pip install duckdb defusedxml
- スキーマ初期化: python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
- バックテスト実行: python -m kabusys.backtest.run --start YYYY-MM-DD --end YYYY-MM-DD --db data/kabusys.duckdb

---

README に書かれている API や関数の詳細はソースコード内の docstring を参照してください。運用時の機密情報（API トークン等）は .env で安全に管理してください。