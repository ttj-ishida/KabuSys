# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けライブラリ群です。データ収集（J-Quants API / RSS）、ETL、特徴量作成、戦略シグナル生成、マーケットカレンダー管理、監査ログなど「データプラットフォーム → 戦略 → 実行」までの主要機能を含み、DuckDB を中心に冪等処理・品質管理・トレーサビリティを重視して設計されています。

主な設計方針のポイント
- ルックアヘッドバイアスを防ぐ（target_date 時点のデータのみを使用）
- DuckDB に対する冪等保存（ON CONFLICT / INSERT … DO UPDATE / DO NOTHING）
- API 呼び出しはレート制御とリトライを実装
- XML/HTTP の堅牢化（SSRF や XML Bomb 対策）
- 簡易な研究用モジュール（research）を提供し、外部依存を最小化

---

## 機能一覧

- 環境設定管理
  - .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須設定を Settings 経由で取得（JQUANTS_REFRESH_TOKEN 等）
- データ取得（data.jquants_client）
  - J-Quants API から日次株価、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - レートリミッタ、リトライ、トークン自動リフレッシュ
- データ保存・スキーマ（data.schema）
  - DuckDB 用のスキーマ初期化（raw / processed / feature / execution 層）
  - init_schema(), get_connection() を提供
- ETL パイプライン（data.pipeline）
  - run_daily_etl() によるカレンダー・株価・財務の差分更新（バックフィル対応）
  - 品質チェックフックの呼び出し（quality モジュールに依存）
- ニュース収集（data.news_collector）
  - RSS フィード取得、前処理、raw_news 保存、銘柄抽出と紐付け
  - SSRF 対策、受信サイズ制限、XML 対策
- 特徴量計算（research.factor_research / strategy.feature_engineering）
  - Momentum / Volatility / Value 等のファクター計算
  - Z スコア正規化（data.stats）
  - ユニバースフィルタ（最低株価・平均売買代金）
- シグナル生成（strategy.signal_generator）
  - ファクター + ai_scores 統合 → final_score を算出
  - Bear レジーム抑制、BUY/SELL シグナルの生成と signals テーブルへの書き込み（冪等）
- マーケットカレンダー管理（data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days 等のユーティリティ
  - calendar_update_job による夜間の差分更新
- 監査ログ（data.audit）
  - signal_events / order_requests / executions など監査用テーブルを定義
  - UUID を連鎖させたトレーサビリティ

---

## 前提・依存関係

- Python 3.10 以上（PEP 604 の型ヒント（|）等を使用）
- 必須 Python パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリで多くを実装しているため、外部依存は最小限

実行環境例（仮想環境作成とパッケージインストール）
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 必要に応じて他パッケージを追加
```

（プロジェクトに requirements.txt がある場合はそちらを利用してください。）

---

## 環境変数

自動でプロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` / `.env.local` を読み込みます。読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

主な環境変数（Settings で参照される）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API の Base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

必須の環境変数が未設定の場合、Settings プロパティ取得時に ValueError が発生します。

---

## セットアップ手順

1. リポジトリをクローン（あるいはソースを取得）
2. 仮想環境を作成・有効化
3. 必要なパッケージをインストール（上記参照）
4. .env をプロジェクトルートに作成し 必要なキーを設定
   - 例（.env.example を参考に作成してください）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```
5. DuckDB スキーマの初期化
   - Python REPL かスクリプトで init_schema を実行（下記「使い方」を参照）

注意: 本リポジトリには自動でインストールするスクリプトはありません。CI/運用では requirements.txt / pyproject.toml を用意して依存管理してください。

---

## 使い方（基本例）

以下はライブラリを直接インポートして実行する最小の例です。実運用ではジョブスケジューラ（cron / Airflow 等）から呼び出すことを想定しています。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ファイルベースの DB を初期化
conn = init_schema("data/kabusys.duckdb")
# またはメモリ DB
# conn = init_schema(":memory:")
```

2) 日次 ETL の実行（J-Quants からデータを差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

3) 特徴量作成（strategy.feature_engineering.build_features）
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2025, 1, 20))
print(f"features upserted: {count}")
```

4) シグナル生成（strategy.signal_generator.generate_signals）
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
signals_count = generate_signals(conn, target_date=date(2025, 1, 20))
print(f"signals written: {signals_count}")
```

5) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄抽出に使う有効な銘柄コードセット（省略可）
res = run_news_collection(conn, known_codes={"7203", "6758"})
print(res)
```

6) カレンダー更新バッチ（夜間）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"market_calendar saved: {saved}")
```

注意点
- run_daily_etl() は内部で calendar → prices → financials → 品質チェックを順に実行します。個別に処理したい場合は run_prices_etl/run_financials_etl/run_calendar_etl を使ってください。
- すべての DB 書き込みは冪等を意識して実装されていますが、運用時はバックアップ・ロールバック手順を整備してください。

---

## ディレクトリ構成（抜粋）

プロジェクトは src/kabusys 配下にパッケージ化されています。主要なファイル・モジュールは以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py                    -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py          -- J-Quants API クライアント
    - news_collector.py          -- RSS ニュース収集
    - schema.py                  -- DuckDB スキーマ定義・初期化
    - pipeline.py                -- ETL パイプライン（run_daily_etl 等）
    - stats.py                   -- 統計ユーティリティ（zscore_normalize）
    - calendar_management.py     -- マーケットカレンダー管理
    - audit.py                   -- 監査ログテーブル定義
    - features.py                -- data.stats の再エクスポート
  - research/
    - __init__.py
    - factor_research.py         -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py     -- 研究用の将来リターン / IC / サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py     -- 特徴量作成（features テーブルへ保存）
    - signal_generator.py        -- シグナル生成（features + ai_scores → signals）
  - execution/                    -- 発注/実行関連（雛形）
  - monitoring/                   -- 監視 / メトリクス（雛形）

（上記は主要モジュールの一覧です。実際のリポジトリには追加ユーティリティやテスト、ドキュメントが存在する可能性があります。）

---

## 実運用での注意事項

- 本コードはシステムのコアロジックを提供しますが、実際の自動売買を行う場合は以下を必ず検討してください：
  - リスク管理・ポジション管理ロジックの追加と監査
  - 発注 API（証券会社）のレート制限やエラーハンドリングの検証
  - テスト環境（paper_trading）と live 環境の厳密な分離
  - 監査ログ・バックアップ・監視アラートの整備
- J-Quants の API レート制限や利用規約を遵守してください。
- 外部との通信（RSS / API）を行うコードはネットワーク障害や異常データに耐えるように運用してください。

---

もし README に含めたい追加の情報（例えば CI 流れ、テストの実行方法、詳しい .env.example、具体的な運用手順）があれば教えてください。必要に応じてサンプル .env.example や運用チェックリストも作成します。