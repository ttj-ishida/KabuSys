# KabuSys

KabuSys は日本株向けの自動売買およびリサーチ基盤です。  
DuckDB を用いたデータパイプライン／ファクター計算、特徴量生成、シグナル生成、ポートフォリオ構築、バックテスト、ニュース収集などの主要コンポーネントを含みます。

---

## プロジェクト概要

主な目的：
- J-Quants API から市場データ・財務データを取得して DuckDB に保存
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- ファクターの正規化・合成（feature engineering）
- AI スコアやファクターを組み合わせた売買シグナル生成（generate_signals）
- セクター制限・レジーム乗数を考慮したポートフォリオ構築および発注株数計算
- シンプルだが現実的なスリッページ／手数料モデルを持つバックテストエンジン
- RSS ベースのニュース収集と銘柄紐付け

設計方針：
- ルックアヘッドバイアスを避ける（target_date ベースの計算）
- DuckDB を中心とした軽量なデータ層
- 基本的に副作用を持たない純粋関数群と、DB/IO 層での明示的な操作
- 冪等性・トランザクション安全性を重視

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（日足・財務データ・上場情報・カレンダー）
  - raw_prices / raw_financials / market_calendar 等への保存関数（冪等）
- ニュース収集
  - RSS 取得、前処理、raw_news 保存、記事→銘柄の紐付け
  - SSRF 対策・Gzip/サイズ制限・XML 脆弱性対策を実装
- 研究・ファクター
  - calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials ベース）
  - 研究ユーティリティ（IC 計算・将来リターン計算・サマリー等）
- 特徴量エンジニアリング
  - ユニバースフィルタ、Z スコア正規化、クリッピング、features テーブルへの UPSERT
- シグナル生成
  - ファクター + AI スコアを統合して final_score を算出、BUY/SELL シグナルを作成
  - Bear レジームでの BUY 抑制、エグジット条件（ストップロス等）
- ポートフォリオ構築
  - 候補選定、等配分／スコア加重配分、risk_based サイジング
  - セクターキャップ、レジーム乗数
- バックテスト
  - in-memory DuckDB コピーによる安全なバックテスト環境構築
  - PortfolioSimulator （擬似約定、スリッページ／手数料モデル）
  - 日次スナップショット、TradeRecord、評価指標（CAGR、Sharpe、MaxDD、勝率等）
  - CLI ランナー（python -m kabusys.backtest.run）
- 設定管理
  - .env 自動ロード（プロジェクトルート検出、.env/.env.local の優先順）
  - 必須設定のラッパー（Settings）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈の構文 Path | None 等を使用）
- DuckDB が利用可能（pip パッケージ）
- ネットワークアクセス（J-Quants API、RSS）

推奨手順（ローカル開発）：

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml
   - （プロジェクトに pyproject.toml/requirements.txt がある場合はそれに従ってください）
   - 開発環境で使う場合は必要に応じて他の依存（例えば ai ライブラリや slack-sdk 等）を追加

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に `.env` または `.env.local` を置くことで自動ロードされます（起動時に自動読み込み）。
   - 自動ロードを無効化したいときは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

必須（または推奨）環境変数（例）
- JQUANTS_REFRESH_TOKEN=...        （必須: J-Quants 用リフレッシュトークン）
- KABU_API_PASSWORD=...            （必須: kabuステーション API パスワード）
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  （任意: デフォルト localhost）
- SLACK_BOT_TOKEN=...              （必須: Slack 通知を使う場合）
- SLACK_CHANNEL_ID=...             （必須: Slack 通知を使う場合）
- DUCKDB_PATH=data/kabusys.duckdb   （任意: デフォルト）
- SQLITE_PATH=data/monitoring.db    （任意: デフォルト）
- KABUSYS_ENV=development|paper_trading|live  （任意: デフォルト development）
- LOG_LEVEL=INFO|DEBUG|...          （任意）

例 .env（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

5. DuckDB スキーマ初期化
   - パッケージ内にスキーマ初期化関数があるため Python REPL 等で実行可能：
     ```
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```
   - （注）schema モジュールは本 README に含めていないため、実際のプロジェクトではスキーマ定義 SQL を用意してください。

---

## 使い方（主要なワークフロー）

- バックテスト（CLI）
  - 価格・features 等の DB を用意した上で以下を実行：
    ```
    python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2024-12-31 \
      --cash 10000000 --db data/kabusys.duckdb
    ```
  - オプション：--slippage, --commission, --allocation-method, --max-positions など

- 特徴量生成（Python API）
  - DuckDB 接続を渡して features を構築：
    ```
    import duckdb
    from kabusys.strategy.feature_engineering import build_features
    conn = duckdb.connect("data/kabusys.duckdb")
    from datetime import date
    build_features(conn, date(2024, 1, 31))
    conn.close()
    ```

- シグナル生成（Python API）
  - features / ai_scores / positions を参照して signals テーブルに書き込み：
    ```
    from kabusys.strategy.signal_generator import generate_signals
    generate_signals(conn, date(2024, 1, 31))
    ```

- ニュース収集（RSS）
  - RSS を取得して DB に保存（known_codes を渡すと銘柄抽出も実行）：
    ```
    from kabusys.data.news_collector import run_news_collection
    result = run_news_collection(conn, known_codes=set_of_codes)
    ```

- データ取得（J-Quants）
  - API 呼び出し例（取得 → 保存）：
    ```
    from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
    rows = fetch_daily_quotes(date_from=..., date_to=...)
    save_daily_quotes(conn, rows)
    ```

- バックテスト結果の取得（Python API）
  - run_backtest を使ってメモリ内でバックテストを実行し、結果を受け取る：
    ```
    from kabusys.backtest.engine import run_backtest
    result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
    # result.history, result.trades, result.metrics を利用
    ```

注意点：
- generate_signals / build_features 等は target_date ベースでルックアヘッドを防ぐ設計です。バックテストや本番実行時は必ず同一の target_date を用いたフローに従って実行してください。
- J-Quants クライアントはレート制限・リトライ・トークンリフレッシュを含みます。環境変数でトークンを設定してください。
- news_collector は外部ネットワークを使用するため、SSRF 保護や応答サイズ制限等の安全機構が入っています。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - backtest/
    - __init__.py
    - engine.py            — バックテストエンジン（run_backtest）
    - simulator.py         — PortfolioSimulator, DailySnapshot, TradeRecord
    - metrics.py           — バックテスト評価指標計算
    - run.py               — CLI エントリポイント
    - clock.py
  - data/
    - jquants_client.py    — J-Quants API クライアント・保存関数
    - news_collector.py    — RSS 取得・前処理・保存・銘柄抽出
    - (schema.py, calendar_management.py 等想定のモジュール)
  - research/
    - __init__.py
    - factor_research.py   — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py — IC / forward returns / summary
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル構築
    - signal_generator.py    — final_score 計算・signals 生成
  - portfolio/
    - __init__.py
    - portfolio_builder.py  — select_candidates, weight 計算
    - position_sizing.py    — calc_position_sizes
    - risk_adjustment.py    — apply_sector_cap, calc_regime_multiplier
  - execution/              — 発注／接続周り（実装の拡張点）
  - monitoring/            — 監視・通知関連（Slack 等）
  - research/              — 研究関連ユーティリティ群
  - etc.

（実際のリポジトリには上記以外にも補助モジュールやテスト、SQL スキーマ等が含まれる可能性があります）

---

## 開発上のメモ / よくある質問

- Python バージョン
  - 本コードは 3.10+ の構文（a | b 型、match 未使用だが union 表記）を想定しています。3.10 以上を推奨します。

- .env の自動読み込み
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に .env/.env.local を自動ロードします。
  - テスト時や明示的に無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- データベース初期化
  - init_schema() のようなスキーマ初期化関数を提供している想定です（schema モジュール参照）。プロジェクトの SQL 定義に従って DB を作成してください。

- ロギング
  - Settings.log_level によりログレベルを制御できます。初期開発は DEBUG を使用すると内部挙動が確認しやすいです。

---

## 貢献 / 拡張案

- execution 層：kabuステーション API 経由での実取引実装（安全ガード・テスト要）
- 銘柄別単元（lot_size）対応：stocks マスタに単元情報を持たせる
- マルチコア／バッチ処理：大量銘柄処理の高速化
- AI スコア生成パイプラインの具体実装（モデル訓練・推論）
- 分足シミュレーション対応（SimulatedClock の拡張）

---

README は以上です。必要であれば README に具体的な .env.example、schema 初期化 SQL 例、あるいはデモ用の小さなスクリプトを追加できます。どの情報を優先して詳しく載せたいか教えてください。