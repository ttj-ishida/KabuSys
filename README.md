# KabuSys

日本株自動売買システムのコアライブラリ（軽量なデータ基盤・ETL・監査・収集モジュール群）

このリポジトリは、J-Quants / kabuステーション 等の外部 API からデータを収集し、
DuckDB に格納・品質チェック・特徴量作成・監査ログ管理までを支援する
Python モジュール群を提供します。自動売買戦略や発注実装は別モジュールで
実装しやすい設計（data / strategy / execution / monitoring の分離）です。

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の取得 API（settings オブジェクト）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務（四半期 BS/PL）、市場カレンダー取得
  - レート制限（120 req/min）管理、リトライ（指数バックオフ）、トークン自動リフレッシュ
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・前処理（URL除去・空白正規化）
  - URL 正規化（トラッキングパラメータ除去）→ SHA-256 ハッシュで記事ID生成
  - SSRF 対策、gzip/サイズ制限、defusedxml による安全な XML パース
  - DuckDB へ冪等保存（INSERT … RETURNING）、銘柄コード紐付け
- データスキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 層を定義する DuckDB DDL
  - init_schema() で初期化（冪等）
- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新、バックフィル、品質チェック統合
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日の判定、前後営業日取得、夜間カレンダー更新ジョブ
- 監査ログ（kabusys.data.audit）
  - シグナル → 発注 → 約定までのトレーサビリティ用テーブル群と初期化 API
- 品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合の検出と QualityIssue レポート

---

## 必要要件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード等）

（実際の setup.py / pyproject.toml に従ってインストールしてください）

---

## セットアップ手順

1. リポジトリを取得
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - ここでは例として pip を使用：
   ```
   pip install duckdb defusedxml
   ```
   - 実際は pyproject.toml / requirements.txt に従ってください。

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を配置すると自動で読み込まれます。
   - 自動読み込みを無効化したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN       : Slack ボットトークン（必須）
     - SLACK_CHANNEL_ID      : Slack 送信先チャンネル ID（必須）
   - オプション:
     - KABUSYS_ENV : development | paper_trading | live（default: development）
     - LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL（default: INFO）
     - DUCKDB_PATH : DuckDB ファイルパス（default: data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 SQLite パス（default: data/monitoring.db）
   - .env の雛形はプロジェクトに `.env.example` を用意しておくことを推奨します。

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトから以下を実行して DB を初期化します：
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
   conn.close()
   ```

6. 監査ログ（audit）スキーマを追加する場合
   ```python
   from kabusys.data.schema import get_connection
   from kabusys.data.audit import init_audit_schema
   conn = get_connection("data/kabusys.duckdb")
   init_audit_schema(conn, transactional=True)
   conn.close()
   ```

---

## 使い方（例）

- J-Quants トークン取得（ID トークン）：
  ```python
  from kabusys.data.jquants_client import get_id_token
  id_token = get_id_token()  # settings.jquants_refresh_token を使って POST で取得
  ```

- 日次 ETL を実行する（市場カレンダー・株価・財務・品質チェック）：
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- ニュース収集ジョブ（RSS）を実行する：
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9432"}  # あらかじめ有効銘柄コードを用意
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: 新規保存件数}
  conn.close()
  ```

- 品質チェックだけを実行する：
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i)
  conn.close()
  ```

- 環境設定の参照（アプリケーションコードから）：
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

---

## ディレクトリ構成

主要ファイルのみ抜粋（src/ がパッケージルート）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py            — RSS ニュース収集・前処理・DB 保存
    - schema.py                    — DuckDB スキーマ定義・初期化
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py       — カレンダー管理（営業日判定・更新ジョブ）
    - audit.py                     — 監査ログ（シグナル/発注/約定）DDL と初期化
    - quality.py                   — データ品質チェック
  - strategy/
    - __init__.py                  — 戦略関連（拡張用）
  - execution/
    - __init__.py                  — 発注/実行関連（拡張用）
  - monitoring/
    - __init__.py                  — 監視・アラート関連（拡張用）

この README はソースコード内の設計注釈に基づいて作成しています。各モジュールに詳細な docstring があり、関数 API は基本的にドキュメンテーションコメントに従います。

---

## 開発・テスト時の注意点

- 自動 .env ロードを抑制する:
  - テストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動で .env を読み込まない挙動になります。
- ネットワーク呼び出しをモックする:
  - news_collector._urlopen や jquants_client の HTTP 呼び出しはテストで差し替え可能なように設計されています。
- DuckDB を ":memory:" で使うとテストが容易になります。

---

## トラブルシュート（よくある問題）

- 環境変数が見つからない:
  - 必須の環境変数が未設定だと Settings のプロパティで ValueError が発生します。`.env` を作成するか環境変数を設定してください。
- API レスポンスで JSON デコードエラー:
  - jquants_client は生レスポンスの先頭200文字を含むエラーメッセージを出します。レスポンスが HTML 等だと発生します。
- RSS 取得でサイズ超過や圧縮解除失敗:
  - 大きすぎるレスポンスや不正な gzip に対しては安全上スキップする挙動です。ログを確認してください。

---

## 貢献・ライセンス

- 貢献: Pull Request または Issue を通じて歓迎します。コードスタイルやテストを整えて送ってください。
- ライセンス: プロジェクトの LICENSE ファイルに従ってください（この README では指定なし）。

---

README の内容はコードベースの現状に基づく概要です。より詳細な使用法や運用手順は各モジュールの docstring（ソース内コメント）を参照してください。