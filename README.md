# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォームです。  
DuckDB をデータレイヤーに用い、J-Quants API と RSS ニュースを取り込み、特徴量生成・シグナル生成・発注監査までの主要機能を含む設計になっています。

バージョン: 0.1.0

---

## 概要

このリポジトリは以下の機能を持つ Python パッケージ（src/kabusys）です。

- J-Quants API から株価・財務・カレンダー等を取得して DuckDB に保存（差分取得、ページネーション、リトライ、レートリミット対応）
- RSS ベースのニュース収集と記事の前処理・銘柄紐付け
- 研究（research）で生成した生ファクターを正規化して特徴量（features）を作成
- features と AI スコアを統合して売買シグナルを生成（BUY / SELL）
- DuckDB 上のスキーマ定義・初期化・ETL パイプライン・カレンダー管理等のユーティリティ
- 監査（audit）テーブル群によりシグナル→発注→約定のトレーサビリティを確保

設計上のポイント:
- ルックアヘッドバイアスの排除（必ず target_date 時点のデータのみ使用）
- 冪等性（DB 保存は ON CONFLICT / DO UPDATE などで上書き可能）
- ネットワーク・XML・SSRF に対する安全対策（HTTP リトライ、XML パーサ保護、URL 検証等）

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（トークン自動リフレッシュ、レートリミット、リトライ）
  - fetch/save: 日足・財務・カレンダー取得と DuckDB への冪等保存
- data/schema.py
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution 層）と初期化
- data/pipeline.py
  - 日次 ETL（差分取得、backfill、品質チェック）と個別 ETL ジョブ
- data/news_collector.py
  - RSS 取得、前処理、記事保存、記事⇄銘柄の紐付け（SSRF 対策・gzip 制限等）
- data/calendar_management.py
  - market_calendar 管理、営業日判定、next/prev_trading_day 等のユーティリティ
- research/*
  - factor 計算（momentum / volatility / value）や特徴量探索（forward returns, IC, summary）
- strategy/feature_engineering.py
  - 生ファクターのマージ・ユニバースフィルタ・Zスコア正規化・features テーブルへの書き込み
- strategy/signal_generator.py
  - features / ai_scores / positions を元に最終スコアを計算し BUY/SELL シグナルを生成・signals テーブルへ保存
- data/news_collector.py
  - RSS 収集 & raw_news 保存、ニュース→銘柄抽出

---

## 要求事項（推奨）

- Python 3.10+（型注釈に union 型 | を使用）
- 必要なライブラリ（最低限）:
  - duckdb
  - defusedxml

（プロジェクトに pyproject.toml / requirements.txt がある想定の場合はそちらを利用してください）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb>=0.7" defusedxml
# 開発中なら: pip install -e .
```

---

## 環境変数（.env）

自動ロード機能は package 起動時にプロジェクトルートの `.env` / `.env.local` を読み込みます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

必須（Settings._require を通して参照される）
- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン
- KABU_API_PASSWORD：kabuステーション 等の API パスワード
- SLACK_BOT_TOKEN：Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID：通知先チャンネル ID

任意 / デフォルトあり
- KABUSYS_ENV：development / paper_trading / live（デフォルト: development）
- LOG_LEVEL：DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- DUCKDB_PATH：DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH：モニタリング DB パス（デフォルト: data/monitoring.db）

例 (`.env.example`):
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローンしてワークスペースを用意
2. 仮想環境作成・依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb defusedxml
   # その他必要なパッケージがあれば追加
   ```
3. `.env` を作成して環境変数を設定（上記参照）
4. DuckDB スキーマ初期化（最初の一度）
   Python REPL やスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings
   conn = init_schema(settings.duckdb_path)
   # conn を使ってそのまま ETL/処理を実行できます
   ```
   - インメモリ DB を試す場合は `":memory:"` を渡せます。

---

## 使い方（主要ワークフロー例）

以下は最小限のサンプルコード例です。実運用ではロギング設定・例外処理を適切に追加してください。

- 日次 ETL（市場カレンダー・日足・財務の差分取得）
```python
from datetime import date
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # 初回のみ。既存 DB は上書きしない。
result = run_daily_etl(conn, target_date=date.today())  # ETLResult を返す
print(result.to_dict())
```

- 特徴量生成（features テーブルへの書き込み）
```python
from datetime import date
from kabusys.data.schema import get_connection, init_schema
from kabusys.strategy import build_features
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)  # 既存 DB に接続
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

- シグナル生成（signals テーブルへの書き込み）
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
n = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {n}")
```

- RSS ニュース収集
```python
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- カレンダーの夜間更新ジョブ
```python
from kabusys.data.schema import get_connection
from kabusys.data.calendar_management import calendar_update_job

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

---

## よく使うユーティリティ

- jquants_client.get_id_token(): リフレッシュトークンから ID トークンを取得
- data.schema.init_schema(db_path): DuckDB スキーマ初期化（冪等）
- data.pipeline.run_daily_etl(...): 日次 ETL の統合エントリポイント
- strategy.build_features(conn, target_date): features 作成
- strategy.generate_signals(conn, target_date): signals 作成
- news_collector.fetch_rss / save_raw_news / run_news_collection: ニュース収集

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ初期化、version 情報
- config.py — 環境変数 / 設定管理（Settings）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save）
  - news_collector.py — RSS 収集・前処理・DB 保存
  - schema.py — DuckDB スキーマ定義と init_schema
  - pipeline.py — ETL パイプライン、run_daily_etl 等
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - calendar_management.py — market_calendar 管理、営業日ユーティリティ
  - audit.py — 発注／約定の監査テーブル DDL（部分）
- research/
  - __init__.py
  - factor_research.py — momentum / volatility / value の計算
  - feature_exploration.py — forward returns / IC / summary 等
- strategy/
  - __init__.py
  - feature_engineering.py — features の構築（正規化・ユニバースフィルタ）
  - signal_generator.py — final_score 計算・BUY/SELL シグナル作成
- execution/ — 発注関連の実装用プレースホルダ（将来的な実装）
- monitoring/ — モニタリング DB 用ユーティリティ（実装ファイルは本コードには含まれている想定）

（上記はリポジトリ内の主なモジュールの抜粋説明です）

---

## 開発上の注意 / トラブルシューティング

- 自動で `.env` をロードする処理はプロジェクトルート（pyproject.toml か .git）が基準です。テスト等で自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の初回初期化時に parent ディレクトリが自動作成されます（schema.init_schema）。
- J-Quants API のレート制限・リトライは内蔵されていますが、実行環境のネットワーク状況に応じてタイムアウトや待ち時間が発生します。
- news_collector は外部 RSS をダウンロードします。SSRF 対策や最大レスポンスサイズの制限を実装していますが、実環境ではプロキシやアクセス制限を検討してください。
- strategy 層は発注・execution 層に依存しません。シグナルは signals テーブルへ出力され、発注部分は別モジュールで実装する想定です。

---

## 今後の拡張案（参考）

- execution 層の具体的なブローカー連携（kabuステーション等）実装
- リアルタイム監視・アラート（Slack 通知）の統合
- テストカバレッジ・CI の整備
- ai_scores の自動生成（外部 ML パイプライン連携）

---

必要であれば、README に以下を追加できます:
- フル API リファレンス（関数・引数一覧）
- より具体的な運用手順（Cron/airflow でのスケジュール化例）
- 例外発生時のログ例と復旧手順

追加して欲しい項目があれば教えてください。