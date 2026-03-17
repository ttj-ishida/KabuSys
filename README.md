# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants / RSS 等から市場データ・財務データ・ニュースを取得し、DuckDB に格納・整形して戦略層や実行層で利用できるようにすることを目的としています。

主な設計方針：
- ETL は差分更新かつ冪等（ON CONFLICT / DO UPDATE）で安全に実行
- J-Quants API に対してレート制限・リトライ・自動トークンリフレッシュを実装
- ニュース収集は SSRF / XML Bomb 等の攻撃に配慮した堅牢な実装
- データ品質チェック（欠損・重複・スパイク・日付不整合）を提供
- 監査ログ（signal → order → execution のトレーサビリティ）を保持

---

## 機能一覧

- J-Quants API クライアント（株価日足、四半期財務、マーケットカレンダー）
  - レート制御（120 req/min）
  - リトライ（408/429/5xx, 最大3回）、401 時の自動トークンリフレッシュ
  - フェッチ時刻（fetched_at）を UTC で記録
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得 / 保存 / 品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev trading day、夜間更新ジョブ）
- ニュース収集（RSS 取得・前処理・ID生成・DB 保存・銘柄抽出）
  - URL 正規化・トラッキングパラメータ削除
  - SSRF 防止、レスポンスサイズ制限、gzip 対応
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal, order_request, executions）テーブルと初期化ユーティリティ

---

## 動作要件

- Python 3.10+
- 主要依存ライブラリ（例）:
  - duckdb
  - defusedxml

その他、実行環境により Slack API / kabu API 用のクライアント等が必要になる場合があります。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```bash
   git clone <repository-url>
   cd <project-root>
   ```

2. 仮想環境を作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell)
   ```

3. 必要パッケージをインストール
   - pyproject / requirements があればそれに従ってください。最小限：
   ```bash
   pip install duckdb defusedxml
   ```
   - 開発インストール（パッケージとして扱う場合）:
   ```bash
   pip install -e .
   ```

4. 環境変数の設定
   - ルートに `.env` または `.env.local` を置くと自動で読み込まれます（優先度: OS 環境 > .env.local > .env）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストなどで使用）。

必須の環境変数（settings で参照）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

任意 / デフォルトあり
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

例 .env（参考）
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

## 使い方（主要 API の例）

以下は簡単な Python スニペット例です。実運用ではエラーハンドリングやロギングを適切に行ってください。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")  # ディレクトリがなければ自動作成
```

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェックを順次実行）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- ニュース収集（RSS）と銘柄紐付け
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄コードのセット（例: {'7203', '6758', ...}）
res = run_news_collection(conn, sources=None, known_codes=known_codes)
print(res)  # {source_name: 新規保存件数}
```

- カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("saved", saved)
```

- 監査ログテーブル初期化（監査専用または既存 conn に追加）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
# または新規監査DBとして作る:
# from kabusys.data.audit import init_audit_db
# audit_conn = init_audit_db("data/audit.duckdb")
```

- J-Quants の ID トークンを明示的に取得
```python
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を使用して取得
```

---

## 主要モジュールの説明（短）

- kabusys.config
  - .env / 環境変数の自動読み込み、Settings クラスで設定値を提供
- kabusys.data.jquants_client
  - J-Quants API 呼び出し、ページネーション、保存ユーティリティ（DuckDB への保存関数含む）
- kabusys.data.schema
  - DuckDB の DDL（Raw / Processed / Feature / Execution 層）と初期化関数
- kabusys.data.pipeline
  - 差分 ETL と品質チェックをワンストップで実行するパイプライン
- kabusys.data.news_collector
  - RSS 取得、前処理、raw_news 保存、銘柄抽出・紐付け
- kabusys.data.calendar_management
  - 営業日判定、next/prev trading day、calendar 更新ジョブ
- kabusys.data.quality
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
- kabusys.data.audit
  - 監査ログ用のテーブル定義と初期化ユーティリティ

---

## ディレクトリ構成

以下はプロジェクト（src/kabusys）の主要ファイル・ディレクトリです（一部抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/          # 発注・実行層の実装用パッケージ（空 __init__）
    - strategy/           # 戦略層の実装用パッケージ（空 __init__）
    - monitoring/         # 監視用モジュール（空 __init__）
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - calendar_management.py
      - schema.py
      - audit.py
      - quality.py

---

## 注意事項 / 補足

- DuckDB の SQL 実行ではパラメータバインドを用いてインジェクションリスクを抑えていますが、実運用時は接続の権限やファイル配置に注意してください。
- news_collector は外部 URL を扱うため SSRF や XML 攻撃対策を講じていますが、社内ポリシーに合わせた追加制御（プロキシ、アウトバウンドルール等）を推奨します。
- J-Quants の API レート制限や kabu API の仕様に沿って運用してください。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を活用できます。
- 本 README はコードベースのコメント・仕様に基づくドキュメントです。実運用向けにはさらに運用手順、監視・アラート、CI/CD、テスト手順を追加してください。

---

必要であれば、README に入れる具体的な .env.example、requirements.txt、または CI / systemd / Docker の例も作成します。どれを追加しますか？