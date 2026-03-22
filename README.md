# KabuSys

KabuSys は日本株向けの自動売買 / 研究プラットフォームです。データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、バックテスト、ニュース収集、簡易実行層（スキーマ）を揃え、研究 → 本番のワークフローをサポートすることを目的としています。

主な設計方針
- ルックアヘッドバイアス回避（計算は target_date 時点の情報のみ使用）
- 冪等性（DB への保存は ON CONFLICT / UPSERT を利用）
- 外部依存最小化（分析処理は可能な限り標準ライブラリと DuckDB で完結）
- API 呼び出しはレート制御・リトライ・トークン自動更新あり

バージョン: 0.1.0

---

## 機能一覧

- 環境変数 / 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検索）
  - 必須変数の簡易取得
- データ取得 & 保存（kabusys.data）
  - J-Quants API クライアント（株価・財務・市場カレンダー） — rate limit / retry / token refresh 対応
  - RSS ニュース収集（記事正規化・SSRF 対策・トラッキング除去・銘柄抽出）
  - DuckDB スキーマ定義と初期化（init_schema）
  - ETL パイプライン（差分更新、品質チェック）
  - 汎用統計ユーティリティ（Z スコア正規化等）
- 研究用モジュール（kabusys.research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計算・ファクター統計
- 戦略（kabusys.strategy）
  - 特徴量作成（build_features）
  - シグナル生成（generate_signals）
    - momentum/value/volatility/liquidity/news を統合して final_score を算出
    - Bear レジーム抑制、エグジット（ストップロス等）
- バックテスト（kabusys.backtest）
  - ポートフォリオシミュレータ（スリッページ・手数料モデル）
  - 日次ループでのシグナル約定シミュレーション（run_backtest）
  - 評価指標計算（CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- ニュース & シンボル紐付け（kabusys.data.news_collector）
- （実行層）スキーマに発注 / ポジション周りのテーブル定義を含む（kabusys.data.schema）

---

## 要求環境（推奨）

- Python 3.9+（型注釈により 3.10 を想定している箇所がありますが、3.9 でも動作することが多いです）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
  - （用途に応じて）requests 等（本実装は urllib を利用）
- DuckDB（Python パッケージ duckdb を使用）

requirements.txt が無い場合は仮想環境を作成して以下をインストールしてください（例）:

pip install duckdb defusedxml

※ 実行環境で他の依存が必要になった場合は適宜追加してください。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate (macOS / Linux)
   - .venv\Scripts\activate (Windows)

3. 依存ライブラリをインストール
   - pip install duckdb defusedxml
   - （必要なら追加のパッケージをインストール）

4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml と同じディレクトリ）に `.env` を置くと自動的に読み込まれます（起動時に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。
   - 必須変数（kabusys.config.Settings 参照）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必須）
     - SLACK_CHANNEL_ID — Slack チャネル ID（必須）
   - 任意 / デフォルト:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動読み込みを無効化
     - KABUSYS が使用する DB パス等:
       - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
       - SQLITE_PATH（デフォルト: data/monitoring.db）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ファイル DB を作成・テーブルを初期化
     conn.close()
     ```

---

## 使い方（主要な操作例）

ここでは代表的な操作の使い方を示します。

- バックテスト CLI
  - 事前にデータ（prices_daily, features, ai_scores, market_regime, market_calendar 等）が DB にあることが前提。
  - 実行例:
    ```
    python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2023-12-31 \
      --cash 10000000 --db data/kabusys.duckdb
    ```
  - 結果は標準出力に要約が表示されます。

- Python API: バックテストをプログラムから実行
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest

  conn = init_schema("data/kabusys.duckdb")
  try:
      result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
      metrics = result.metrics
      print(metrics)
  finally:
      conn.close()
  ```

- 特徴量作成（日次）
  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  try:
      n = build_features(conn, target_date=date(2024,1,31))
      print(f"features upserted: {n}")
  finally:
      conn.close()
  ```

- シグナル生成（1日分）
  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy import generate_signals

  conn = duckdb.connect("data/kabusys.duckdb")
  try:
      total = generate_signals(conn, target_date=date(2024,1,31))
      print(f"signals generated: {total}")
  finally:
      conn.close()
  ```

- ETL（株価取得の差分 ETL、Pipeline 関数を利用）
  - J-Quants から差分で取得して保存する関数が実装されています（kabusys.data.pipeline）。
  - 例（抜粋、実行には J-Quants トークンと DB が必要）:
    ```python
    from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_prices_etl

    conn = init_schema("data/kabusys.duckdb")
    try:
        fetched, saved = run_prices_etl(conn, target_date=date.today())
        print(f"fetched={fetched}, saved={saved}")
    finally:
        conn.close()
    ```

- ニュース収集
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  try:
      known_codes = {"7203","6758", ...}  # 有効コード集合（抽出用）
      results = run_news_collection(conn, known_codes=known_codes)
      print(results)
  finally:
      conn.close()
  ```

---

## 主な API / 参照関数

- kabusys.config.settings — 環境設定オブジェクト（プロパティ経由で設定取得）
- kabusys.data.schema.init_schema(db_path) — DB 初期化
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes — 株価取得 / 保存
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection — RSS 取得・保存
- kabusys.research.calc_momentum / calc_value / calc_volatility — ファクター計算
- kabusys.strategy.build_features(target_date) — features 作成
- kabusys.strategy.generate_signals(target_date) — signals 作成
- kabusys.backtest.run_backtest(...) — バックテスト実行
- python -m kabusys.backtest.run — バックテスト CLI

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境設定・.env 自動ロード
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API client（rate limit / retry / token refresh）
    - news_collector.py — RSS 収集・保存・銘柄抽出
    - pipeline.py — ETL パイプライン（差分更新 / 品質チェック）
    - schema.py — DuckDB スキーマ定義・初期化（init_schema）
    - stats.py — zscore_normalize 等の共通統計関数
  - research/
    - __init__.py
    - factor_research.py — momentum / volatility / value の計算
    - feature_exploration.py — forward returns / IC / summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py — features を作成して DB に保存
    - signal_generator.py — final_score を計算して signals を作成
  - backtest/
    - __init__.py
    - engine.py — run_backtest（バックテストの全体ループ）
    - simulator.py — PortfolioSimulator（約定・評価をシミュレート）
    - metrics.py — バックテスト評価指標計算
    - run.py — CLI ラッパー
    - clock.py — 将来拡張のための SimulatedClock
  - execution/ — 発注実装用プレースホルダ（現状空）
  - monitoring/ — 監視用モジュール（リポジトリによる）

---

## 運用上の注意点 / 実装ノート

- 環境変数読み込み
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読込します。OS 環境変数が優先され、.env.local は .env を上書きします。
  - 自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants クライアント
  - レート制限（120 req/min）を守るため固定間隔スロットリングを実装しています。
  - 401 を受けた場合はリフレッシュトークンで idToken を自動更新して再試行します（ただし無限ループはしない設計）。
- ニュース収集
  - RSS の XML パースには defusedxml を使用し、SSRF / XML ビル攻撃などの対策を施しています。
  - 記事ID は正規化 URL の SHA-256 の先頭 32 文字で生成（冪等性確保）。
- DB スキーマ
  - DuckDB を用いて Raw / Processed / Feature / Execution レイヤーを定義しています。スキーマの変更は schema.py を編集して反映してください。
- ルックアヘッド回避
  - すべての戦略計算・シグナル生成は target_date 時点の情報のみを使用するように作られています。データ取得タイムスタンプ（fetched_at）を記録し、いつデータが利用可能になったかをトレース可能にしています。

---

## 開発 / テストのヒント

- 単体テストやテスト環境では .env の自動ロードを無効にし（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）、settings オブジェクトや関数にテスト用の値を注入して下さい。
- news_collector._urlopen や jquants_client._request はモックしやすい構造になっています。ネットワーク依存のテストはこれらを差し替えて実行してください。
- バックテストはソース DB を汚さないために、内部で in-memory DuckDB に必要なテーブルをコピーして実行します（_build_backtest_conn）。

---

## ライセンス / 責任

- 本 README はコードの現状実装に基づく簡易ドキュメントです。実運用前に十分なテストを行い、API 利用に関する規約・金融関連の法令遵守を確認してください。
- 実装にはサンプル・参照的なコードが含まれます。実際の資金運用は自己責任でお願いします。

---

必要があれば次の内容を追加できます:
- 詳細なテーブル定義（columns の説明）
- StrategyModel.md / DataPlatform.md に対応する仕様要約
- よくあるエラーとトラブルシューティング
- CI / ローカル開発用の Makefile / scripts 例

どの追加情報が必要か教えてください。