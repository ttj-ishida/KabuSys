# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリ。  
DuckDB を用いたデータレイヤ、J-Quants API からの ETL、RSS ニュース収集、ファクター計算（Research）や監査ログなどを備えた設計です。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムに必要な下記機能群を提供する Python パッケージです。

- J-Quants API を用いたマーケットデータ（株価・財務・マーケットカレンダー）取得と DuckDB への永続化
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- RSS ベースのニュース収集と記事→銘柄紐付け
- Research 向けのファクター計算（モメンタム・ボラティリティ・バリュー等）と統計ユーティリティ
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 監査ログ（signal → order → execution のトレース用スキーマ）
- 設定は環境変数 / .env ファイルで管理（自動ロード機能あり）

パッケージは modulized に設計されており、data / research / strategy / execution / monitoring 等のサブパッケージで責務を分離しています。

---

## 主な機能一覧

- data
  - jquants_client: API クライアント（レート制限・リトライ・トークンリフレッシュ対応）、DuckDB への保存関数
  - pipeline / etl: 日次差分 ETL（市場カレンダー → 株価 → 財務）、バックフィル、品質チェック
  - schema / audit: DuckDB スキーマ定義と初期化、監査ログ用スキーマ
  - news_collector: RSS 取得（SSRF 対策、gzip 上限、XML 安全パーサ）、記事保存と銘柄抽出
  - quality: データ品質チェック（欠損、重複、スパイク、日付不整合）
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - stats / features: Zスコア正規化など統計ユーティリティ
- research
  - factor_research: mom/volatility/value 等のファクター計算（DuckDB を参照）
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
- config
  - Settings クラスで環境変数を一元管理（必須項目は取得時に検証）
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込む仕組み（無効化可能）
- audit/監査
  - signal_events / order_requests / executions 等の監査テーブルとインデックス

---

## 必要な環境変数

以下はコードから参照される主な環境変数です（必須は README 内で明記）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注機能を使う場合）
- SLACK_BOT_TOKEN — Slack 通知用トークン（通知機能がある場合）
- SLACK_CHANNEL_ID — Slack チャネル ID

オプション（デフォルトあり）:
- KABUSYS_ENV — 実行環境 ("development", "paper_trading", "live")。デフォルト "development"
- LOG_LEVEL — ログレベル ("DEBUG","INFO","...")。デフォルト "INFO"
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB 等）パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する場合は `1` を設定

.env ファイルの自動読み込みは、プロジェクトルート（.git または pyproject.toml を基準）から `.env` → `.env.local` の順に行われます。`.env.local` は上書き許可。

例（.env）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python の準備
   - 推奨: Python 3.9+（typing などを使用）
2. パッケージのインストール
   - 最低限必要なライブラリ:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - 実行時に追加ライブラリが必要な場合は適宜インストールしてください（HTTP クライアント等は標準 urllib を利用しています）。
3. リポジトリをクローンし、環境変数を設定
   - プロジェクトルートに `.env` を配置するか、環境変数をエクスポートしてください。
4. DuckDB スキーマの初期化
   - 例: Python REPL / スクリプト内で
     ```
     from kabusys.data import schema
     from kabusys.config import settings

     conn = schema.init_schema(settings.duckdb_path)
     ```
   - :memory: を指定するとインメモリ DB を使用できます（テスト等）。

---

## 使い方（基本例）

以下は主要ユースケースの簡単な使用例です。

1) 日次 ETL を実行する
```
from datetime import date
import duckdb
from kabusys.data import schema, pipeline
from kabusys.config import settings

# スキーマ初期化（既存ならスキップ）
conn = schema.init_schema(settings.duckdb_path)

# 当日分 ETL を実行（id_token を省略すると設定されたリフレッシュトークンで自動取得）
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) RSS ニュース収集ジョブを回す
```
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
known_codes = {"7203", "6758", "9984"}  # 自分で管理する有効銘柄一覧
res = run_news_collection(conn, sources=None, known_codes=known_codes)
print(res)  # {source_name: saved_count}
```

3) ファクター計算（Research）
```
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect(str(settings.duckdb_path))
target = date(2025, 1, 15)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
# z-score 正規化などは kabusys.data.stats.zscore_normalize を利用
```

4) 監査スキーマの初期化
```
from kabusys.data import audit, schema
conn = schema.init_schema(settings.duckdb_path)
audit.init_audit_schema(conn, transactional=True)
```

---

## 実装上のポイント / 注意点

- J-Quants クライアント
  - レート制限 (120 req/min) を固定間隔スロットリングで守る実装
  - 401 受信時はリフレッシュトークンで自動再取得（1回のみ）
  - ページネーション対応
  - DuckDB へは冪等的に保存（ON CONFLICT ... DO UPDATE / DO NOTHING）する

- News Collector
  - defusedxml を使った安全な XML パース
  - SSRF 対策（スキームチェック / ホストがプライベートか否か検査 / リダイレクト検査）
  - 受信サイズ上限・gzip 保護（Gzip bomb 対策）
  - 記事 ID は正規化 URL の SHA-256 の先頭 32 文字で生成

- データ品質チェック
  - Fail-Fast ではなく全チェックを収集して呼び出し元に返す設計
  - スパイク検出や日付整合性チェックを提供

- カレンダー管理
  - market_calendar が存在しない場合は土日フォールバックで営業日判定
  - DB にカレンダーがある場合は DB 値を優先

- Settings
  - 環境変数の自動読み込みはプロジェクトルートを基準に .env / .env.local を順に読み込む
  - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）
- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - etl.py
    - features.py
    - stats.py
    - quality.py
    - calendar_management.py
    - audit.py
    - pipeline.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

各ファイルの役割は上の機能一覧と README 内容を参照してください。

---

## 追加情報 / 今後の拡張候補

- strategy / execution 層の具体的な発注ロジック・ブローカー接続の実装（kabuステーション統合）
- Slack 通知や監視用ダッシュボード統合（monitoring パッケージ）
- テストスイート（ユニットテスト・統合テスト）と CI での自動実行
- Docker イメージ化やデプロイ用の運用手順ドキュメント

---

ご不明点や README に追記したい利用シナリオ（例: バックテスト、運用時の cron 設定等）があれば教えてください。必要に応じてサンプルスクリプトや requirements.txt 例も追加します。