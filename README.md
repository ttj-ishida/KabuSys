# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群。  
J-Quants や kabuステーション 等の外部 API からデータを取得して DuckDB に格納し、ETL・品質チェック・ニュース収集・監査ログなどの基盤処理を提供します。

バージョン: 0.1.0

---

## 主な特徴

- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得
  - API レート制御（120 req/min 固定スロットリング）
  - リトライ（指数バックオフ、特定ステータスでの再試行）、401 受信時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を記録して Look-ahead Bias を防止
  - DuckDB への冪等保存（ON CONFLICT / DO UPDATE）

- ニュース収集
  - RSS フィードから記事を取得して前処理（URL除去・空白正規化）
  - 記事IDは正規化 URL の SHA-256（先頭32文字）で生成して冪等性確保
  - SSRF 対策、受信サイズ制限、XML パース安全化（defusedxml）
  - 銘柄コード抽出（4桁コード）と news_symbols への紐付け

- ETL パイプライン
  - 差分更新（最終取得日を基に差分取得）、バックフィル、品質チェック
  - 日次 ETL の統合エントリポイント（calender → prices → financials → quality）

- データ品質チェック
  - 欠損、スパイク（前日比）、重複、日付不整合の検出
  - QualityIssue オブジェクトのリストで問題を返却（Fail-Fast ではなく集約）

- スキーマ／監査
  - DuckDB 用の包括的スキーマ（Raw / Processed / Feature / Execution / Audit）
  - 監査ログテーブル（signal_events / order_requests / executions）とインデックス初期化関数

---

## 必要条件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークへのアクセス（J-Quants API、RSS フィードなど）

（実際のインストールはプロジェクトの pyproject.toml / requirements.txt を参照してください）

---

## 環境変数（主な設定）

パッケージはプロジェクトルートの `.env` / `.env.local` を自動的にロードします（OS 環境変数が優先）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（ライブラリ利用で必要になるもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

オプション／デフォルト:
- KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト: `development`）
- LOG_LEVEL — `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（デフォルト: `INFO`）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（任意）
- KABUSYS_* 以外:
  - KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — SQLite パス（監視用）（デフォルト: data/monitoring.db）

.env のサンプル（README 用例）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして Python 仮想環境を用意
   ```
   git clone <repo-url>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール（例）
   ```
   pip install duckdb defusedxml
   ```
   （実際は pyproject.toml / requirements.txt に従ってください）

3. `.env` を作成して上記必須環境変数を設定

4. DuckDB スキーマを初期化
   - Python REPL やスクリプトで:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ（audit）スキーマを追加する場合:
     ```python
     from kabusys.data import audit
     audit.init_audit_schema(conn)
     ```

---

## 使い方（代表的な API）

ここでは主要な機能の呼び出し例を示します。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")  # ディレクトリは自動作成
  ```

- J-Quants から日足データを取得して保存
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
  saved = jq.save_daily_quotes(conn, records)
  ```

- RSS からニュースを収集して保存（既定ソース）
  ```python
  from kabusys.data import news_collector as nc
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")
  # known_codes は銘柄抽出に利用する有効なコード集合（例: 上場銘柄リスト）
  results = nc.run_news_collection(conn, known_codes={"7203","6758"})
  ```

- 日次 ETL パイプラインを実行
  ```python
  from datetime import date
  from kabusys.data import pipeline
  conn = schema.get_connection("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 品質チェックを個別に実行
  ```python
  from kabusys.data import quality
  issues = quality.run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i)
  ```

注意:
- jquants_client は内部で rate limiter と retry を持ちます。大量リクエストを投げる場合でも基本的にそのまま使えますが、API 利用規約に従ってください。
- ニュース収集では SSRF・XML Bomb 等の対策が組み込まれていますが、外部 URL を扱う処理であるため追加の運用上の注意が必要です。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要モジュールとファイルは以下の通りです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理（.env 自動ロード含む）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py         — RSS 取得・前処理・保存・銘柄抽出
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py    — 市場カレンダー管理（営業日判定等）
    - schema.py                 — DuckDB スキーマ定義・初期化
    - audit.py                  — 監査ログスキーマ初期化
    - quality.py                — データ品質チェック
  - strategy/                    — 戦略関連（未実装のエントリポイント）
  - execution/                   — 発注/約定/ポジション管理（未実装のエントリポイント）
  - monitoring/                  — 監視用コード（未実装のエントリポイント）

---

## 運用上の注意・設計上のポイント

- 環境変数は OS 環境 > .env.local > .env の優先順位で読み込まれます。テストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って自動読み込みを無効にできます。
- すべての日時は設計上 UTC を基準に扱う箇所があり（fetched_at / audit のタイムスタンプ等）、運用時はタイムゾーンに注意してください。
- DuckDB の初期化は idempotent（既存テーブルがあればスキップ）なので、本番/開発の起動スクリプトから安全に呼び出せます。
- ニュースの URL 正規化はトラッキングパラメータを除去して固有 ID を作るため、同一記事の二重投入を防ぎます。
- ETL は Fail-Fast を採らず、発生した問題を集約して返す設計です。呼び出し元で結果を評価して必要なアラートや停止を行ってください。

---

## 例: 簡易起動スクリプト

以下は日次 ETL を単純に実行する例（起動タスク等に組み込む想定）。

```python
# run_daily.py
from datetime import date
from kabusys.data import schema, pipeline

def main():
    conn = schema.init_schema("data/kabusys.duckdb")
    res = pipeline.run_daily_etl(conn, target_date=date.today())
    print(res.to_dict())

if __name__ == "__main__":
    main()
```

---

## ライセンス・貢献

（ここには実際のプロジェクトのライセンスや貢献ガイドラインを記載してください）

---

必要に応じて README に記載する具体的なインストールコマンドや pyproject/requirements の内容、CI / デプロイ手順や実運用上の監視（Slack 通知等）の設定例を追加できます。どの情報を追記しますか？