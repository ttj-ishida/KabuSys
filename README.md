# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。J-Quants から市場データを取得して DuckDB に保存し、研究（research）で作成したファクターを正規化・統合して戦略シグナルを生成します。監査ログ・実行レイヤーも備え、ETL → 特徴量生成 → シグナル生成 → 発注のワークフローを想定した設計になっています。

バージョン: 0.1.0

---

## 主要機能

- J-Quants API クライアント
  - 日足（OHLCV）・財務データ・市場カレンダーの取得（ページネーション対応、トークン自動リフレッシュ、リトライ、レートリミット制御）
  - DuckDB への冪等的保存（ON CONFLICT による上書き）
- ETL パイプライン
  - 日次差分取得（バックフィル対応）、市場カレンダー先読み
  - 品質チェック連携（quality モジュール）
- データスキーマ管理
  - DuckDB 用スキーマの初期化・接続ユーティリティ
  - Raw / Processed / Feature / Execution 層のテーブル定義
- 特徴量計算（research）
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - z-score 正規化ユーティリティ
- 特徴量エンジニアリング（strategy）
  - 研究で作成した生ファクターを結合・フィルタリング・正規化して features テーブルへ UPSERT（冪等）
- シグナル生成（strategy）
  - features と ai_scores を統合して final_score を算出
  - Bear レジーム判定、BUY/SELL シグナル生成、既存ポジションのエグジット判定
  - signals テーブルへの日付単位置換（トランザクションで原子性を保証）
- ニュース収集（data.news_collector）
  - RSS 取得、前処理、raw_news 保存、銘柄コード抽出と紐付け
  - SSRF/サイズ/圧縮/XML攻撃対策を考慮した実装
- 市場カレンダー管理（calendar_management）
  - 営業日判定、next/prev trading day、期間の営業日取得、夜間カレンダー更新ジョブ

---

## 要件

- Python 3.10+
- 依存ライブラリ（代表）
  - duckdb
  - defusedxml
  - （標準ライブラリ以外の依存は setup / requirements に合わせてインストールしてください）

※ このリポジトリには requirements.txt / pyproject.toml が含まれる想定です。ローカルでは仮想環境の作成を推奨します。

---

## セットアップ手順（ローカル）

1. リポジトリをクローンして仮想環境を作成・有効化
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

2. 依存をインストール
   - pip install -r requirements.txt
   - または develop インストール: pip install -e .

3. 環境変数を設定
   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。

   主な環境変数（必須は README の該当箇所参照）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL : kabu API のベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN : Slack 通知用トークン（必須）
   - SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH : SQLite 監視 DB（デフォルト data/monitoring.db）
   - KABUSYS_ENV : development / paper_trading / live（デフォルト development）
   - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 初期化（DuckDB スキーマ作成）

Python REPL またはスクリプトで DuckDB スキーマを初期化します。

例:
```
from kabusys.data.schema import init_schema
init_schema("data/kabusys.duckdb")
```

- db_path に ":memory:" を指定するとインメモリ DB を使えます。
- init_schema は冪等なので既存テーブルがあればスキップされます。

---

## 基本的な使い方（主要 API）

以下は代表的な呼び出し例です。アプリケーション側でジョブスケジューラ（cron / Airflow 等）から呼ぶ想定です。

- 日次 ETL を実行（市場カレンダー/株価/財務の差分取得・保存）
```
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量（features）を構築（対象日は ETL の取込後の営業日）
```
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2025, 1, 15))
print(f"upserted features: {n}")
```

- シグナル生成（features と ai_scores を統合して signals テーブルへ）
```
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date(2025, 1, 15))
print(f"generated signals: {total}")
```

- ニュース収集ジョブ（RSS から raw_news 保存 + news_symbols 紐付け）
```
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
results = run_news_collection(conn, known_codes={"7203","6758"})
print(results)  # {source_name: saved_count}
```

- カレンダー更新ジョブ（夜間バッチ）
```
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved calendar rows: {saved}")
```

---

## 実装上のポイント / 注意事項

- 型ヒントに Python 3.10+ の構文（|）を使用しています。Python バージョンに注意してください。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行います。テスト環境などで自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API に対するリトライ/レートリミット/401 トークンリフレッシュは jquants_client が管理します。大量取得時はレートリミットに注意してください（デフォルト 120 req/min）。
- features / signals の処理は「ルックアヘッドバイアス防止」を意識して target_date 時点のデータのみを参照する実装になっています。
- DuckDB への挿入は基本的にトランザクション + ON CONFLICT を用いた冪等性を確保する方式です。
- news_collector は SSRF / XML Bomb / レスポンスサイズなどに対する安全対策を組み込んでいますが、外部 RSS の扱いには慎重に。

---

## ディレクトリ構成

主要ファイル／ディレクトリの説明:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（J-Quants トークン、Kabu API、Slack、DB パスなど）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ユーティリティ）
    - schema.py
      - DuckDB スキーマ定義・init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
    - news_collector.py
      - RSS 取得・解析・DB 保存・銘柄抽出
    - calendar_management.py
      - 市場カレンダー管理・営業日判定・夜間更新ジョブ
    - audit.py
      - 監査ログ／トレーサビリティ（order_requests / executions 等の DDL）
    - features.py
      - data.stats のエクスポート
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py
      - momentum / volatility / value 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算 / IC 計算 / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py
      - 研究で計算した生ファクターを統合・正規化して features に保存
    - signal_generator.py
      - final_score を算出し BUY/SELL シグナルを生成して signals に保存
  - execution/
    - (発注・ブローカー連携層。現コードベースでは空のパッケージ)
  - monitoring/
    - (監視・メトリクス・Slack 通知等のモジュールを想定)

---

## 開発 / 貢献

- コードスタイル・テスト・CI はプロジェクトの方針に従ってください。
- 重要な変更（スキーマ・表定義・ETL ロジック等）は DataSchema.md / DataPlatform.md / StrategyModel.md に整合するよう更新してください（リポジトリ内の設計ドキュメントに従うことを想定しています）。

---

## 問い合わせ

バグ報告・改善提案は Issue を作成してください。README の記載は実装に基づく概要であり、詳細な設計・仕様はプロジェクト内の設計ドキュメントを参照してください。

--- 

（この README は提供されたコードベースのソースから生成しています。実際の運用やデプロイ手順は環境に合わせて調整してください。）