# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（モジュール群）。  
データ収集（J-Quants）、DuckDB ベースのデータプラットフォーム、研究用ファクター計算、特徴量エンジニアリング、シグナル生成、ニュース収集、監査ログ等を含む設計済みのコンポーネント群です。

---

## 概要

KabuSys は以下の責務を分離したモジュール群で構成されています。

- データ取得・保存（J-Quants API からの株価・財務・カレンダー等）
- DuckDB を用いたスキーマ管理と永続化（Raw / Processed / Feature / Execution 層）
- 研究向けファクター計算（モメンタム / ボラティリティ / バリュー等）
- 特徴量作成（正規化・ユニバースフィルタ）と戦略シグナル生成
- ニュースの RSS 収集と銘柄紐付け
- ETL パイプライン（差分取得・品質チェック）
- 監査ログ（シグナル→注文→約定のトレーサビリティ）
- 環境変数・設定管理（.env 自動ロード対応）

設計上の特徴：
- DuckDB をデータレイク／DB として利用し、SQL と Python を組み合わせて処理を実行
- 冪等性を保つ保存ロジック（ON CONFLICT / INSERT DO UPDATE など）
- ルックアヘッドバイアス対策（target_date 時点の情報のみで計算）
- ネットワーク安全性（RSS に対する SSRF 対策等）、API レート制御、リトライ戦略

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（ページング、トークン自動リフレッシュ、レート制限、リトライ）
  - データ保存用ユーティリティ（raw_prices / raw_financials / market_calendar など）
- data/schema.py
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution）
  - init_schema() による初期化
- data/pipeline.py
  - run_daily_etl() による日次 ETL（差分取得・保存・品質チェック）
- data/news_collector.py
  - RSS 取得、前処理、記事保存、銘柄抽出（SSRF 保護、gzip サイズ制限、トラッキングパラメータ除去）
- data/calendar_management.py
  - market_calendar の管理、営業日判定ユーティリティ（next/prev/get_trading_days 等）
- data/audit.py
  - 監査ログスキーマ（signal_events, order_requests, executions 等）
- research/
  - factor_research.py：モメンタム、ボラティリティ、バリューなどのファクター計算
  - feature_exploration.py：将来リターン計算、IC（Spearman）計算、統計サマリ
- strategy/
  - feature_engineering.py：ファクター正規化・ユニバースフィルタ・features テーブルへの書き込み
  - signal_generator.py：features と ai_scores を統合して BUY/SELL シグナルを生成
- config.py
  - 環境変数管理（.env/.env.local 自動ロード、必須チェック、デフォルト値）

---

## セットアップ手順

前提
- Python 3.10 以上（`X | Y` 型ヒント等を使用）
- DuckDB を利用するためネイティブバイナリを含むパッケージのインストール可能な環境

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール
   最低限の依存例：
   - duckdb
   - defusedxml

   pip でインストール例：
   ```
   pip install duckdb defusedxml
   ```

   （プロジェクトに requirements.txt があればそれを利用してください）

3. 環境変数設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成します。config.py はプロジェクトルート（.git または pyproject.toml のある場所）を基準に自動で .env を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   必須環境変数（runtime によって ValueError が出ます）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

4. DuckDB スキーマ初期化
   Python REPL またはスクリプトで実行：
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)  # デフォルト: data/kabusys.duckdb
   ```

---

## 使い方（代表的な例）

以下はよく使うワークフローのサンプルです。実運用時はロギング設定や例外ハンドリングを追加してください。

1) 日次 ETL を実行してデータを取得・保存する
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # デフォルト: 今日の日付を対象に ETL 実行
print(result.to_dict())
```

2) 特徴量を作成（features テーブルに書き込む）
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2025, 3, 1))
print(f"features upserted: {n}")
```

3) シグナルを生成して signals テーブルへ保存
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2025, 3, 1))
print(f"signals generated: {count}")
```

4) ニュース収集ジョブの実行
```python
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9432"}  # 事前に取得した有効銘柄コードのセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

5) J-Quants から株価を差分取得（個別利用）
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings

records = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,3,1))
# DuckDB へ保存するには save_daily_quotes(conn, records)
```

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: monitoring 用 SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行モード ("development" | "paper_trading" | "live")（デフォルト development）
- LOG_LEVEL: ログレベル ("DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL")

自動 .env ロードを無効化する場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成

リポジトリ中の主なファイル/ディレクトリは次の通りです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - calendar_management.py
    - features.py
    - stats.py
    - audit.py
    - pipeline.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - monitoring/  (将来的/別モジュールとして想定)

各モジュールは役割ごとに分離されており、テストや差し替えがしやすい形になっています。例えばデータ取得と DB 保存は分離されており、テスト時は jquants_client の HTTP 呼び出しをモックできます。

---

## 注意事項 / 実運用向けのヒント

- Python バージョン: 3.10 以上を推奨
- DuckDB のファイルはバックアップやスナップショットで管理してください。大型データ保存時はディスク容量に注意。
- J-Quants API のレート制限（120 req/min）とエラーハンドリングは jquants_client に組み込まれていますが、運用時はさらにスロットリング等を監視すると良いです。
- ニュース収集は外部 RSS を取得するため、ネットワーク安全性（プロキシ・ファイアウォール）やプライベートホストへのアクセス制御に注意してください。
- 本リポジトリは取引ロジック／資金管理を含みます。実口座での運用はリスクが伴うため、必ず paper_trading モードで十分検証してください（KABUSYS_ENV）。

---

## 貢献・開発

- バグ修正や機能追加は Pull Request を歓迎します。設計原則（冪等性・ルックアヘッド対策・トレーサビリティ）を崩さないようにしてください。
- 単体テスト・インテグレーションテストを整備してから PR を出すとレビューがスムーズです。

---

この README はコードベースの要点をまとめたものです。詳細な API の使用法や設計ドキュメント（StrategyModel.md, DataPlatform.md 等）が存在する想定で、そちらも併せて参照してください。必要であれば README に追記する用の「例: systemd タイマー構成」「CI/CD（DB マイグレーション）」などの運用手順も作成できます。