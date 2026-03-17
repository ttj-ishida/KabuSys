# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（プロジェクト骨格）。  
本リポジトリはデータ取得・ETL・データ品質チェック・カレンダー管理・ニュース収集・監査ログなど、アルゴリズム取引基盤で必要となる主要機能をモジュール化して提供します。

主な設計方針
- データ取得は冪等（ON CONFLICT）で保存し、後出し修正を吸収するバックフィルをサポート
- API レート制限・リトライ・トークン自動更新などの堅牢性を考慮
- ニュース収集では SSRF 対策・XML 注入対策・受信サイズ制限を実装
- DuckDB をベースにスキーマを定義し、Feature/Execution/Audit 層を分離

----------------------------------------------------------------------
目次（この README の構成）
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（利用例）
- 環境変数一覧（.env）
- ディレクトリ構成（ファイル一覧と各説明）
----------------------------------------------------------------------

プロジェクト概要
- KabuSys は日本株向けの自動売買/データ基盤モジュール群です。  
  データ取得（J-Quants）、ニュース収集（RSS）、DuckDB スキーマ管理、ETL パイプライン、データ品質チェック、マーケットカレンダー管理、監査ログ用スキーマ等を含みます。
- コアは Python パッケージとして提供され、既存の取引エンジンや監視系と連携して利用可能です。

機能一覧
- 環境設定読み込み
  - .env / .env.local または OS 環境変数から自動読込（プロジェクトルート検出）
  - 必須環境変数チェック（settings オブジェクト）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得
  - レート制限（120 req/min）、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存用ユーティリティ（save_*）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、テキスト前処理、記事ID生成（URL 正規化＋SHA-256）
  - SSRF 対策、defusedxml による XML 保護、受信サイズ制限
  - DuckDB への冪等保存（raw_news）と銘柄紐付け（news_symbols）
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化（init_schema）
  - インデックス作成
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日からの差分）、バックフィル、品質チェックの統合 run_daily_etl
  - 個別 ETL（prices / financials / calendar）の実行関数
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日取得、期間内の営業日列挙、夜間カレンダー更新ジョブ
- 監査ログスキーマ（kabusys.data.audit）
  - signal_events / order_requests / executions 等、監査用テーブル初期化（init_audit_db）
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合検出。QualityIssue を返す run_all_checks

セットアップ手順
- 推奨 Python バージョン
  - Python >= 3.10（typing の | などを使用）
- 依存パッケージ（最低限）
  - pip install duckdb defusedxml
  - 標準ライブラリのみで動作する部分もありますが、上記は必須に近いです。
- インストール例
  - 仮想環境作成（推奨）
    - python -m venv .venv
    - source .venv/bin/activate (Windows: .venv\Scripts\activate)
  - パッケージインストール
    - pip install duckdb defusedxml
    - （将来的に requirements.txt があれば pip install -r requirements.txt）
- 環境変数 (.env)
  - プロジェクトルートに .env / .env.local を置くと自動読み込みされます（.git または pyproject.toml をプロジェクトルート判定に使用）。
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

必須環境変数（代表）
- JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD - kabuステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN - Slack 通知用 BOT トークン（必須）
- SLACK_CHANNEL_ID - Slack チャンネル ID（必須）

その他（デフォルトあり）
- KABUSYS_ENV - development | paper_trading | live （デフォルト: development）
- LOG_LEVEL - DEBUG|INFO|WARNING|ERROR|CRITICAL （デフォルト: INFO）
- KABUS_API_BASE_URL - kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH - デフォルト DB パス（data/kabusys.duckdb）
- SQLITE_PATH - monitoring 用 SQLite パス（data/monitoring.db）

例: .env（最小）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO

使い方（基本的な利用例）
- 初期スキーマ作成（DuckDB）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ファイルを自動作成
```

- 日次 ETL 実行（J-Quants から差分取得して保存 → 品質チェックを実行）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- ニュース収集ジョブ実行
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes を与えるとテキストから銘柄コード抽出して news_symbols に紐付ける
known_codes = {"7203", "6758", "9984"}
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)  # {source_name: saved_count}
```

- カレンダー更新ジョブ（夜間バッチ想定）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn, lookahead_days=90)
print("saved:", saved)
```

- 監査ログスキーマ初期化（監査専用 DB を用いる場合）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

- 設定の参照
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.kabu_api_base_url)
print(settings.env)
```

主要パブリック API の一覧（抜粋）
- kabusys.config.settings - 環境設定オブジェクト
- kabusys.data.schema.init_schema(db_path)
- kabusys.data.jquants_client.get_id_token(refresh_token=None)
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.save_daily_quotes(conn, records)
- kabusys.data.pipeline.run_daily_etl(...)
- kabusys.data.news_collector.fetch_rss(url, source, timeout=30)
- kabusys.data.news_collector.save_raw_news(conn, articles)
- kabusys.data.news_collector.run_news_collection(conn, sources=None, known_codes=None)
- kabusys.data.calendar_management.is_trading_day(...)
- kabusys.data.calendar_management.calendar_update_job(...)
- kabusys.data.audit.init_audit_db(db_path)
- kabusys.data.quality.run_all_checks(conn, target_date=None, reference_date=None)

注意点 / 実装上のポイント
- jquants_client は内部でレートリミッタ（120 req/min）とリトライ機構を保持しています。429/408/5xx に対して指数バックオフでリトライし、401 時はリフレッシュトークンを使って自動再取得を行います。
- news_collector は URL 正規化、トラッキングパラメータ除去、ID は正規化 URL の SHA-256 (先頭32文字) を採用して冪等性を確保しています。SSRF 対策としてリダイレクト先の検査・プライベートアドレス拒否・スキーム検査を行います。
- DuckDB へは SQL のパラメータバインド（?）で値を渡していますが、一部の大量挿入ではプレースホルダを文字列連結で構築する実装箇所があります。信頼できる入力（内部で生成したもの）を用いるか、外部入力は十分検証してください。
- ETL は Fail-Fast ではなく、可能な範囲で処理を継続し結果を ETLResult にまとめます。品質チェック結果は呼び出し元で判断してください。

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py - パッケージ初期化、__version__
  - config.py - 環境変数/設定管理（.env 自動読込、settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py - J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py - RSS ニュース収集・保存・銘柄抽出
    - schema.py - DuckDB スキーマ定義・init_schema/get_connection
    - pipeline.py - ETL パイプライン（run_daily_etl 等）
    - calendar_management.py - マーケットカレンダー操作・更新ジョブ
    - audit.py - 監査ログ（signal_events, order_requests, executions）
    - quality.py - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py - 戦略モジュール用プレースホルダ
  - execution/
    - __init__.py - 発注/ブローカー連携用プレースホルダ
  - monitoring/
    - __init__.py - 監視・メトリクス用プレースホルダ

拡張 / 次のステップ案
- strategy モジュールに戦略実装（シグナル生成）を追加して signals テーブルへ出力
- execution モジュールで kabu API と連携して発注を自動化（order_requests / executions と監査）
- monitoring に Prometheus / Slack 通知連携を追加
- CI で DuckDB を使った統合テストを追加

ライセンス / 貢献
- （この README はコードベースからの抜粋ドキュメントです。実際のライセンスやコントリビューションポリシーはリポジトリルートの LICENSE / CONTRIBUTING を参照してください。）

以上。プロジェクトの他モジュール（strategy / execution / monitoring）は骨格のみです。必要があれば README に追記する利用シナリオや詳細な API ドキュメント（各関数の細かい引数説明・戻り値例）を追加します。