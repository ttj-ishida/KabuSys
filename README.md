# KabuSys

日本株向けの自動売買プラットフォーム基盤ライブラリです。  
データ取得（J-Quants）・ETL・データ品質チェック・ニュース収集・DuckDB スキーマ管理・監査ログなど、戦略実装と実行基盤のための共通機能群を提供します。

---
## 主な特徴
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得
  - レート制限（120 req/min）順守、指数バックオフによるリトライ、401 時の自動トークンリフレッシュ対応
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead バイアスを防止
- DuckDB ベースのスキーマ管理
  - Raw / Processed / Feature / Execution / Audit 各レイヤのテーブル定義とインデックス
  - 初期化用ユーティリティ（init_schema / init_audit_db 等）
- ETL パイプライン
  - 差分更新＋バックフィル機能（最後に取得した日付を基に自動算出）
  - 市場カレンダー先読み、品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集
  - RSS から記事を収集して DuckDB に冪等保存
  - URL 正規化＆トラッキング除去、SSRF 対策、受信サイズ制限、gzip 解凍対策等の安全設計
- 監査ログ（Audit）
  - signal → order_request → execution のトレーサビリティを UUID 連鎖で保持
  - 発注冪等キー（order_request_id）やタイムスタンプ（UTC）を必須とする設計

---
## 必要条件
- Python 3.9+
- 推奨ライブラリ（主要な依存）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API 等）

（実際のパッケージ化時に requirements.txt / pyproject.toml に依存関係を追加してください）

---
## セットアップ手順（開発向け）
1. リポジトリをクローン／作業ディレクトリへ移動
2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール（例）
   ```bash
   pip install duckdb defusedxml
   # またはパッケージ化されていれば:
   # pip install -e .
   ```
4. 環境変数の設定
   - プロジェクトルートの `.env` または `.env.local` を作成すると自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD : kabuステーション API パスワード
     - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID : Slack チャンネル ID
   - 任意（デフォルトがあるもの）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト `development`
     - LOG_LEVEL (DEBUG|INFO|...) — デフォルト `INFO`
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する場合に `1`
     - KABUSYS_ENABLE_... 等（将来的に追加される可能性あり）
   - DB パス（デフォルト）
     - DUCKDB_PATH : デフォルト `data/kabusys.duckdb`
     - SQLITE_PATH : デフォルト `data/monitoring.db`

例 .env（参考）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---
## 使い方（コード例）
以下は代表的な利用例です。Python スクリプトやバッチから利用してください。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- J-Quants の ID トークン取得（リフレッシュ）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を利用
```

- 日次 ETL 実行（株価・財務・カレンダーの差分取得＋品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- ニュース収集ジョブ実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄コードの集合（例: {"7203","6758",...}）
res = run_news_collection(conn, sources=None, known_codes=None)
print(res)  # ソースごとの新規保存件数
```

- 監査ログスキーマ初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/kabusys_audit.duckdb")
```

- J-Quants データ取得（個別）
```python
from kabusys.data.jquants_client import fetch_daily_quotes
records = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,3,31))
```

ログやエラーは標準 logging ライブラリに出力されます。環境変数 `LOG_LEVEL` で制御してください。

---
## 注意点（設計上の重要事項）
- J-Quants API 呼び出しは内部でレートリミッタとリトライを行いますが、利用側でも過度に短い間隔でのループ呼び出しに注意してください。
- news_collector は SSRF や XML 攻撃対策を多重に実装しています。外部 URL をそのまま信頼しない運用を推奨します。
- DuckDB スキーマ初期化は冪等であり、既存テーブルがあっても上書きしません（CREATE IF NOT EXISTS を使用）。
- audit スキーマはタイムゾーンを UTC に固定します（init_audit_schema 内で SET TimeZone='UTC' を実行）。

---
## ディレクトリ構成
リポジトリ内の主な構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定管理（.env 自動ロード機能含む）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存処理）
    - news_collector.py       — RSS ニュース収集・保存ロジック
    - schema.py               — DuckDB スキーマ定義と初期化ユーティリティ
    - pipeline.py             — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py  — 市場カレンダー管理ユーティリティ
    - audit.py                — 監査ログ（signal/order/execution）スキーマ & 初期化
    - quality.py              — データ品質チェック
  - strategy/
    - __init__.py
    - (戦略実装モジュールを配置)
  - execution/
    - __init__.py
    - (発注/ブローカ連携モジュールを配置)
  - monitoring/
    - __init__.py
    - (監視/メトリクス関連モジュールを配置)

---
## よくある運用ワークフロー（例）
1. init_schema() で DuckDB を初期化
2. 毎朝 run_daily_etl() をバッチで実行（スケジューラ: cron / Airflow 等）
3. ニュースは定期的に run_news_collection() で収集
4. 戦略は features / ai_scores を参照して signals を生成し、signal_queue → 発注 → executions の流れで処理
5. audit テーブルで end-to-end のトレーサビリティを確保

---
## 今後の拡張案（参考）
- CLI ユーティリティ（init / run-etl / collect-news など）
- retry/backoff ポリシーの外部設定化
- Prometheus / メトリクス連携
- 詳細な運用ドキュメント（DB マイグレーション、バックアップ、権限管理）

---
## サポート / 貢献
バグ報告や機能追加の提案は Issue を立ててください。プルリクエスト歓迎です。

---

README はこのプロジェクトの現状の実装（コードベース）に基づく概要と利用例を示しています。実運用の前に必ず環境変数や DB のバックアップ、権限設定、シークレット管理（Vault 等）を適切に行ってください。