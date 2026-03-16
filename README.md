# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータ取得・ETL・品質チェック・監査ログ基盤を備えた自動売買プラットフォームのコアライブラリです。J-Quants API から市場データ・財務データ・マーケットカレンダーを取得し、DuckDB に冪等に保存、品質チェックを実行して戦略層／発注層へ受け渡すための基盤機能を提供します。

主な特徴
- J-Quants API クライアント（トークン自動リフレッシュ、レート制限、リトライ、ページネーション対応）
- DuckDB ベースのスキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- ETL パイプライン（差分更新、バックフィル、先読みカレンダー）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 環境変数／.env 自動読み込み（プロジェクトルート検出、.env/.env.local 優先度）

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（コード例）
- ディレクトリ構成
- 環境変数（必須・任意）
- 開発メモ / 注意事項

プロジェクト概要
- パッケージ名: kabusys
- 目的: 日本株自動売買システム向けに信頼性の高いデータ基盤と監査基盤を提供すること
- 設計上の留意点:
  - Look-ahead bias 回避のため fetched_at を UTC で記録
  - API レート制限遵守（J-Quants: 120 req/min）
  - 冪等性を重視（DuckDB への INSERT は ON CONFLICT DO UPDATE）
  - 品質チェックは Fail-Fast にせず、全問題を収集して呼び出し元が判断可能

機能一覧
- 環境設定読み込み（kabusys.config）
  - .env/.env.local を自動読み込み（プロジェクトルートを .git または pyproject.toml で推定）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能
  - settings オブジェクト経由で設定取得
- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（リフレッシュトークン→IDトークン）
  - レートリミット、指数バックオフ、401 時のトークン自動更新
  - DuckDB に保存する save_* 関数（冪等）
- スキーマ管理（kabusys.data.schema）
  - init_schema(db_path) で DuckDB の全テーブル・インデックスを冪等に作成
  - init_audit_schema / init_audit_db による監査テーブル初期化
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl: 市場カレンダー → 株価 → 財務 → 品質チェック の一括処理
  - 差分更新、バックフィル、カレンダー先読み
  - ETLResult により処理結果と品質問題を返却
- 品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合 を SQL ベースで検出
  - QualityIssue オブジェクトのリストを返す
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の DDL と初期化関数
  - 発注の冪等キー（order_request_id）による二重発注防止を想定

セットアップ手順
前提
- Python 3.10 以上（'|' 型ユニオン、型注釈の記法を使用）
- DuckDB を使用するため duckdb パッケージが必要

インストール（開発時）
1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (UNIX/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - 最低限: duckdb
   - pip install duckdb
   - 実際のプロジェクトでは requirements.txt や pyproject.toml に合わせてインストールしてください。

4. パッケージをインストール（編集可能な状態）
   - pip install -e .

環境変数設定
- プロジェクトルートの .env または .env.local に設定を記載してください。
- 自動ロードはデフォルト有効。テスト等で無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数（必須 / 推奨）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- KABU_API_BASE_URL (任意) — kabuAPI ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH (任意) — デフォルト data/kabusys.duckdb
- SQLITE_PATH (任意) — 監視用途の SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

使い方（コード例）
1) DuckDB スキーマ初期化
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリがなければ自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行する（J-Quants トークンは settings から自動取得）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

3) 監査ログスキーマを初期化する（既存接続に追加）
```python
from kabusys.data import audit

audit.init_audit_schema(conn)
# あるいは専用 DB を作る
# audit_conn = audit.init_audit_db("data/audit.duckdb")
```

4) J-Quants からデータを直接取得して保存する（個別利用）
```python
from kabusys.data import jquants_client as jq

# ID トークンを自動取得
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
saved = jq.save_daily_quotes(conn, records)
```

5) 品質チェックを単独で実行
```python
from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

API の振る舞い（主要ポイント）
- jquants_client._request:
  - レート制限: 120 req/min を固定間隔で守る
  - リトライ: 最大 3 回（指数バックオフ）、408/429/5xx を対象
  - 401 を受けた場合は ID トークンを自動更新して1回再試行
- save_* 関数:
  - DuckDB への挿入は ON CONFLICT DO UPDATE を使い冪等
  - PK 欠損のレコードはスキップして警告ログ出力
- pipeline.run_daily_etl:
  - カレンダー→株価→財務→品質チェックの順で実行
  - 各ステップで例外が発生しても他ステップは継続
  - ETLResult で取得件数・保存件数・品質問題・エラー一覧を返す

ディレクトリ構成
（抜粋: src/kabusys 以下）
- src/
  - kabusys/
    - __init__.py            : パッケージ定義（__version__ 等）
    - config.py              : 環境変数 / 設定管理（.env 自動ロード、settings オブジェクト）
    - data/
      - __init__.py
      - jquants_client.py    : J-Quants API クライアント（取得・保存・認証・レート制御）
      - schema.py            : DuckDB スキーマ定義・初期化（全テーブル・インデックス）
      - pipeline.py          : ETL パイプライン（差分更新・品質チェック）
      - audit.py             : 監査ログ（signal/order_request/execution）DDL と初期化
      - quality.py           : データ品質チェック（欠損・スパイク・重複・日付不整合）
      - ... (将来的に raw/news クローラ等)
    - strategy/
      - __init__.py          : 戦略層（プレースホルダ、実装はプロジェクト毎に追加）
    - execution/
      - __init__.py          : 発注・ブローカー連携（プレースホルダ）
    - monitoring/
      - __init__.py          : 監視用モジュール（プレースホルダ）

開発メモ / 注意事項
- Python バージョンは 3.10 以上を推奨します（型注釈の "X | Y" 記法を使用）。
- .env の自動ロードはプロジェクトルートを .git または pyproject.toml で検出します。別パスで運用する場合は環境変数を直接設定するか、KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- 実運用での発注機能（execution/strategy）はこのコードベースには最小限のスケルトンしか含まれていません。ブローカーとの安全な接続やリスク管理ロジックはプロジェクト固有に実装してください。
- DuckDB のファイルパスはデフォルトで data/kabusys.duckdb に設定されています。運用時は適切な永続ストレージを確保してください。
- 監査ログは削除しない前提（ON DELETE RESTRICT 等）で設計されています。運用ポリシーに合わせてバックアップ／保持戦略を整備してください。

補足（トラブルシューティング）
- J-Quants のトークンが無効で get_id_token が失敗する場合、kabusys.config.settings.jquants_refresh_token の値を確認してください。
- API レート超過や 429 応答時は retry-after ヘッダを尊重し指数バックオフでリトライします。大量の一括取得は注意して実行してください。

ライセンスや貢献方法などはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

以上。必要であれば README にサンプル .env.example、CI 実行例、より詳細な API リファレンスや使用例（ユースケース別）を追記します。どの情報を追加しますか？