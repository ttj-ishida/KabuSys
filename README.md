# KabuSys

日本株向けの自動売買 / データプラットフォーム共通ライブラリです。  
データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を含む Python パッケージです。

- J-Quants API からの株価・財務・カレンダー取得（Rate limiting / リトライ / トークン自動リフレッシュ対応）
- DuckDB を用いた Raw / Processed / Feature / Execution 層のスキーマ定義・初期化
- ETL パイプライン（差分取得、バックフィル、品質チェックフレームワーク）
- ファクター計算（モメンタム / バリュー / ボラティリティ / 流動性）
- 特徴量正規化・合成（feature_engineering）
- シグナル生成（final_score の重み付け、BUY / SELL ルール、エグジット判定）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策・XML 脆弱性対策を含む）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査（audit）テーブル定義（発注 → 約定のトレーサビリティ）

設計上、発注 API（実際のブローカー送信）に直接依存しない層設計になっています。  
研究 / 本番で同じ関数を使えるように DuckDB ベースでデータ処理を行います。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・リトライ・トークン管理）
  - schema: DuckDB スキーマ初期化（raw/processed/feature/execution 層）
  - pipeline: 日次 ETL（差分取得、バックフィル、品質チェックの統合）
  - news_collector: RSS 収集・前処理・保存（SSRF & XML 安全対策）
  - calendar_management: JPX カレンダー管理・営業日ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- research/
  - factor_research: モメンタム・バリュー・ボラティリティ計算
  - feature_exploration: 将来リターン計算、IC（Spearman）やサマリー
- strategy/
  - feature_engineering: ファクター合成・フィルタ・正規化・features テーブルへの UPSERT
  - signal_generator: final_score 計算、BUY/SELL シグナル生成、signals テーブルへの書き込み
- execution/ / monitoring/ （パッケージ空骨格、将来の発注/監視実装向け）

その他：
- 環境変数管理（.env / .env.local 自動読み込み、プロジェクトルート検出）
- 設定ラッパ（settings）で必須変数チェック

---

## セットアップ手順

前提:
- Python 3.9+（typing の union 表記などに依存）
- pip

1. リポジトリをクローンし、パッケージをインストール（開発モード推奨）
   - ルートには `pyproject.toml` がある想定（パッケージは `src/` 配下）
   - 例:
     ```
     git clone <repo-url>
     cd <repo>
     pip install -e .[dev]  # optional extras がある場合
     ```
   - 依存パッケージ例（プロジェクト側で指定してください）:
     - duckdb
     - defusedxml

2. 環境変数
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` と `.env.local` を置くと自動的に読み込まれます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用途など）。
   - 必須環境変数（settings でチェックされます）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   - .env の簡易例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

3. DuckDB スキーマ初期化
   - Python REPL / スクリプトで:
     ```py
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)
     ```
   - デフォルトは `data/kabusys.duckdb`。`:memory:` を渡すとインメモリ DB。

---

## 使い方（主要ユースケース）

以下は典型的なワークフローの例です。必要に応じてスクリプト / ジョブにラップして運用してください。

1. 日次 ETL（株価 / 財務 / カレンダー取得）
   ```py
   from kabusys.config import settings
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema(settings.duckdb_path)
   result = run_daily_etl(conn)  # target_date を指定可能
   print(result.to_dict())
   ```

2. 特徴量作成（features テーブルへ）
   ```py
   from datetime import date
   import duckdb
   from kabusys.config import settings
   from kabusys.strategy import build_features

   conn = duckdb.connect(str(settings.duckdb_path))
   count = build_features(conn, target_date=date.today())
   print("features upserted:", count)
   ```

3. シグナル生成（signals テーブルへ）
   ```py
   from datetime import date
   import duckdb
   from kabusys.config import settings
   from kabusys.strategy import generate_signals

   conn = duckdb.connect(str(settings.duckdb_path))
   total = generate_signals(conn, target_date=date.today())
   print("signals generated:", total)
   ```

4. ニュース収集ジョブ
   ```py
   import duckdb
   from kabusys.config import settings
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   conn = duckdb.connect(str(settings.duckdb_path))
   known_codes = {"7203", "6758", "9984"}  # 事前に有効コードセットを用意
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   ```

5. カレンダー更新ジョブ（夜間バッチ）
   ```py
   from kabusys.data.calendar_management import calendar_update_job
   conn = init_schema(settings.duckdb_path)
   saved = calendar_update_job(conn)
   print("calendar saved:", saved)
   ```

注意:
- settings で必須環境変数が足りない場合は ValueError が発生します。
- DuckDB 接続はスレッドセーフではないため、マルチスレッド運用時はコネクションの取り扱いに注意してください。

---

## ディレクトリ構成

主要ファイル/ディレクトリ（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 / 保存）
    - news_collector.py      — RSS 取得・前処理・保存
    - schema.py              — DuckDB スキーマ定義・初期化
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — カレンダー関連ユーティリティ
    - features.py            — data.stats の公開ラッパ
    - audit.py               — 監査テーブル DDL
  - research/
    - __init__.py
    - factor_research.py     — mom/value/volatility 計算
    - feature_exploration.py — forward returns / IC / summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py — features の生成・保存
    - signal_generator.py    — シグナル生成ロジック
  - execution/                — 発注/実行管理（将来実装）
  - monitoring/               — 監視・アラート（将来実装）

---

## 実運用上の注意点 / トラブルシューティング

- 環境変数未設定:
  - settings のプロパティは未設定の場合 ValueError を投げます。CI / デプロイ前に必要変数を設定してください。
- .env 自動ロード:
  - プロジェクトルート検出は __file__ から親ディレクトリを上って `.git` または `pyproject.toml` を探します。見つからないと自動読み込みはスキップされます。
- API レート制限:
  - J-Quants クライアントはデフォルトで 120 req/min を守る実装ですが、大量取得や並列化では注意してください。
- DuckDB ファイルのパーミッション / ディスク容量:
  - デフォルトの DB パスは `data/kabusys.duckdb`。親ディレクトリが存在しない場合は自動作成されますが、パーミッションや容量に注意してください。
- セキュリティ:
  - news_collector は SSRF、XML 脆弱性、gzip bomb 等に対する防御を実装していますが、外部 RSS を取り扱う際は運用監視を行ってください。
- テスト:
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し、環境制御を行ってください。

---

## 貢献・拡張案

- execution 層のブローカー接続実装（kabuステーション等）
- モニタリング / アラート（Slack 投稿ラッパを使った監視ジョブ）
- 戦略バックテスト用ユーティリティの追加
- CI 用の DB 初期データ / Fixtures

---

この README はコードベースの主要な意図と基本的な使い方をまとめたものです。詳細な設計仕様（StrategyModel.md, DataPlatform.md 等）や API 仕様は別ドキュメントにある想定です。必要であれば、操作スクリプト例や運用 runbook のテンプレートも作成します。