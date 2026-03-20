# KabuSys

日本株向けの自動売買／データプラットフォームライブラリです。  
データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、カレンダー管理、発注監査などをモジュール化して提供します。

> 本READMEはリポジトリ内のソースコードをもとに作成しています。実行には外部API（J‑Quants / kabuステーション 等）の認証情報が必要です。実運用（live）モードでの実行は十分な検証と注意のうえ行ってください。

## 主な機能
- J-Quants API クライアント（株価・財務・カレンダー取得、ページネーション、レートリミット・リトライ・トークン自動リフレッシュ対応）
- DuckDB ベースのスキーマ定義と初期化（raw / processed / feature / execution 層）
- ETL パイプライン（日次 ETL：市場カレンダー / 株価 / 財務の差分取得と保存、品質チェック統合）
- 特徴量（ファクター）計算（モメンタム / バリュー / ボラティリティ / 流動性）と Z スコア正規化
- シグナル生成（特徴量 + AI スコア統合 → final_score → BUY / SELL シグナル生成。Bear レジーム抑制、エグジット条件判定）
- ニュース収集（RSS 取得、前処理、記事保存、銘柄抽出、SSRF / gzip / XML 攻撃対策）
- マーケットカレンダー管理（営業日判定、next/prev trading day、夜間更新ジョブ）
- 監査ログ（signal → order_request → execution までのトレーステーブル群）

## 必要条件
- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- ネットワーク（J-Quants / RSS / kabuステーション へアクセス可能な環境）
- 各種 API トークン / 資格情報（環境変数で設定）

インストール例（仮想環境内）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# パッケージをeditableでインストールする場合（セットアップがある場合）
# pip install -e .
```

## 環境変数（設定）
自動で `.env` / `.env.local` をプロジェクトルートから読み込みます（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

必須（実行にあたって設定が必要なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

オプション（デフォルトあり）
- KABUSYS_ENV — environment: `development` / `paper_trading` / `live`（default: development）
- LOG_LEVEL — ログレベル: `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（default: INFO）
- KABU_API_BASE_URL — kabuステーション API ベース URL（default: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）

例（.env）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

## セットアップ手順
1. リポジトリをクローンして仮想環境を作成・有効化
2. 必要パッケージをインストール（上記参照）
3. プロジェクトルートに `.env` を作成して必要な環境変数を設定
4. DuckDB スキーマを初期化する

DuckDB スキーマ初期化の例:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# 以降 conn を使って操作できます
```

## 使い方（代表的な操作例）

- 日次 ETL を実行（市場カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量（features）を構築
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection, init_schema

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date.today())
print(f"built features: {n}")
```

- シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection, init_schema

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {count}")
```

- ニュース収集（RSS）と DB 保存
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "8306"}  # 既知の銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar rows saved: {saved}")
```

注意:
- ここで示したコードは最低限の呼び出し例です。実運用ではログ設定、エラーハンドリング、ジョブスケジューリング（cron / Airflow 等）、監査ログの記録、発注層との統合などを適切に行ってください。
- generate_signals / build_features は DB 内の各種テーブル（prices_daily, raw_financials, features, ai_scores, positions 等）に依存します。まず ETL を走らせてデータを準備してください。

## ディレクトリ構成（抜粋）
リポジトリの主要なモジュールと役割:

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理
  - data/
    - __init__.py
    - schema.py — DuckDB スキーマ定義・初期化
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - news_collector.py — RSS 取得・記事保存・銘柄抽出
    - calendar_management.py — 市場カレンダー操作 / 夜間更新ジョブ
    - features.py — zscore_normalize 再エクスポート
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py — 発注／約定の監査ログ用 DDL（トレーステーブル）
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン / IC / 要約統計の補助関数
  - strategy/
    - __init__.py
    - feature_engineering.py — ファクター正規化・features テーブルへの保存
    - signal_generator.py — final_score 計算と signals テーブルへの書き込み
  - execution/ — （発注実装・ブリッジ等。空の __init__ が存在）
  - monitoring/ — 監視・メトリクス関連（コードベースに応じて配置）

ファイル分割の考え方:
- data/*: データ取得・保存・ETL・スキーマ管理
- research/*: 研究用のファクター生成・解析ユーティリティ（実行環境と分離）
- strategy/*: 戦略の特徴量整形・シグナル生成ロジック
- execution/*: 発注フローとブローカ連携（将来的に実装）
- config.py: 環境変数中心の設定。自動 .env ロードを行う

## 開発上の注意・設計方針（抜粋）
- ルックアヘッドバイアス対策: すべての戦略系計算は target_date 時点までの情報のみを用いる設計。
- 冪等性: 外部データの DB 保存は ON CONFLICT / INSERT ... DO UPDATE / DO NOTHING を用いて冪等に実装。
- レート制御 & リトライ: J-Quants クライアントは固定間隔のスロットリングと指数バックオフを実装。
- セキュリティ: RSS 周りは SSRF/XML Bomb 対策、gzip 解凍後サイズチェック等を実施。
- DuckDB を用いた軽量オンディスク DB（分析と本番データの一元化に適する）。

## よくある運用フロー（例）
1. init_schema() で DB 作成
2. 毎夜 cron で run_daily_etl() を実行（市場カレンダー → 株価 → 財務）
3. ETL 終了後、build_features() を実行して features を更新
4. generate_signals() で当日のシグナルを作成 → signals テーブルに保存
5. execution 層（ブローカ連携）で signals を読み取り発注 → audit テーブルに記録
6. news_collector を定期実行して raw_news・news_symbols を更新して分析へ活用

## サポート・貢献
- ソース内の docstring に主要な設計・仕様（DataPlatform.md, StrategyModel.md 等）が参照されています。追加のドキュメントやユニットテストを整備すると採用・運用が容易になります。
- 実運用では必ずステージング / paper_trading モードで検証し、KABUSYS_ENV を適切に切り替えてください。

---

この README はコードベースの主要機能と使い方の概要を示しています。個別の関数やテーブル定義の詳細はソースの docstring / モジュール内コメントをご参照ください。必要であればサンプルスクリプトやデプロイ手順（systemd / Docker / Airflow 連携例）を追記します。どの部分を詳しく書いて欲しいか教えてください。