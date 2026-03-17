# KabuSys

日本株向けの自動売買基盤コンポーネント群（KabuSys）。J-Quants / kabuステーション等の外部APIと連携してデータ収集（株価・財務・カレンダー・ニュース）、ETL、品質チェック、監査ログ、実行レイヤのためのスキーマ／ユーティリティを提供します。

## プロジェクト概要
- J-Quants API を使った株価（日足）、財務（四半期BS/PL）、JPXマーケットカレンダーの取得
- RSS フィードからのニュース収集（前処理・記事ID生成・銘柄紐付け）
- DuckDB を用いた3層データレイヤ（Raw / Processed / Feature）および Execution / Audit テーブル定義と初期化
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- ニュース収集における SSRF 対策・XML 攻撃対策・受信サイズ制限などのセキュリティ設計
- 各モジュールは冪等性（ON CONFLICT）やリトライ、レート制御を考慮して設計されています

## 主な機能
- データ取得
  - 株価日足（OHLCV）取得（ページネーション、レート制御、リトライ、トークン自動リフレッシュ）
  - 財務データ（四半期）取得
  - JPX マーケットカレンダー取得
- 保存／スキーマ
  - DuckDB のスキーマ初期化（raw / processed / feature / execution 層）
  - 監査ログ（signal_events / order_requests / executions）用スキーマと初期化
- ETL / パイプライン
  - 差分更新（最終取得日からの差分算出）、バックフィル、品質チェック統合
  - 日次 ETL エントリポイント（run_daily_etl）
- ニュース収集
  - RSS フィード取得、HTML/XML 安全パース（defusedxml）、URL 正規化（トラッキング除去）、記事ID生成（SHA-256）
  - SSRF 対策（リダイレクト検査、プライベートIP拒否）、受信サイズ制限、DB への冪等保存
- データ品質チェック
  - 欠損データ、スパイク（前日比）、主キー重複、日付不整合（将来日付・非営業日）検出
- 設定管理
  - .env ファイルまたは環境変数の自動読み込み（プロジェクトルート検出）
  - 必須設定の取得ラッパ

## 要件
- Python 3.10+
- 依存ライブラリ（例）
  - duckdb
  - defusedxml
- （任意）J-Quants API の利用には API トークン、kabuステーション 連携にはパスワード等の環境変数が必要

## セットアップ手順（開発 / 実行向け）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject があればそちらを使用してください）

4. 環境変数設定
   プロジェクトルート（.git または pyproject.toml を基準）に `.env` または `.env.local` を配置すると、自動的に読み込まれます（自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   
   主な必須環境変数:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API 用パスワード
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      : Slack チャンネル ID

   任意 / デフォルトあり:
   - KABUSYS_ENV : development / paper_trading / live（デフォルト development）
   - LOG_LEVEL   : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite パス（デフォルト data/monitoring.db）
   - KABU_API_BASE_URL : kabuAPI のベース URL（デフォルト http://localhost:18080/kabusapi）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. DuckDB スキーマ初期化
   Python REPL またはスクリプトから init_schema を呼び出します。

   例:
   python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

   監査ログ専用 DB を作る場合:
   python -c "from kabusys.data.audit import init_audit_db; init_audit_db('data/kabusys_audit.duckdb')"

## 使い方（代表的な利用例）

- 設定オブジェクトの参照
  from kabusys.config import settings
  token = settings.jquants_refresh_token

- DuckDB 接続の初期化
  from kabusys.data.schema import init_schema, get_connection
  conn = init_schema('data/kabusys.duckdb')  # 新規初期化
  # 既存 DB へ接続するだけ:
  conn = get_connection('data/kabusys.duckdb')

- 日次 ETL 実行（J-Quants から差分取得・保存・品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import get_connection
  conn = get_connection('data/kabusys.duckdb')
  result = run_daily_etl(conn)
  print(result.to_dict())

- 市場カレンダー更新ジョブ
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)

- RSS ニュース収集（テスト的な呼び出し）
  from kabusys.data.news_collector import run_news_collection
  results = run_news_collection(conn, sources=None, known_codes={'7203','6758'})
  print(results)

- J-Quants 生データ取得（個別）
  from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements, get_id_token
  token = get_id_token()
  records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)

注意:
- run_daily_etl 等の関数は内部で例外を吸収しつつ処理を継続する設計です。戻り値（ETLResult）でエラーや品質問題の概要を確認してください。
- J-Quants API はレート制限（120 req/min）に従うよう組み込まれています。大量取得時は処理時間を考慮してください。

## 自動環境読み込みの挙動
- パッケージの config モジュールは、プロジェクトルート（.git または pyproject.toml を含む親ディレクトリ）を起点に .env と .env.local を自動読み込みします。
  - 読み込み優先度: OS 環境変数 ＞ .env.local ＞ .env
  - OS に既に定義された環境変数は上書きされません（ただし .env.local は override=True で上書きできますが、protected な OS 変数は保持されます）
- テスト等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## セキュリティ・堅牢性に関する設計メモ（抜粋）
- J-Quants クライアントは指数バックオフを用いたリトライ、401 受信時の自動トークンリフレッシュ、固定間隔スロットリングによるレート制御を実装
- ニュース収集は defusedxml による XML パース、Gzip サイズチェック、受信上限（10MB）、リダイレクト先のスキーム/内部IPチェック（SSRF対策）を実施
- DB 保存は冪等（ON CONFLICT）で重複を排除
- ETL は差分取得・バックフィル（後出し修正吸収）を標準とし、品質チェックを行うことでデータ健全性を担保

## ディレクトリ構成
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py  — パッケージ定義（バージョン）
  - config.py    — 環境変数・設定管理（.env 自動読み込み、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py     — RSS ニュース収集・前処理・保存ロジック
    - schema.py             — DuckDB スキーマ定義・初期化
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py— マーケットカレンダー管理・ユーティリティ
    - audit.py              — 監査ログスキーマ（signal / order / execution の監査）
    - quality.py            — データ品質チェック
  - strategy/
    - __init__.py           — 戦略モジュール（拡張用）
  - execution/
    - __init__.py           — 発注・実行関連（拡張用）
  - monitoring/
    - __init__.py           — 監視・アラート関連（拡張用）

（上のモジュール群はそれぞれ ETL / 実行 / 監視パイプラインのビルディングブロックとなります）

## 開発上のヒント
- テストでは settings の自動 .env 読み込みを無効化して差し替え可能（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）
- ネットワーク依存の関数（_urlopen など）はモック可能な設計になっています
- DuckDB を使うことでローカルテストや CI でのインメモリ(":memory:")利用が容易です

---

追加で README に載せたい内容（例: ライセンス、CI、具体的な CLI/デーモン実行方法、Slack 通知や実際の発注フローの注意点など）があれば教えてください。必要に応じてサンプルスクリプトや systemd / cron ジョブ例も作成できます。