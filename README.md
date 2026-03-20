# KabuSys — 日本株自動売買システム

KabuSys は日本株向けに設計されたデータプラットフォーム兼戦略エンジンです。J-Quants API から市場データ・財務データ・カレンダーを取得し、DuckDB に保存。研究用ファクター計算、特徴量エンジニアリング、シグナル生成、ニュース収集等のパイプラインを備えます。発注・実行層は分離され、監査ログやトレーサビリティを考慮したスキーマ設計がされています。

---

## 主な機能一覧

- データ取得
  - J-Quants API クライアント（ページネーション・リトライ・トークン自動更新・レート制御）
  - 市場カレンダー取得（JPX）
  - 日次株価（OHLCV）・四半期財務データの取得・保存
- ETL / データ品質
  - 差分更新（バックフィル対応）
  - 品質チェックフロー（欠損・スパイク・重複等の検出設計）
- スキーマ管理
  - DuckDB 用の完全なスキーマ定義（Raw / Processed / Feature / Execution 層）
  - インデックス・DDL の冪等初期化
- 研究・特徴量
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - Z スコア正規化ユーティリティ
  - 将来リターン・IC（Information Coefficient）などの解析ユーティリティ
- 特徴量パイプライン（feature_engineering）
  - ユニバースフィルタ（最低株価・売買代金）
  - 正規化・クリッピング・features テーブルへの UPSERT
- シグナル生成（signal_generator）
  - features と ai_scores を統合して final_score を計算
  - Bear レジーム抑制、BUY/SELL シグナルの判定、signals テーブルへの書き込み（冪等）
- ニュース収集（news_collector）
  - RSS フィード取得（SSRF 対策・サイズ制限・トラッキングパラメータ除去）
  - raw_news 保存、銘柄コード抽出・紐付け
- 監査（audit）
  - signal → order → execution のトレーサビリティ用テーブル設計（UUID ベース）

---

## 必須依存と推奨環境

- Python 3.9+
- 主要外部ライブラリ（例）:
  - duckdb
  - defusedxml
- 標準ライブラリの urllib/ssl 等を使用

（実行環境に合わせて requirements.txt を用意してください。プロジェクトは外部ライブラリに過度に依存しないよう設計されていますが、DuckDB と defusedxml は必須です。）

---

## セットアップ手順

1. リポジトリをクローンしてインストール（開発モードの例）
   - git clone ...
   - pip install -e .

2. 必要な Python パッケージをインストール
   - pip install duckdb defusedxml

3. 環境変数を設定
   - プロジェクトルートの `.env` または `.env.local` に必要な値を設定できます。
   - 自動ロードはデフォルトで有効（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
   - 主な環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID — Slack 通知先チャンネルID（必須）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

   例 `.env`（最小）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   ```

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで実行:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 初期化は冪等（既存テーブルは再作成されません）。`":memory:"` でインメモリ DB も可。

---

## 使い方（主なワークフローの例）

- 日次 ETL 実行（市場カレンダー、株価、財務データ、品質チェック）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量（features）構築
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features

  conn = get_connection("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2026, 3, 1))
  print(f"built features: {n}")
  ```

- シグナル生成
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals

  conn = get_connection("data/kabusys.duckdb")
  count = generate_signals(conn, target_date=date(2026, 3, 1))
  print(f"signals generated: {count}")
  ```

- RSS ニュース収集（既知銘柄リストを渡して銘柄紐付け）
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.news_collector import run_news_collection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "8306"}  # 例
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- J-Quants から直接データを取得して保存
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print(saved)
  ```

---

## 設計上のポイント・注意点

- ルックアヘッドバイアス防止:
  - 特徴量・シグナル計算では target_date 時点の公開情報のみを使用する方針。
  - J-Quants データ取得では fetched_at を UTC で記録し、いつデータを知り得たかを追跡可能にする。
- 冪等性:
  - DuckDB への保存は ON CONFLICT DO UPDATE / DO NOTHING を用いて冪等化。
  - ETL は差分更新を行い、バックフィルで後出し修正を吸収。
- セキュリティ・堅牢性:
  - news_collector は SSRF 対策、XML の安全パース、レスポンスサイズ制限等を実装。
  - J-Quants クライアントはレート制御とリトライ（指数バックオフ）を実装。
- 実行層:
  - このコードベースは戦略層とデータ層を中心に実装。kabuステーション等の発注インターフェースは別モジュール（execution）で扱う設計だが、実装は分離されています。
- 自動 .env 読み込み:
  - パッケージはプロジェクトルート（.git または pyproject.toml）を探して `.env` / `.env.local` を自動ロードします。テスト時に自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存）
    - news_collector.py — RSS ニュース収集・保存
    - schema.py — DuckDB スキーマ定義と init_schema()
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理・ジョブ
    - features.py — features の公開インターフェース
    - audit.py — 監査ログ用 DDL
    - (その他: quality モジュールなど想定)
  - research/
    - __init__.py
    - factor_research.py — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py — features 構築ワークフロー
    - signal_generator.py — final_score とシグナル生成
  - execution/ — 発注・実行層（境界モジュール、発展実装）
  - monitoring/ — 監視・メトリクス（実装場所）
- pyproject.toml / setup.cfg / .gitignore（プロジェクトルート）

（上記はコードベース内に含まれる主要モジュールの抜粋です）

---

## 追加情報

- ログやエラーは各モジュールで詳細に出力する設計です。運用時は LOG_LEVEL を調整してください。
- DuckDB のファイルパスは Settings.duckdb_path で指定できます（デフォルト: data/kabusys.duckdb）。
- 研究用ユーティリティ（research パッケージ）を用いてファクター品質評価（IC 等）を行えます。
- 本 README はコード内ドキュメントに基づいて作成しています。実運用時は DataPlatform.md / StrategyModel.md 等の設計文書も参照してください。

---

必要であれば、README にサンプル .env.example、requirements.txt、簡易運用スクリプト例（cron / systemd / Airflow 用）などを追加で作成します。どの形式の追加が必要か教えてください。