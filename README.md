# KabuSys

日本株向けの自動売買基盤ライブラリです。データ収集（J-Quants API）、ETL、特徴量計算、シグナル生成、ニュース収集、監査用スキーマなどを含むモジュール群を提供します。研究（research）→データ（data）→戦略（strategy）→実行（execution）という層構造を想定した設計です。

---

## プロジェクト概要

- 目的: 日本株の自動売買システムに必要なデータ基盤・研究・戦略ロジック・監査機能をモジュール化して提供する。
- 主な技術:
  - DuckDB を用いたローカルデータベース（ファイルまたはインメモリ）
  - J-Quants API クライアント（rate limit / retry / token refresh 対応）
  - RSS 収集とニュース→銘柄紐付け（SSRF・XML攻撃対策）
  - ファクター計算（momentum / volatility / value 等）と Z スコア正規化
  - シグナル生成（重み付け合成、Bear レジーム抑制、エグジット判定）
  - 冪等な DB 保存（ON CONFLICT / トランザクション）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local を自動読み込み（プロジェクトルート判定: .git / pyproject.toml）
  - 必須環境変数チェック（Settings クラス）
  - 自動読み込み無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- データ取得・保存
  - J-Quants API クライアント（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）
  - 保存用ユーティリティ（raw_prices / raw_financials / market_calendar などへ冪等保存）
  - API レート制御・リトライ・トークン自動更新
- ETL / パイプライン
  - 日次 ETL（run_daily_etl）：カレンダー・株価・財務データの差分取得と品質チェック
  - 個別 ETL ジョブ（prices / financials / calendar）
- スキーマ管理
  - DuckDB スキーマ初期化（init_schema）: Raw / Processed / Feature / Execution 層のテーブルを作成
- ニュース収集
  - RSS フィード取得・正規化・DB 保存（raw_news）・銘柄抽出（4桁コード）
  - SSRF / XML 攻撃 / レスポンスサイズ対策を実装
- 研究用ツール
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
- 特徴量・シグナル生成
  - build_features: raw ファクターを統合して features テーブルへ保存（Z スコア正規化・ユニバースフィルタ）
  - generate_signals: features と ai_scores を統合して BUY / SELL シグナルを生成し signals テーブルへ保存
- 監査（audit）テーブル群
  - signal_events / order_requests / executions 等により signal→order→execution をトレース可能

---

## 必要条件 / 依存

- Python 3.10 以上（型ヒントで | 演算子を使用）
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml
- 標準ライブラリ: urllib, json, datetime, logging 等

（実行環境によって追加パッケージが必要になる場合があります。プロジェクトの requirements.txt がある場合はそちらを参照してください。）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成
   ```
   git clone <repo>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストール
   ```
   pip install duckdb defusedxml
   # その他必要なパッケージがあれば追加でインストール
   ```

3. 環境変数を準備
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` または `.env.local` を置くと自動ロードされます（自動ロードはデフォルトで有効）。
   - 主な環境変数（Settings クラスで参照されるもの）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
     - SLACK_BOT_TOKEN (必須)
     - SLACK_CHANNEL_ID (必須)
     - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
     - KABUSYS_ENV (任意, 値: development / paper_trading / live; デフォルト: development)
     - LOG_LEVEL (任意, DEBUG/INFO/WARNING/ERROR/CRITICAL)
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトから初期化できます。
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイルパスまたは ":memory:"
   ```

---

## 使い方（基本的なワークフロー例）

1. DB を初期化して日次 ETL を実行（J-Quants からデータ取得）
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn)  # デフォルトで本日を対象に実行
   print(result.to_dict())
   ```

2. 特徴量（features）を構築
   ```python
   from datetime import date
   from kabusys.strategy import build_features

   cnt = build_features(conn, date.today())
   print(f"built features: {cnt}")
   ```

3. シグナル生成
   ```python
   from datetime import date
   from kabusys.strategy import generate_signals

   total_signals = generate_signals(conn, date.today(), threshold=0.6)
   print(f"signals generated: {total_signals}")
   ```

4. ニュース収集（RSS）
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   # known_codes は既知の銘柄コードセット（例: prices_daily から取得）
   known_codes = {"7203", "6758", "9984"}
   res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(res)
   ```

5. 追加のユーティリティ
   - 研究用: calc_forward_returns / calc_ic / factor_summary などは kabusys.research パッケージにあります。
   - スキーマ参照・監査ログ操作・実行層は kabusys.data.audit や execution パッケージを参照してください。

---

## 注意点 / 実運用上の挙動

- J-Quants クライアントはレート制限（120 req/min）を守る設計です。大量取得時は時間がかかります。
- API の 401 応答を受けた場合はリフレッシュトークンを使って自動的に ID トークンを再取得し 1 回リトライします。
- ETL は差分更新を行います。初回ロードでは過去データを取得しますが、その後は最終取得日以降のみ取得します（バックフィル調整あり）。
- ニュース収集は外部 XML を扱うため、defusedxml を用いて XML 攻撃を緩和しています。また、SSRF 対策としてリダイレクト先やホストの検査を行います。
- features / signals 生成は「ルックアヘッドバイアスを防ぐ」ため、target_date 時点で利用可能なデータのみを参照する設計になっています。
- 環境変数の自動読み込みはプロジェクトルートを .git または pyproject.toml から探索して行います。CI やテスト環境では無効化することを推奨します（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

## ディレクトリ構成（抜粋）

以下は主要モジュールの構成（src/kabusys 以下）。実際のリポジトリには他の補助ファイルやテスト等がある場合があります。

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py          # J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py         # RSS 取得・前処理・DB保存
    - schema.py                 # DuckDB スキーマ定義・init_schema
    - stats.py                  # zscore_normalize など統計ユーティリティ
    - pipeline.py               # ETL パイプライン（run_daily_etl 等）
    - features.py               # data.stats の再エクスポート
    - calendar_management.py    # market_calendar の管理・営業日API
    - audit.py                  # 監査ログ用DDL と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py        # momentum/volatility/value 計算
    - feature_exploration.py    # 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py    # build_features
    - signal_generator.py       # generate_signals
  - execution/
    - __init__.py               # 実行層（発注・オーダー管理）用パッケージ（実装は別途）
  - monitoring/                  # 監視・メトリクス関連（存在する場合）

---

## ライセンス / 貢献

（この README ではライセンスや貢献方法の記載は省略しています。リポジトリの LICENSE / CONTRIBUTING ファイルを参照してください。）

---

README に記載されていない詳細な使い方や API は各モジュールの docstring を参照してください（例: kabusys/data/jquants_client.py, kabusys/strategy/signal_generator.py 等）。必要であれば、README にサンプルスクリプトや運用ガイド（cron/airflow での日次実行例、ロギング設定、監視設計）を追加できます。ご希望があれば追記します。