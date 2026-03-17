# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants などの外部 API から市場データを取得して DuckDB に格納し、ETL／品質チェック／マーケットカレンダー管理／ニュース収集／監査ログを提供します。戦略・発注・監視のための基盤コンポーネントを含んでいます。

バージョン: 0.1.0

---

## 主な機能

- 環境変数ベースの設定管理
  - プロジェクトルートの `.env` / `.env.local` を自動読み込み（無効化可）
  - 必須変数チェック（未設定時は例外を発生）

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）・四半期財務・マーケットカレンダー取得
  - レートリミット制御（120 req/min）と固定間隔スロットリング
  - リトライ（指数バックオフ・最大 3 回）、401 時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を抑制
  - DuckDB への冪等保存（ON CONFLICT ... DO UPDATE）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事収集・前処理・DuckDB への冪等保存
  - URL 正規化（tracking パラメータ除去）→ SHA-256（先頭32文字）で記事ID生成
  - defusedxml を用いた安全な XML パース
  - SSRF 対策（スキーム検証・ホストのプライベート判定・リダイレクト検査）
  - レスポンスサイズ上限（Gzip を考慮）など DoS 対策
  - 銘柄コード抽出（本文/タイトルから4桁コード）と news_symbols 保存

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化関数
  - インデックス定義、冪等な初期化（init_schema）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日 + backfill 日数を考慮）
  - カレンダー先読み（lookahead）
  - 品質チェック（欠損・スパイク・重複・日付不整合）と集約結果（ETLResult）

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定・前後営業日の取得・範囲内営業日リスト生成
  - 夜間バッチでのカレンダー差分更新ジョブ

- 監査ログ（kabusys.data.audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティ用テーブル群
  - order_request_id による冪等性確保、UTC タイムゾーン固定

- データ品質チェック（kabusys.data.quality）
  - 欠損検出・スパイク検出（前日比）・重複検出・日付整合性検査
  - 問題は QualityIssue として集められ、呼び出し元で重み付けなど制御可能

---

## 必要条件（開発環境）

- Python 3.10+
  - 型ヒント（`X | Y` など）を使用しているため 3.10 以上を推奨します
- 主要依存パッケージ:
  - duckdb
  - defusedxml

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# パッケージとしてインストールする場合（このリポジトリのルートで）
pip install -e .
```

※ 実際の production では Slack 通知や kabu API クライアントなど追加の依存が必要になる可能性があります。

---

## 環境変数（主なもの）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` からロードされます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite パス（モニタリング用デフォルト: data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）

.env.example を参考に `.env` を作成してください（コード内で .env.example の存在が参照されています）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成と依存ライブラリのインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   # 他に必要なパッケージがあればここで追加
   ```

3. 環境変数ファイルを作成（.env）
   - `JQUANTS_REFRESH_TOKEN` 等の必須値を設定
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB スキーマ初期化
   - Python REPL / スクリプトで実行:
     ```python
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")
     ```
   - これで必要なテーブルとインデックスが作成されます。

---

## 使い方（代表的な例）

- DuckDB 接続の取得（初期化済み DB を使用）
  ```python
  from kabusys.data.schema import get_connection, init_schema
  conn = init_schema("data/kabusys.duckdb")  # または get_connection("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（市場カレンダー取得 → 株価/財務取得 → 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- 株価のみ差分 ETL を実行
  ```python
  from kabusys.data.pipeline import run_prices_etl
  from datetime import date
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  # known_codes は銘柄コードセット（例: {'7203','6758',...}）
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={'7203','6758'})
  print(results)
  ```

- カレンダー夜間バッチ更新
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"saved {saved} records")
  ```

- マーケットデイ判定などユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date
  print(is_trading_day(conn, date(2026, 1, 1)))
  print(next_trading_day(conn, date.today()))
  ```

- J-Quants の ID トークンを直接取得（テスト・デバッグ時）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使う
  ```

注意:
- 上記関数は例外を投げることがあるため production では適切に例外処理・ログ記録してください。
- ETL やネットワークリクエストはレートリミットや API 制限を考慮して運用してください。

---

## ディレクトリ構成

以下は主要ファイル／ディレクトリの一覧（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py
  - execution/
    - __init__.py
  - strategy/
    - __init__.py
  - monitoring/
    - __init__.py
  - data/
    - __init__.py
    - jquants_client.py         -- J-Quants API クライアント（取得 + DuckDB 保存ロジック）
    - news_collector.py         -- RSS ニュース収集・前処理・保存
    - schema.py                 -- DuckDB スキーマ定義・初期化
    - pipeline.py               -- ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py    -- マーケットカレンダー管理 / 営業日ユーティリティ
    - audit.py                  -- 監査ログ（signal / order_request / executions）
    - quality.py                -- データ品質チェック（欠損・スパイク・重複・日付整合性）

（戦略・発注・監視関連の実装はパッケージ構造を用意済みで、将来的な実装を想定しています）

---

## 運用上の注意点

- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml の存在）を検出して行います。テスト時に自動読み込みを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API はレート制限があります（デフォルト 120 req/min）。jquants_client はこれを守る実装ですが、運用時は大量リクエストを避けてください。
- DuckDB は単一ファイル DB で軽量ですが、運用規模に応じてバックアップやファイルローテーションを検討してください。
- ニュース収集では外部 URL を扱うため SSRF 対策・サイズ制限などの安全策が組み込まれています。独自に外部フィードを追加する際は信頼性と安全性を確認してください。
- 監査データは削除しない前提で設計されています。必要に応じて保管ポリシーを検討してください。

---

## 貢献・開発

- バグ報告・機能要求は Issue を立ててください。
- ローカルで開発・実行する際はテスト用の `.env.local` を利用すると便利です（`.env.local` は自動的に上書きされます）。

---

README は以上です。必要であれば、`.env.example` のテンプレート、requirements.txt、サンプルスクリプト（ETL を定期実行する cron / systemd unit）などの追加ドキュメントを作成します。どの部分を優先して追加しますか？