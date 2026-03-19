# KabuSys

日本株向けの自動売買 / データプラットフォーム基盤ライブラリです。  
市場データの取得・品質管理・特徴量生成・シグナル生成・監査ログ等、戦略実行に必要な主要機能をモジュール化して提供します。

---

## プロジェクト概要

KabuSys は以下の要件を目標とした Python ベースのライブラリです。

- J-Quants API 等からの市場データ取得（株価・財務・カレンダー）
- DuckDB を用いたデータレイク（Raw / Processed / Feature / Execution 層）
- 研究→本番に繋げるためのファクター計算、特徴量正規化、シグナル生成ロジック
- RSS ニュース収集と記事→銘柄紐付け
- ETL パイプライン、品質チェック、監査ログ機能
- 発注／実行まわり（execution 層）との連携を想定したテーブル群 / API（発注実装は層として分離）

設計上のポイント：
- ルックアヘッドバイアス回避（target_date 時点のデータのみ参照）
- 冪等性：DB 保存は ON CONFLICT / トランザクションで安全に上書き
- 外部 API 呼び出しは retry / rate limit / token refresh を備えた実装

---

## 主な機能一覧

- 環境・設定管理（kabusys.config）
  - .env/.env.local をプロジェクトルートから自動読み込み（優先順: OS env > .env.local > .env）
  - 必須環境変数チェック、環境（development/paper_trading/live）判定
- データ取得 / 保存（kabusys.data.jquants_client）
  - J-Quants API から株価日足・財務・カレンダーをページネーション対応で取得
  - トークン自動リフレッシュ、リトライ、レート制限対応
  - DuckDB への冪等保存関数（raw_prices, raw_financials, market_calendar 等）
- スキーマ管理（kabusys.data.schema）
  - DuckDB 用のテーブル DDL 定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日からの差分取得、バックフィル）
  - 日次 ETL 実行エントリ（run_daily_etl）と個別ジョブ
  - 品質チェックフック（quality モジュールを通じて）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードの取得・正規化・前処理・DB 保存（SSRF/サイズ/XML攻撃対策あり）
  - 記事IDは正規化URLの SHA-256（先頭32文字）で冪等化
  - 記事から銘柄コード抽出→news_symbols で紐付け
- 統計ユーティリティ（kabusys.data.stats）
  - クロスセクション Z スコア正規化など
- 研究用モジュール（kabusys.research）
  - ファクター計算（mom/volatility/value）、将来リターン計算、IC 計算、統計サマリー
- 戦略層（kabusys.strategy）
  - 特徴量生成（build_features）
  - シグナル生成（generate_signals）：複数コンポーネントを重み付けして final_score を算出、BUY/SELL を判定
- カレンダー管理 / バッチ（kabusys.data.calendar_management）
  - 営業日判定、next/prev_trading_day、カレンダー更新ジョブ
- 監査ログ（kabusys.data.audit）
  - signal/event/order_request/execution の監査テーブル DDL（トレーサビリティ確保）

---

## 動作要件（推奨）

- Python 3.10 以上（PEP 604 の型記法 "X | Y" を利用）
- 依存パッケージ（代表例）:
  - duckdb
  - defusedxml
  - そのほかネットワーク処理やロギングに必要な標準ライブラリ

プロジェクトの pyproject.toml / requirements.txt がある場合はそちらを参照して依存をインストールしてください。

---

## セットアップ手順

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存インストール（例）
   - pip install -U pip
   - pip install duckdb defusedxml
   - またはプロジェクトルートに requirements.txt / pyproject.toml があれば:
     - pip install -r requirements.txt
     - または pip install -e .

3. DuckDB 初期化
   - デフォルト DB パスは data/kabusys.duckdb（環境変数 DUCKDB_PATH で変更可）
   - Python REPL などで:
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")

4. 環境変数の準備
   - プロジェクトルートに .env/.env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
   - 必須環境変数（少なくともテスト/ETL 実行に必要なもの）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : （Slack 通知を使う場合）
     - KABU_API_PASSWORD : kabu API を使う場合
   - その他:
     - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH : DuckDB ファイルパス（例: data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 SQLite パスなど（例: data/monitoring.db）

例（.env の最小例）
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（簡易ガイド）

以下はライブラリの主要ワークフローの例です。用途に合わせてスクリプト化してください。

1) DuckDB スキーマの初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（J-Quants からの差分取得・保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) 特徴量作成（戦略用 features テーブルの構築）
```python
from kabusys.strategy import build_features
from datetime import date
count = build_features(conn, target_date=date(2024, 1, 12))
print(f"features upserted: {count}")
```

4) シグナル生成（features + ai_scores → signals テーブル）
```python
from kabusys.strategy import generate_signals
from datetime import date
signals_written = generate_signals(conn, target_date=date(2024, 1, 12))
print(f"signals: {signals_written}")
```

5) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
known_codes = {"7203","6758", ...}  # 既知の銘柄コードセット（抽出用）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6) カレンダー更新（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意:
- KABUSYS_ENV が `live` の場合は発注・実取引に繋がる設定やコードの取り扱いに注意してください（本番接続まわりは慎重に）。
- generate_signals や build_features は DuckDB 内のテーブル（prices_daily, raw_financials, features 等）を参照します。ETL を先に実行してください。

---

## 設定挙動の補足

- .env 自動読み込み
  - パッケージは実行時にプロジェクトルート（.git または pyproject.toml を起点）を探索し、以下順で読み込みます:
    1. OS 環境変数（既に設定されているものは上書きされない）
    2. .env（override=False）
    3. .env.local（override=True）
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト時などに便利）。

- 環境モード（KABUSYS_ENV）
  - 有効値: development, paper_trading, live
  - settings.is_live / is_paper / is_dev プロパティで判別できます。

---

## ディレクトリ構成（主要ファイルの説明）

リポジトリは src/kabusys 以下にモジュール群があります。主要ファイル:

- src/kabusys/__init__.py
  - パッケージメタ（version 等）
- src/kabusys/config.py
  - 環境変数・設定管理（settings）
- src/kabusys/data/
  - jquants_client.py : J-Quants API クライアント（取得→保存関数）
  - schema.py         : DuckDB スキーマ定義と init_schema()
  - pipeline.py       : ETL パイプライン（run_daily_etl 等）
  - news_collector.py : RSS フィード収集・記事保存・銘柄抽出
  - calendar_management.py : カレンダー管理・営業日判定・更新ジョブ
  - audit.py          : 監査ログ用 DDL・初期化
  - stats.py          : 統計ユーティリティ（zscore_normalize 等）
  - features.py       : data.stats の再エクスポート
  - execution/        : 発注・実行関連のモジュール（層として配置）
- src/kabusys/research/
  - factor_research.py : ファクター計算（momentum/value/volatility）
  - feature_exploration.py : 将来リターン・IC・統計サマリ
- src/kabusys/strategy/
  - feature_engineering.py : features テーブル構築ロジック
  - signal_generator.py    : final_score 計算と BUY/SELL 判定、signals 書き込み
- src/kabusys/monitoring/
  - （監視・メトリクス用モジュールを想定）
- その他:
  - README.md（本ファイル）
  - .env.example（プロジェクトルートにある想定のサンプル .env）

---

## 注意事項 / 運用上のヒント

- 本ライブラリはデータ取得や発注に関わるため、実運用では権限管理・シークレット管理（Vault 等）を併用してください。
- J-Quants の API レート制限（120 req/min）・403/429 等の扱いはクライアント側で考慮されていますが、実行頻度には配慮してください。
- Live モードで動かす前に paper_trading / development モードで十分な検証を行ってください。
- DuckDB のファイルパスを共有ディスクに置く場合は同時接続・排他に注意してください。

---

必要であれば README にサンプル .env.example、CLI スクリプト例、ユニットテスト方針、リファレンスや API 使用例（関数一覧）を追加できます。どの情報を優先して追加しますか？