# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、品質チェック、特徴量作成、リサーチ用ユーティリティ、ニュース収集、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムに必要なデータ層（Raw / Processed / Feature / Execution）とそれに付随するユーティリティを提供する Python パッケージです。主な目的は以下です。

- J-Quants API からの市場データ・財務データ・カレンダーの取得（レート制御・リトライ付き）
- DuckDB を用いたスキーマ定義・初期化・永続化（冪等保存）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- ニュース（RSS）収集と銘柄抽出
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 監査ログ（signal → order → execution トレース）用テーブル

設計上、Research / Data モジュールは本番発注 API を呼ばず、DuckDB のみを参照して解析可能です。

---

## 主な機能一覧

- 環境設定読み込み（.env 自動ロード、保護機構付き）
- J-Quants API クライアント
  - レート制御（120 req/min）
  - リトライ（指数バックオフ、401時の自動トークンリフレッシュ）
  - ページネーション対応
  - DuckDB へ冪等的に保存する save_* ユーティリティ
- DuckDB スキーマ定義・初期化（data.schema.init_schema）
- ETL パイプライン（data.pipeline.run_daily_etl）
  - 市場カレンダー / 株価 / 財務データの差分取得・保存
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）と銘柄抽出（data.news_collector）
  - SSRF対策・XML攻撃対策・サイズ制限付き
  - 正規化URL→記事ID（SHA-256 ハッシュ）で冪等保存
- リサーチ用ファクター計算（research.factor_research）
  - モメンタム（1M/3M/6M、MA200乖離）
  - バリュー（PER, ROE）
  - ボラティリティ（20日ATR 等）
  - forward returns / IC / 統計サマリ等（research.feature_exploration）
- 統計ユーティリティ（zscore 正規化など）
- 監査ログスキーマ（signal_events, order_requests, executions 等）

---

## 必要な環境変数

以下は本パッケージが参照する主要な環境変数です（settings でラップされています）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注系を使う場合）
- SLACK_BOT_TOKEN — Slack 通知用（必要な場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必要な場合）

任意（デフォルトあり）:
- KABUSYS_ENV — 環境: `development` | `paper_trading` | `live`（デフォルト: development）
- LOG_LEVEL — ログレベル: `DEBUG|INFO|WARNING|ERROR|CRITICAL`（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

自動 .env 読み込み:
- プロジェクトルートにある `.env` / `.env.local` が自動で読み込まれます。テスト時などで自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

1. Python 環境の作成（例: venv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージのインストール（主な依存）
   - duckdb
   - defusedxml
   - （必要に応じて他の HTTP / Slack クライアント等を追加）

   例:
   ```bash
   pip install duckdb defusedxml
   ```

3. パッケージを開発モードでインストール（プロジェクトルートに setup / pyproject がある前提）
   ```bash
   pip install -e .
   ```

4. 環境変数（.env）を作成
   - プロジェクトルートに `.env` を作成し、必須変数を設定します。例:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```

5. DuckDB スキーマの初期化
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ディレクトリを自動作成
   conn.close()
   ```

   監査用 DB を別途作る場合:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（基本例・API スニペット）

以下は主要機能の簡単な使用例です。詳細は各モジュールの docstring を参照してください。

- ETL（日次パイプライン）実行
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # settings.jquants_refresh_token を使用して J-Quants から差分取得
  print(result.to_dict())
  ```

- J-Quants のデータ取得（低レベル）
  ```python
  from kabusys.data import jquants_client as jq

  # トークンは settings から自動取得されます
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  # DuckDB に保存
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  jq.save_daily_quotes(conn, records)
  ```

- ニュース収集
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 任意
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count, ...}
  ```

- リサーチ（ファクター計算）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, zscore_normalize

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2024, 1, 31)
  mom = calc_momentum(conn, target)
  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  ```

- Zスコア正規化（data.stats）
  ```python
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(mom, ["mom_1m", "ma200_dev"])
  ```

- 簡単な品質チェック実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=target)
  for issue in issues:
      print(issue.check_name, issue.severity, issue.detail)
  ```

---

## 設計上の注意点 / ポイント

- Research / Data モジュールは本番口座や発注 API（kabuステーション）へアクセスせず、DuckDB のみ参照する方針です。これにより安全な解析環境を保ちます。
- J-Quants API 呼び出しはレート制御・リトライ・トークン自動更新を備えていますが、APIキー（refresh token）は必ず安全に管理してください。
- DuckDB への書き込みは冪等化（ON CONFLICT DO UPDATE / DO NOTHING）を採用しています。
- news_collector は SSRF 防止、XML Bomb 対策、レスポンスサイズ制限など堅牢性を考慮して実装されています。
- audit（監査ログ）スキーマはトレース可能性を重視し、作成日時や冪等キー（order_request_id）を持ちます。

---

## ディレクトリ構成

プロジェクトの主なファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py               — RSS ニュース収集・保存・銘柄抽出
    - schema.py                       — DuckDB スキーマ定義 / init_schema
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - quality.py                      — データ品質チェック
    - calendar_management.py          — 市場カレンダー管理ユーティリティ
    - stats.py                        — 統計ユーティリティ（zscore_normalize）
    - features.py                     — features インターフェース
    - audit.py                        — 監査ログスキーマ / init_audit_db
    - etl.py                          — ETL の公開型再輸出
  - research/
    - __init__.py
    - factor_research.py              — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py          — forward returns / IC / summary / rank
  - strategy/                          — 戦略関連（プレースホルダ）
  - execution/                         — 発注/実行関連（プレースホルダ）
  - monitoring/                        — 監視関連（プレースホルダ）

ドキュメントや設計ノート（参照される想定のファイル）:
- DataPlatform.md, StrategyModel.md など（リポジトリ外または別途管理）

---

## 貢献 / 開発について

- コードは docstring と型ヒントを重視しており、ユニットテストを追加して堅牢性を高めることを推奨します。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）から行われます。テスト中に自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- パッケージの拡張（ブローカー連携や追加ファクター）は modules を追加することで容易に行えます。既存の DuckDB スキーマは冪等性を重視して定義されていますが、スキーマ変更時は互換性に注意してください。

---

README に記載されていない詳細を知りたい場合（例: 特定 API の返却フォーマット、DuckDB のテーブル定義の詳細、テスト方法等）は、どの項目を優先して説明するか教えてください。追加のサンプルコードや運用手順（cron / Airflow でのジョブ化例等）も提供できます。