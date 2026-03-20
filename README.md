# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリです。  
データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、DuckDB スキーマ管理、監査ログなどを含むパイプラインを提供します。

主な設計方針:
- ルックアヘッドバイアスを避ける（target_date 時点の情報のみを使用）
- idempotent（冪等）な DB 保存（ON CONFLICT/INSERT RETURNING 等）を重視
- 外部 API 呼び出しはレート制御・リトライ・トークン自動リフレッシュ対応
- セキュリティ（SSRF 対策、XML パースに対する防御など）を考慮

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（株価日足・財務データ・マーケットカレンダー）
  - raw データの DuckDB への冪等保存（raw_prices, raw_financials, market_calendar 等）
- ETL / データパイプライン
  - 差分取得（最終取得日からの差分）、バックフィル対応、品質チェック組み込み
  - 日次 ETL エントリポイント（run_daily_etl）
- スキーマ管理
  - DuckDB 用スキーマの定義と初期化（init_schema）
- 特徴量 / 戦略
  - ファクター計算（momentum, volatility, value）
  - Z スコア正規化ユーティリティ
  - features テーブル構築（build_features）
  - シグナル生成（generate_signals） — final_score を計算して BUY/SELL を作成
- ニュース収集
  - RSS 収集、前処理、記事保存、銘柄コード抽出、SSRF 対策、XML の安全パース
- 監査・発注ロギング
  - signal_events / order_requests / executions 等の監査テーブル定義
- ユーティリティ
  - マーケットカレンダー（営業日判定 / next/prev_trading_day / get_trading_days）
  - 統計ユーティリティ（zscore_normalize 等）

---

## セットアップ手順

前提:
- Python 3.9+（型アノテーションや typing の使用を想定）
- DuckDB（Python パッケージとしてインストール可能）
- ネットワーク経由の API 呼び出しのための適切なネットワーク環境

1. リポジトリをクローン／配置
   - ソースが配置されている想定: `src/` 以下に `kabusys` パッケージがある構成

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール（最低限）
   - pip install duckdb defusedxml
   - その他プロジェクト固有の依存がある場合は requirements.txt を参照（本コードベースには requirements ファイルは含まれていません）

4. 開発用インストール（ローカルパッケージとして使う場合）
   - pip install -e .

5. 環境変数の設定
   - .env / .env.local をプロジェクトルートに置くことで自動ロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化します）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API のパスワード（execution 層で使用予定）
     - SLACK_BOT_TOKEN — 通知用 Slack ボットトークン
     - SLACK_CHANNEL_ID — 通知先チャンネル ID
   - 任意 / デフォルト:
     - KABUSYS_ENV — one of {development, paper_trading, live} （デフォルト: development）
     - LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL / デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- 自動ロードは config.py がプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を読み込みます。テスト時に自動読み込みを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（簡単なワークフロー例）

以下は基本的な日次ワークフローの例です（Python REPL やスクリプト内で実行）。

1. DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" でインメモリDBも可能
```

2. 日次 ETL（市場カレンダー、株価、財務の差分取得・保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3. 特徴量の構築（features テーブルへ書き込み）
```python
from kabusys.strategy import build_features
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

4. シグナル生成（signals テーブルへ書き込み）
```python
from kabusys.strategy import generate_signals
n = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {n}")
```

5. ニュース収集（RSS から raw_news へ）
```python
from kabusys.data.news_collector import run_news_collection
# known_codes: 銘柄抽出に使う有効コード集合（例: {'7203','6758',...}）
res = run_news_collection(conn, known_codes={'7203', '6758'})
print(res)
```

追加のユーティリティ:
- カレンダー更新ジョブ:
  - kabusys.data.calendar_management.calendar_update_job(conn)
- DuckDB 既存接続取得:
  - from kabusys.data.schema import get_connection; conn = get_connection("data/kabusys.duckdb")

テスト・開発のヒント:
- id_token を外部注入できる API（jquants_client）設計にしているため、テストでトークンや HTTP 呼び出しをモックしやすいです。
- 自動 env 読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要モジュールと簡単な説明です（src/kabusys）:

- __init__.py
  - パッケージメタ情報（__version__）とサブパッケージの公開

- config.py
  - 環境変数管理（.env 自動読み込み、settings オブジェクト）

- data/
  - jquants_client.py — J-Quants API クライアント（取得/保存ロジック、レート制御、リトライ、トークン管理）
  - schema.py — DuckDB スキーマ定義と init_schema / get_connection
  - pipeline.py — ETL パイプライン（run_daily_etl 他）
  - news_collector.py — RSS 収集、前処理、DB 保存、銘柄抽出
  - calendar_management.py — 市場カレンダー管理（営業日判定・更新ジョブ）
  - audit.py — 監査ログ（signal_events / order_requests / executions 等）
  - features.py — zscore_normalize の再エクスポート
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - (その他) raw_* / processed layer 用の保存ユーティリティ

- research/
  - factor_research.py — momentum / volatility / value のファクター算出（prices_daily / raw_financials を参照）
  - feature_exploration.py — 将来リターン計算、IC（Spearman）計算、統計サマリー
  - __init__.py — 研究用ユーティリティのエクスポート

- strategy/
  - feature_engineering.py — 生ファクターのマージ・ユニバースフィルタ・正規化・features への upsert
  - signal_generator.py — features + ai_scores を統合して BUY/SELL シグナル生成
  - __init__.py — build_features / generate_signals の公開

- execution/
  - （発注・ブローカー連携は execution 層に実装予定／分離）

---

## 実装上の注意・設計メモ

- idempotency: DB への保存関数は ON CONFLICT / DO UPDATE / DO NOTHING を多用し、重複挿入や再実行に耐える設計です。
- Look-ahead bias: features / signal の計算は基本的に target_date 時点で利用可能なデータのみを使用します。
- Rate limiting: J-Quants クライアントは 120 req/min を遵守する固定間隔スロットリングを持っています。
- セキュリティ: news_collector は URL 正規化、トラッキングパラメータ除去、SSRF / private host 検出、defusedxml を用いた安全な XML パース、レスポンスサイズ制限を実施します。
- ロギング: 各モジュールが logging を活用しており、LOG_LEVEL 環境変数で制御できます。

---

## 貢献・開発

- コードの品質を維持するため、ユニットテスト／インテグレーションテストを追加してください。外部 API 呼び出しはモック可能な設計になっています。
- 新しいテーブルを追加する際は schema.py の _ALL_DDL と _INDEXES に適切に追加し、init_schema の挙動を考慮してください。
- 実運用での execution 層（発注処理・ブローカー API 連携）は本パッケージの外側に置くことが推奨されます（安全性・テスト容易性の観点から）。

---

README に記載が必要な補足や、利用例（CI 用スクリプト、cron ジョブの設定例、Dockerfile など）があればお知らせください。必要に応じて追加の利用手順や運用ドキュメントを作成します。