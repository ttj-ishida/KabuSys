# KabuSys

日本株向けの自動売買／データ基盤ライブラリ KabuSys のリポジトリ用 README（日本語）。

概要、主要機能、セットアップ手順、基本的な使い方およびディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株を対象としたデータ収集・ETL、特徴量作成、戦略シグナル生成、ニュース収集、監査ログ／実行レイヤを備えた自動売買プラットフォーム向けの Python ライブラリ群です。  
主な設計方針は以下のとおりです。

- DuckDB をローカル DB として用いることで大規模データを効率的に扱う
- 取得データは冪等に保存（ON CONFLICT / INSERT ... DO UPDATE 等）
- ルックアヘッドバイアスを防ぐために「target_date 時点で利用可能なデータのみ」を使用
- 外部 API 呼び出しは限定し、発注層（execution）への直接依存は持たない（分離）

現在のバージョン: 0.1.0（パッケージメタ情報は src/kabusys/__init__.py を参照）

---

## 機能一覧（概要）

- data/jquants_client.py
  - J-Quants API クライアント（株価、財務、マーケットカレンダー取得）
  - レート制御・リトライ・トークン自動リフレッシュ機能付き
  - DuckDB へ冪等保存する save_* 関数群
- data/schema.py
  - DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
  - init_schema, get_connection を提供
- data/pipeline.py
  - 日次 ETL（run_daily_etl）および個別 ETL ジョブ（株価・財務・カレンダー）
  - 差分更新／バックフィル／品質チェック呼び出しの統合
- data/news_collector.py
  - RSS 収集、記事正規化、重複排除、DB 保存、銘柄抽出
  - SSRF 対策、受信サイズ制限、XML パースの堅牢化
- data/calendar_management.py
  - JPX カレンダー管理（営業日判定、next/prev trading day 等）
- data/audit.py
  - 発注〜約定までの監査ログ用スキーマ・初期化ロジック
- data/stats.py
  - zscore_normalize（クロスセクション Z スコア正規化）などの統計ユーティリティ
- research/*
  - factor_research.py：Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py：将来リターン計算、IC（Spearman）計算、統計サマリー
- strategy/*
  - feature_engineering.py：research 結果を取り込み features テーブルへ正規化保存
  - signal_generator.py：features + ai_scores を統合して BUY/SELL シグナルを生成
- config.py
  - 環境変数管理（.env の自動ロード、必須設定チェック、環境フラグなど）

---

## 動作要件（最低限）

- Python 3.10+
  - （コードでは型注釈で union | を利用しているため Python 3.10 以上を推奨）
- 主要依存パッケージ
  - duckdb
  - defusedxml

インストールはプロジェクトの requirements.txt / pyproject.toml を参照してください（存在する場合）。

例（pip）:
pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト

2. 仮想環境を作成・有効化（任意）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージのインストール
   pip install duckdb defusedxml

4. 環境変数の設定
   プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（src/kabusys/config.py の実装による）。テストやスクリプト実行時に自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な必須環境変数（Settings で必須とされているもの）:
   - JQUANTS_REFRESH_TOKEN : J-Quants API のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API パスワード（発注層利用時）
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（任意の通知機能に必要）
   - SLACK_CHANNEL_ID      : Slack チャネル ID

   その他の設定（省略可、デフォルトあり）:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db

5. DuckDB スキーマ初期化
   以下のようにして DB を初期化します（例: Python スクリプト実行や REPL）。
   from kabusys.data.schema import init_schema, get_connection
   conn = init_schema("data/kabusys.duckdb")

   init_schema は存在しない親ディレクトリを自動作成し、必要な全テーブルとインデックスを作成します（冪等）。

---

## 使い方（クイックスタート）

以下は主要処理を順に実行する最小例です。実運用ではジョブスケジューラ（cron, Airflow 等）や監視を組み合わせます。

1) DB 初期化（1 回）
```
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（株価・財務・カレンダーの差分取得）
```
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を省略すると today（ただしカレンダー調整あり）
print(result.to_dict())
```

3) 特徴量作成（features テーブルを作成）
```
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2025, 1, 17))
print(f"features upserted: {count}")
```

4) シグナル生成（features と ai_scores 参照）
```
from datetime import date
from kabusys.strategy import generate_signals
conn = get_connection("data/kabusys.duckdb")
n = generate_signals(conn, target_date=date(2025, 1, 17))
print(f"signals written: {n}")
```

5) ニュース収集ジョブ（RSS 収集 → raw_news 保存 → 銘柄紐付け）
```
from kabusys.data.news_collector import run_news_collection
conn = get_connection("data/kabusys.duckdb")
results = run_news_collection(conn, known_codes={"7203","6758","9432"})
print(results)
```

6) カレンダー更新ジョブ（夜間バッチ）
```
from kabusys.data.calendar_management import calendar_update_job
conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意:
- run_daily_etl 等の関数はエラーハンドリングを行いますが、API トークンやネットワーク状態に依存します。ログ出力や監視を併用してください。
- 発注 / 実行層（kabuAPI 等）との接続や実際の発注処理は execution パッケージ側を実装する必要があります（this codebase は発注 API への直接依存を最小化しています）。

---

## 主要 API（抜粋）

- kabusys.data.schema.init_schema(db_path)
  - DuckDB スキーマを作成して接続を返す
- kabusys.data.pipeline.run_daily_etl(conn, target_date=None, ...)
  - 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
- kabusys.data.jquants_client.fetch_daily_quotes(...) / save_daily_quotes(...)
  - J-Quants から日足を取得し保存
- kabusys.strategy.build_features(conn, target_date)
  - research モジュールのファクターを正規化して features テーブルへ保存
- kabusys.strategy.generate_signals(conn, target_date, threshold=0.6, weights=None)
  - features / ai_scores / positions を用いて BUY / SELL シグナルを生成し signals テーブルへ保存
- kabusys.data.news_collector.run_news_collection(conn, sources=None, known_codes=None)
  - RSS によるニュース収集ジョブ
- kabusys.data.calendar_management.next_trading_day / is_trading_day / get_trading_days
  - 営業日判定関連ユーティリティ

各関数の詳細は対応ファイル内の docstring を参照してください。

---

## 設定ファイル（.env）の取り扱い

- src/kabusys/config.py はプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を探索し、`.env` と `.env.local` を自動で読み込みます。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - テストなどで自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- .env.example（リポジトリに含める想定）を参考に必須変数を設定してください。
- Settings クラスで必須値を _require() により検査します（不足時は ValueError が発生）。

---

## ディレクトリ構成（主要ファイル）

リポジトリのソースは `src/kabusys` 以下に配置されています。主なファイル構成は以下のとおり：

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
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
  - monitoring/  (存在が示唆されるが実装は状況により)
  - その他モジュール（将来的に拡張される部分）

各ファイルは docstring で機能・設計方針が詳細に記載されています。実装の詳細を確認する際は該当ファイルのトップにある説明を参照してください。

---

## ログと監視

- 設定変数 `LOG_LEVEL`（環境変数）でログレベルを制御できます（DEBUG/INFO/...）。
- ETL 結果や品質チェック結果は run_daily_etl の戻り値（ETLResult）で取得可能です。監査ログや execution 層のテーブルも用意されているため、必要に応じて監視／アラートを組み合わせてください。

---

## 開発・拡張について

- strategy と execution 層は明確に分離してあり、発注ロジック（証券会社 API 連携）を独立して実装できます。
- research モジュールはバックテスト／ファクター探索を目的に作られているため、ここで算出された生ファクターを feature_engineering で正規化して戦略に組み込みます。
- テストを行う際は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用し、環境変数の影響を切ることができます。

---

必要であれば README に次の内容も追加できます：
- サンプル .env.example（項目と説明）
- 実運用でのワークフロー例（cron / Airflow / systemd の設定例）
- テスト実行方法、CI 設定
- ライセンス情報

追加希望があれば教えてください。