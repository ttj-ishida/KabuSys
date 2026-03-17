# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群（KabuSys）。  
データ収集・ETL、データ品質チェック、ニュース収集、監査ログ（発注 → 約定トレース）などの基盤機能を提供します。

主な目的は「J-Quants 等のデータソースから安全かつ冪等にデータを取得・保存し、戦略層／実行層へ渡す」ことです。

---

## 機能一覧

- 環境変数管理
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に自動検出）
  - 必須項目未設定時は明示的なエラーを返す

- データ取得（J-Quants クライアント）
  - 日足（OHLCV）・四半期財務データ・JPX マーケットカレンダーの取得
  - API レート制御（120 req/min 相当の固定間隔スロットリング）
  - リトライ（指数バックオフ、401 の場合はリフレッシュトークンで自動再取得）
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集
  - RSS フィードを安全に取得（SSRF/リダイレクト検査、gzip/サイズ上限）
  - URL 正規化・トラッキングパラメータ削除・記事IDを SHA-256 で生成（先頭32文字）
  - DuckDB へ冪等保存（INSERT ... RETURNING を利用）
  - テキストから銘柄コード（4桁）抽出とニュース⇄銘柄紐付け

- ETL パイプライン
  - 差分更新（DBの最終日からの不足分のみ取得）
  - backfill による直近補正吸収
  - カレンダー先読み（デフォルト 90 日）
  - 品質チェック（欠損・重複・スパイク・日付不整合）

- マーケットカレンダー管理
  - 営業日判定 / 前後営業日の検索 / 期間内営業日リスト取得
  - カレンダーの夜間差分更新ジョブ

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 を UUID 連鎖でトレース可能に記録する監査用スキーマ
  - 発注要求は order_request_id を冪等キーとして運用

- データ品質チェック
  - 欠損（OHLC 欠損）、主キー重複、スパイク（前日比閾値）、未来日付・非営業日データの検出
  - 問題は QualityIssue として収集し、呼び出し元で判断可能

---

## セットアップ手順

前提: Python 3.9+（型ヒントに union types 等を使っているため 3.9 以上を推奨）

1. リポジトリをクローン／配置
2. 仮想環境を作成して有効化
   - unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows Powershell:
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要パッケージをインストール
   - 最小依存例:
     ```
     pip install duckdb defusedxml
     ```
   - 開発用にパッケージ化されている場合:
     ```
     pip install -e .
     ```

4. 環境変数の設定
   - プロジェクトルート（.git か pyproject.toml のある階層）に `.env` を置くと自動読み込みされます。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

必須環境変数（代表）
- JQUANTS_REFRESH_TOKEN : J-Quants の refresh token（必須）
- KABU_API_PASSWORD : kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN : Slack 通知用 BOT トークン（必須）
- SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
- DUCKDB_PATH : DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH : SQLite 監視DB（省略時: data/monitoring.db）
- KABUSYS_ENV : 実行環境（development, paper_trading, live）デフォルトは development
- LOG_LEVEL : ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

注意: settings オブジェクトは未設定の必須変数に対して ValueError を投げます。

---

## 使い方（簡単な例）

以下は最小の利用例です。プロジェクト内でスクリプトを作成して実行してください。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema

# デフォルトパスを使う場合は settings.duckdb_path を参照してもよい
conn = init_schema("data/kabusys.duckdb")  # 親ディレクトリを自動作成
```

2) 日次ETL を実行（J-Quants トークンは settings から自動参照）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能（date オブジェクト）
print(result.to_dict())
```

3) ニュース収集ジョブ実行
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄抽出用の有効コードセット（省略可）
known_codes = {"7203", "6758"}  # 例
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)  # {source_name: saved_count}
```

4) 監査DB（発注/約定用）初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

5) J-Quants の個別 API 呼び出し（テストやデバッグ用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

token = get_id_token()  # settings の refresh token を使って取得
quotes = fetch_daily_quotes(id_token=token, code="7203", date_from=date(2024,1,1), date_to=date(2024,3,31))
```

---

## 実装上のポイント / 注意点

- 自動環境変数読み込み
  - .env をプロジェクトルートで自動的に読み込みます（優先順位: OS環境 > .env.local > .env）。
  - テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
  - ルート検出は .git または pyproject.toml を探索して行います。配布後に CWD とは無関係に有効です。

- J-Quants クライアント
  - レート制御（固定間隔）とリトライ（408/429/5xx、401 はトークン再発行）を実装済み。
  - ページネーション対応（pagination_key）。
  - データ保存時は fetched_at を UTC で付与し、DuckDB には冪等に保存（ON CONFLICT）します。

- NewsCollector（RSS）
  - defusedxml を利用して XML の脆弱性を低減
  - SSRF 対策: リダイレクトや最終 URL のホストがプライベートであれば拒否
  - レスポンスサイズ上限（デフォルト 10 MB）と gzip 解凍後のサイズチェック
  - 記事IDは正規化 URL の SHA-256（先頭32文字）を使用し冪等性を確保

- DuckDB スキーマ
  - Raw / Processed / Feature / Execution / Audit 等の複数レイヤーを定義
  - インデックス・外部キー・制約を多用してデータ整合性を確保
  - init_schema() は冪等にテーブルを作成します

- 品質チェック
  - ETL 中に発見した問題は QualityIssue として収集し、呼び出し元で停止／通知等の判断を行う設計

---

## ディレクトリ構成

（主要ファイルのみを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                 # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py       # J-Quants API クライアント
      - news_collector.py       # RSS ニュース収集
      - schema.py               # DuckDB スキーマ定義・初期化
      - pipeline.py             # ETL パイプライン（run_daily_etl 等）
      - calendar_management.py  # カレンダー管理（営業日判定等）
      - audit.py                # 監査ログ（発注→約定トレース）
      - quality.py              # データ品質チェック
    - strategy/                  # 戦略層（空の __init__、実装を追加）
      - __init__.py
    - execution/                 # 実行層（空の __init__、発注ラッパ等を追加）
      - __init__.py
    - monitoring/                # 監視用モジュール（placeholder）
      - __init__.py

プロジェクトルートに .env/.env.local/.env.example 等を置き、設定を管理する想定です。

---

## トラブルシューティング

- ValueError: 環境変数が設定されていない
  - settings のプロパティは必須変数未設定時に ValueError を投げます。`.env` を準備するか環境変数を設定してください。

- ネットワークエラー / API レートエラー
  - jquants_client はリトライ・バックオフを行いますが、レートを大幅に超えるアクセスは避けてください。レート制御は固定インターバル（120 req/min 想定）です。

- RSS の取得で XML パースエラーが出る
  - 不正なフィードは警告でスキップします。フィード URL を確認してください。

- DuckDB に関するエラー
  - init_schema() で親ディレクトリがない場合は自動作成しますが、ファイルのパーミッションなどを確認してください。

---

## 今後の拡張案（参考）

- 戦略モジュール（strategy）と実行モジュール（execution）の具体実装
- Slack 等によるアラート送信の実装（config に Slack 設定あり）
- CI/CD での自動テスト・静的解析ツールの導入
- ETL のスケジューリング（Airflow / cron 連携）

---

質問や README の追加改善点（例: 実行スクリプト、requirements.txt、開発用の Makefile など）があれば教えてください。README を用途に合わせてさらに具体的に調整します。