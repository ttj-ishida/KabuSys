# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。J-Quants API や RSS ニュースからデータを取得・保存し、特徴量（features）を作成、シグナル生成、発注・監視レイヤのためのスキーマとユーティリティを提供します。

主な設計方針:
- ルックアヘッドバイアス対策（計算は target_date 時点のデータのみを使用）
- 冪等性（DB 保存は ON CONFLICT / トランザクションで保護）
- ネットワーク安全性（news の SSRF 防止・サイズ制限）と API レート制御
- 研究（research）・本番（execution）レイヤの分離

---

## 機能一覧

- データ収集
  - J-Quants API クライアント（株価・財務・カレンダー取得、認証・自動リフレッシュ、リトライ、レートリミット）
  - RSS 取得・前処理・ニュース保存（SSRF/サイズ安全策、記事ID正規化、銘柄抽出）
- ETL パイプライン
  - 差分取得（バックフィル対応）、保存（冪等）、品質チェックと日次 ETL エントリポイント
  - JPX マーケットカレンダー更新ジョブ
- データベース
  - DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- 研究・特徴量
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を使用）
  - Z スコア正規化ユーティリティ
  - 将来リターン計算・IC（Spearman）・統計サマリー
- 戦略
  - 特徴量を作成して features テーブルへ保存（build_features）
  - features と ai_scores を統合してシグナル生成（generate_signals）
  - 保有ポジションのエグジット判定（ストップロス等）
- 監査・発注用スキーマ（audit / execution 層のテーブル定義）

---

## 要件（推奨）

- Python 3.9+ （typing の一部が使われています）
- duckdb
- defusedxml
- （標準ライブラリのみを用いるモジュールが多いですが、依存パッケージはプロジェクトの requirements.txt を参照してください）

例（pip）:
pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをクローン・配置
2. Python 仮想環境を作成して有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
3. 必要パッケージをインストール
   pip install duckdb defusedxml
4. 環境変数の準備（.env ファイルをプロジェクトルートに配置）
   - 自動ロード: package はプロジェクトルート（.git または pyproject.toml）を検出して `.env` / `.env.local` を自動で読み込みます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

推奨する .env（例）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルト）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 初期 DB の作成（DuckDB スキーマ初期化）

Python REPL またはスクリプトから DuckDB を初期化します:

from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# 返り値は duckdb.DuckDBPyConnection

- ":memory:" を渡すとインメモリ DB を使用できます。
- init_schema はテーブル作成を冪等に行います（既存テーブルは上書きされません）。

---

## 使い方

以下は代表的なユースケースのサンプルです。

1) 日次 ETL を実行（株価・財務・カレンダー取得と品質チェック）
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

2) 特徴量を作成して features テーブルへ保存
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2025, 1, 31))
print(f"features upserted: {n}")

3) シグナル生成（features / ai_scores / positions を参照）
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2025, 1, 31))
print(f"signals written: {count}")

4) RSS ニュース収集ジョブ（news の収集と保存）
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9437"}  # 既知の銘柄コードセット（抽出用）
results = run_news_collection(conn, known_codes=known_codes)
print(results)

5) カレンダーを更新する夜間ジョブ
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)

注意:
- J-Quants API 呼び出しにはリトライ・レートリミット制御が組み込まれています。
- fetch 系関数はページネーションに対応しており、save_* 系は冪等に保存します。
- generate_signals は戦略モデルの重み（weights）や閾値（threshold）を引数で変更可能です。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須) : J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) : kabuステーション API パスワード
- KABU_API_BASE_URL (任意) : kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) : Slack 通知先チャネルID
- DUCKDB_PATH (任意) : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意) : 監視用 sqlite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV (任意) : execution 環境 (development | paper_trading | live)。デフォルト development
- LOG_LEVEL (任意) : ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

設定は .env / .env.local から自動読み込みされます（プロジェクトルート自動検出）。テストなどで自動読み込みを抑止するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
  - パッケージ初期化とバージョン定義（__version__ = "0.1.0"）
- config.py
  - 環境変数管理（.env 読み込み、Settings クラス）
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（認証、レート制御、fetch/save）
  - news_collector.py
    - RSS フェッチ、前処理、raw_news 保存、銘柄抽出（SSRF 保護、サイズ制限）
  - schema.py
    - DuckDB スキーマ（Raw / Processed / Feature / Execution）と初期化関数 init_schema
  - stats.py
    - zscore_normalize（クロスセクション Z スコア正規化）
  - pipeline.py
    - ETL ジョブ実装（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - calendar_management.py
    - カレンダー管理・更新ジョブ
  - audit.py
    - 発注・約定の監査テーブル DDL（order_requests, signal_events, executions 等）
  - features.py
    - data.stats の公開再エクスポート
- research/
  - __init__.py
  - factor_research.py
    - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials 使用）
  - feature_exploration.py
    - 将来リターン計算, IC, 統計サマリー, rank
- strategy/
  - __init__.py
    - build_features, generate_signals をエクスポート
  - feature_engineering.py
    - 生ファクターの統合・フィルタリング・正規化・features への UPSERT
  - signal_generator.py
    - final_score 計算、BUY/SELL 判定、signals テーブルへの書き込み
- execution/
  - (発注実装用のプレースホルダ)
- monitoring/
  - (監視ロジック・DB 連携用のユーティリティ等)
- その他: 各モジュールはログ出力・エラーハンドリング・トランザクション保護を重視して実装されています。

---

## 開発上の注意点 / 実装メモ

- news_collector は外部 XML を処理するため defusedxml を使用して XML 攻撃を防いでいます。HTTP レスポンスは最大サイズで束縛してメモリ DoS を防ぎます。リダイレクト先のプライベート IP へのアクセスは拒否します（SSRF 対策）。
- jquants_client は固定間隔スロットリング（120 req/min）と指数バックオフのリトライを組み合わせています。401 が返った場合はリフレッシュトークンで id_token を再取得して 1 回だけ再試行します。
- DuckDB への保存は可能な限り ON CONFLICT（冪等）かつトランザクションで実装しています。
- ファクター計算・シグナル生成はルックアヘッドバイアスを回避するため target_date 時点の利用可能データのみで計算します。
- 設定のバリデーション（KABUSYS_ENV, LOG_LEVEL 等）は config.Settings で行われます。

---

## 貢献 / ライセンス

本 README では具体的な貢献手順やライセンスファイルは含まれていません。変更・提案がある場合はリポジトリの CONTRIBUTING.md / LICENSE を参照してください（存在する場合）。

---

この README はコードベースから抽出した主要な使い方と構成の概要です。実運用では API キー・パスワードの管理、監視・アラート、運用テスト（ペーパートレード）等を別途整備してください。