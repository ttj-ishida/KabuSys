# KabuSys

日本株向けの自動売買プラットフォームのコアライブラリです。  
データ取得（J-Quants）→ ETL → 特徴量生成 → シグナル生成 → 発注／監査ログまでを想定したモジュール群を含みます。  
（本リポジトリはライブラリ層で、実際の運用ジョブやインフラは別途用意してください）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の責務を持つモジュール群を提供します：

- J-Quants API クライアント（データ取得・保存の冪等処理、レートリミット・リトライ実装）
- DuckDB ベースのデータスキーマ定義と初期化
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェックのフロー）
- 研究（research）向けのファクター計算・特徴量探索ユーティリティ
- 戦略層：特徴量正規化（feature engineering）とシグナル生成（signal generation）
- ニュース収集（RSS）と銘柄紐付け
- マーケットカレンダー管理、監査ログ（発注〜約定のトレーサビリティ）など

設計方針として、ルックアヘッドバイアス回避、冪等性（ON CONFLICT）、API レート制御、エラー分離（各ステップは独立して例外処理）を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants からの株価・財務・カレンダー取得、DuckDB への保存（save_*）
  - schema: DuckDB スキーマ定義と init_schema/get_connection
  - pipeline: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - news_collector: RSS 取得・前処理・DB 保存・銘柄抽出
  - calendar_management: 営業日判定・next/prev_trading_day・calendar_update_job
  - stats: zscore_normalize 等の統計ユーティリティ
- research/
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー
- strategy/
  - feature_engineering.build_features: raw ファクターを正規化して features テーブルへ保存
  - signal_generator.generate_signals: features と ai_scores を統合して BUY/SELL シグナルを作成
- config: .env 自動読み込み（プロジェクトルート検出）と Settings（環境変数管理）

---

## セットアップ手順

前提
- Python 3.10+（typing の構文や型注釈を想定）
- DuckDB の Python バインディングを使用

1. リポジトリをクローンしてパッケージをインストール（開発モード推奨）
   ```
   git clone <repo-url>
   cd <repo>
   pip install -e .
   ```

2. 必要な依存ライブラリ（例）
   ```
   pip install duckdb defusedxml
   ```
   （実際の requirements はプロジェクトで管理してください）

3. 環境変数の準備
   プロジェクトルートに `.env`（または `.env.local`）を置くと自動ロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   主要な必須環境変数（Settings クラス参照）:
   - JQUANTS_REFRESH_TOKEN : J-Quants の refresh token
   - KABU_API_PASSWORD     : kabu ステーション（発注API）パスワード
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      : Slack チャンネル ID

   任意/デフォルト値:
   - KABUSYS_ENV           : development | paper_trading | live（default: development）
   - LOG_LEVEL             : DEBUG | INFO | WARNING | ERROR | CRITICAL（default: INFO）
   - KABU_API_BASE_URL     : 発注 API の base URL（default: http://localhost:18080/kabusapi）
   - DUCKDB_PATH           : DuckDB ファイルパス（default: data/kabusys.duckdb）
   - SQLITE_PATH           : 監視 DB 等で使用（default: data/monitoring.db）

   例 `.env`（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=yourpass
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データベース初期化
   DuckDB スキーマを作成します（親ディレクトリが無ければ自動作成されます）。
   Python REPL やスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)  # または init_schema("data/kabusys.duckdb")
   ```

---

## 基本的な使い方（例）

以下は主要ワークフローの簡単な例です。実運用ではロギング・例外ハンドリング・ジョブスケジューラ（cron / Airflow 等）を追加してください。

1) 日次 ETL を実行してデータを更新する
```python
from kabusys.data.schema import get_connection, init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
from datetime import date

# DB 初期化（初回のみ）
conn = init_schema(settings.duckdb_path)

# 当日分の ETL を実行
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量（features）を構築する
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection(settings.duckdb_path)
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

3) シグナルを生成する
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection(settings.duckdb_path)
count = generate_signals(conn, target_date=date.today(), threshold=0.60)
print(f"signals written: {count}")
```

4) ニュース収集ジョブ（RSS から raw_news を収集して銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)

# known_codes: 有効な銘柄コードセット（extract_stock_codes に使用）
known_codes = {"7203", "6758", "9984", ...}
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

5) カレンダー更新（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意:
- これら関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。
- 実運用ではトランザクションの取り扱い、ログ出力、エラー通知（Slack等）を追加してください。

---

## 環境変数（要約）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

推奨 / 任意:
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (INFO など)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env ロードを無効化します（テスト用途）

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数/設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（fetch / save / rate limit / retry）
    - schema.py             — DuckDB スキーマ定義と init_schema/get_connection
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - news_collector.py     — RSS 収集・前処理・DB 保存・銘柄抽出
    - calendar_management.py— マーケットカレンダー管理（営業日判定等）
    - stats.py              — zscore_normalize など統計ユーティリティ
    - features.py           — データ層の feature utils（再エクスポート）
    - audit.py              — 監査ログ用スキーマ / 初期化（発注〜約定トレーサビリティ）
    - pipeline_quality*     — （品質チェックモジュールと連携、quality は別ファイル想定）
  - research/
    - __init__.py
    - factor_research.py    — モメンタム/ボラティリティ/バリューの定量ファクター
    - feature_exploration.py— 将来リターン、IC、summary、rank 等
  - strategy/
    - __init__.py
    - feature_engineering.py— ファクター正規化 → features テーブルへの UPSERT
    - signal_generator.py   — final_score の計算と BUY/SELL シグナル生成
  - execution/              — 発注/実行ロジック（空の __init__ として分離済）
  - monitoring/             — 監視・メトリクス収集（別途実装想定）
  - その他: README（本ファイル）、pyproject.toml 等

（上記はコードベースの一部を抜粋した構成の要約です）

---

## 開発上の注意点 / 設計上のポイント

- ルックアヘッドバイアス回避: features・signals 等は target_date 時点での情報のみを使う設計
- 冪等性: DB 保存関数は基本的に ON CONFLICT を使った上書き/スキップで安全に再実行可能
- レート制御とリトライ: J-Quants クライアントは固定間隔スロットリングと指数バックオフを実装
- セキュリティ: RSS の SSRF/ローカルアクセス対策、defusedxml による XML 攻撃対策が組み込まれている
- テスト容易性: id_token 注入や _urlopen の差し替えポイントなど、モックしやすい設計

---

## 参考・今後の拡張案

- execution 層のブローカー統合（kabu API への実際の注文送信）
- リスク管理（ポジション制限、ドローダウン制限、トレードサイズ決定ロジック）
- AI スコアの算出パイプラインとモデル管理
- サービス化（API 層 / Web UI / スケジューラ連携）

---

もし README に追記したいサンプルスクリプト、環境構築用の docker-compose、あるいは具体的な運用手順（cron / systemd / Airflow）のテンプレートが必要であれば教えてください。必要に応じて日本語での運用マニュアルも作成できます。