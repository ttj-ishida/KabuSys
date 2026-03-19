# KabuSys

日本株のデータ取得・特徴量生成・シグナル生成・発注トレーサビリティを念頭に設計された自動売買基盤ライブラリです。  
このリポジトリは主に以下レイヤーを提供します：データ取得（J-Quants API）、DuckDB ベースのデータスキーマ、研究（factor 計算 / 探索）、特徴量作成、シグナル生成、ニュース収集、ETL パイプライン。

バージョン: 0.1.0

---

## 主要な特徴（機能一覧）

- データ取得
  - J-Quants API クライアント（日足、財務、マーケットカレンダー）
  - 取得時のレートリミット / リトライ / トークン自動リフレッシュ対応
- データ永続化
  - DuckDB によるスキーマ定義・初期化（raw / processed / feature / execution 層）
  - 冪等（ON CONFLICT）での保存処理
- ETL
  - 差分更新（バックフィル対応）、品質チェックを含む日次 ETL 実装
- 研究・特徴量
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials 参照）
  - cross-sectional Zスコア正規化ユーティリティ
  - 将来リターン計算、IC（スピアマン相関）計算、統計サマリー
- 戦略
  - 特徴量合成（feature_engineering.build_features）
  - シグナル生成（signal_generator.generate_signals）：AI スコア統合、Bear レジーム抑制、BUY/SELL 生成
- ニュース収集
  - RSS 取得・前処理・DB 保存、銘柄コード抽出（SSRF/サイズ対策・XML 安全化）
- 監査・発注トレーサビリティ
  - signal_events / order_requests / executions 等の監査テーブル定義

---

## 動作環境

- Python 3.10 以上（PEP 604 型注釈 `X | Y` を使用）
- 必要な Python パッケージ（一部）
  - duckdb
  - defusedxml
- 標準ライブラリの urllib / logging / datetime 等を広範に使用

必要なパッケージはプロジェクトの requirements.txt / pyproject.toml を使用してインストールしてください（このリポジトリ内に明示的なファイルが無い場合は上記を個別に pip インストール）。

例:
pip install duckdb defusedxml

---

## 環境変数（.env）

アプリケーションは .env ファイルまたは環境変数を読み込みます（プロジェクトルートに `.env` / `.env.local` がある場合、自動ロードされます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

主な環境変数:

- J-Quants / データ
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- kabu ステーション（発注）
  - KABU_API_PASSWORD: kabu API パスワード（必須）
  - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- Slack（通知）
  - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
  - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- データベース
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite（モニタリングDB）パス（デフォルト: data/monitoring.db）
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）

サンプル .env:
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG

---

## セットアップ手順

1. Python 環境を用意（3.10+ を推奨）
2. 依存パッケージをインストール
   pip install duckdb defusedxml
   （プロジェクトで pyproject.toml / requirements.txt を用意している場合はそちらを利用）
3. リポジトリをクローンして作業ディレクトリに移動
4. .env を作成して必要な環境変数を設定
5. DuckDB スキーマを初期化する（下記参照）

---

## 初期化（DuckDB スキーマ）

Python REPL やスクリプトで DuckDB スキーマを作成します。デフォルトの DB パスは settings.duckdb_path により決まります。

簡単な例:

from kabusys.config import settings
from kabusys.data.schema import init_schema

db_path = settings.duckdb_path  # 環境変数で上書き可能
conn = init_schema(db_path)
# conn は duckdb.DuckDBPyConnection。必要に応じて接続を保持して利用。

init_schema は既存テーブルがあればスキップ（冪等）します。

---

## 主要な使い方（API 例）

以下は代表的な操作の例です。実運用ではスケジュールやジョブ管理（cron, systemd, Airflow 等）から呼び出します。

1) 日次 ETL を実行（市場カレンダー・日足・財務の差分取得 + 品質チェック）

from datetime import date
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

2) 特徴量を生成（研究モジュールが計算した raw factors を正規化して features テーブルへ UPSERT）

from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date.today())
print(f"features updated: {n}")

3) シグナル生成（features / ai_scores / positions を参照して signals テーブルへ書き込み）

from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date.today(), threshold=0.60)
print(f"signals written: {count}")

4) ニュース収集（RSS）と DB 保存

from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)

---

## 設計上の注意事項 / ポリシー

- ルックアヘッドバイアス防止: 戦略・特徴量計算は target_date 時点の情報のみを利用する設計です。
- 冪等性: DB への保存は可能な限り ON CONFLICT（UPSERT）やトランザクションで原子性を保証します。
- セキュリティ: RSS の XML は defusedxml を利用し、SSRF や大容量応答の対策を組み込んでいます。
- レート制御: J-Quants API クライアントは固定間隔スロットリングとリトライを実装しています。
- ログ・監査: 監査テーブル（signal_events / order_requests / executions）を用い、シグナルから約定までトレースできる設計です。

---

## ディレクトリ構成

リポジトリ内の主要ファイル / モジュール（簡易一覧）:

src/kabusys/
- __init__.py
- config.py                      — 環境変数 / 設定読み込みロジック
- data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント（fetch / save / rate limit）
  - news_collector.py            — RSS 収集・保存・銘柄抽出
  - schema.py                    — DuckDB スキーマ定義と init_schema
  - stats.py                     — z-score 等の統計ユーティリティ
  - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
  - features.py                  — features の公開インターフェース
  - calendar_management.py       — market_calendar 管理（営業日判定等）
  - audit.py                     — 監査ログテーブル DDL / 初期化
- research/
  - __init__.py
  - factor_research.py           — Momentum / Volatility / Value の計算
  - feature_exploration.py       — forward returns / IC / summary / rank
- strategy/
  - __init__.py
  - feature_engineering.py       — 生ファクター統合 → features テーブル作成
  - signal_generator.py          — final_score 計算 → signals テーブル作成
- execution/
  - __init__.py                  — 発注層（今後の実装想定）
- monitoring/                     — 監視系モジュール（存在が宣言されているが詳細は別途）
（上記は代表的なファイル群。一部ファイルは他にも存在します。）

---

## 開発メモ / テスト

- 自動環境変数ロードはプロジェクトルート（.git または pyproject.toml の存在）を基準に行われます。テスト時に無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のインメモリ接続は `init_schema(":memory:")` で可能です。ユニットテストでの使い勝手が良くなります。
- ネットワーク依存部分（J-Quants API、RSS 取得）はモック可能なように設計されています（例: jquants_client._request / news_collector._urlopen のモック）。

---

この README はコードベースの主要機能と基本的な使い方をまとめたものです。実運用にあたっては戦略仕様書（StrategyModel.md 相当）やデータスキーマ設計書（DataSchema.md）を参照し、ログ出力・監視・リスク制御・証券会社 API の仕様に基づく十分なテストを行ってください。