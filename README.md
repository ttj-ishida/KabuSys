# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（KabuSys）。  
J-Quants API や RSS フィードから市場データ・ニュースを収集し、DuckDB に保存・整形して戦略・発注層に渡すための ETL / スキーマ / 監査・品質管理機能を提供します。

## 主要な特徴
- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - レート制限（120 req/min）の厳守（固定間隔スロットリング）
  - 再試行（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止
  - DuckDB への冪等保存（ON CONFLICT 更新）
- ニュース収集（RSS）
  - RSS フィード取得・前処理（URL 除去、空白正規化）
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で冪等化
  - SSRF 対策、受信サイズ上限、gzip 解凍後の検査、XML パーサの安全化（defusedxml）
  - raw_news / news_symbols への安全・効率的な保存（チャンク・トランザクション）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 各レイヤのテーブル定義とインデックス
  - init_schema(), init_audit_db() による冪等初期化
- ETL パイプライン
  - 差分取得（最終取得日基準の差分）＋バックフィル（デフォルト 3 日）
  - カレンダー先読み（デフォルト 90 日）
  - 品質チェック（欠損・スパイク・重複・日付不整合）を実装
  - run_daily_etl() による一括実行（個別ジョブも呼べます）
- データ品質・監査
  - quality モジュールによる多彩なチェック（QualityIssue を返す）
  - audit モジュールによる発注／約定の監査テーブル（トレーサビリティ）

---

## 必要条件
- Python 3.10 以上（PEP 604 の型記法などを使用）
- 依存パッケージ（最低限）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）

（パッケージ管理ファイルは README に含まれていません。プロジェクトの配布方法に合わせて requirements.txt / pyproject.toml を用意してください。）

---

## 環境変数（重要）
プロジェクトは .env / .env.local から自動で環境変数を読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。必須・よく使う環境変数は以下の通りです。

必須（Settings のプロパティ参照で ValueError を投げます）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack ボットトークン（通知に使用する想定）
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動読み込みの詳細:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に `.env` と `.env.local` を読み込みます。
- OS 環境変数が優先され、.env の上に .env.local の値が上書きされます（ただし既存の OS 環境変数は保護されます）。

---

## セットアップ手順（開発者向け・クイックスタート）
1. リポジトリをクローン
2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール
   (プロジェクトによっては pyproject.toml / requirements.txt を用意してください)
   ```
   pip install duckdb defusedxml
   ```
4. 必要な環境変数を .env に設定（上記参照）
5. DuckDB スキーマ初期化
   - Python REPL やスクリプトから:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ専用 DB を分ける場合:
     ```python
     from kabusys.data.audit import init_audit_db
     conn_audit = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（主要な API と実行例）

- 設定を参照する
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

- J-Quants の ID トークンを取得
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

- ETL（デイリー）を実行する（単純起動例）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- 個別 ETL ジョブを呼ぶ
  ```python
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  # 例: 株価差分取得
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  ```

- ニュース収集
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  # known_codes は銘柄抽出に利用する有効な銘柄コード集合
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set(["7203","6758"]))
  print(results)  # {source_name: 新規保存件数}
  ```

- カレンダー夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"saved calendar rows: {saved}")
  ```

- 品質チェック
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

ログ出力は settings.log_level に従います。開発時は DEBUG にすると詳細ログが見られます。

---

## 主要モジュールの説明（短い概要）
- kabusys.config
  - 環境変数のロード / Settings クラス（必須変数チェック含む）
  - .env 自動読み込みとオーバーライドルール
- kabusys.data.jquants_client
  - J-Quants API 呼び出し、トークン取得、fetch/save 関数（daily quotes, financials, market calendar）
  - レート制御・リトライ・トークン自動更新実装
- kabusys.data.news_collector
  - RSS 収集、前処理、記事 ID 生成、DuckDB 保存、銘柄抽出
  - SSRF 対策・XML 安全パーサ・受信サイズ制限
- kabusys.data.schema
  - DuckDB スキーマ定義（全テーブル / インデックス）と init_schema()
- kabusys.data.pipeline
  - 差分 ETL、backfill、カレンダー先読み、品質チェック、run_daily_etl()
- kabusys.data.calendar_management
  - 営業日判定、next/prev_trading_day、calendar_update_job
- kabusys.data.audit
  - 監査テーブル定義、init_audit_db()
- kabusys.data.quality
  - 欠損・スパイク・重複・日付不整合チェック
- kabusys.strategy, kabusys.execution, kabusys.monitoring
  - パッケージスケルトン（将来的な戦略/発注/監視ロジックを想定）

---

## ディレクトリ構成（抜粋）
プロジェクトルートの src/kabusys 以下に主要ファイルがあります。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - schema.py
      - calendar_management.py
      - quality.py
      - audit.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

各ファイルの目的は上記「主要モジュールの説明」を参照してください。

---

## 注意点 / 運用上のヒント
- 環境変数は必須項目があり、未設定の場合は起動時にエラーとなる箇所があります（Settings._require によるチェック）。
- J-Quants API のレート制限を尊重してください。クライアントは 120 req/min を想定しています。
- DuckDB のスキーマ初期化は冪等です。複数回実行しても問題ありません。
- ニュース収集では外部 URL を扱うため SSRF 等のリスク対策が組み込まれていますが、社内運用ではさらにネットワークポリシーで保護してください。
- ETL 実行は失敗耐性を持ちますが、品質チェックで重大な問題が検出された場合は運用判断（再実行・アラート）が必要です。
- ログや監視（Slack 通知等）は本 README のコード内では省略されているため、運用に合わせて実装・接続してください。

---

この README はコードベースからの要点をまとめたものです。詳細な API や運用フロー、外部サービスとの連携方法はプロジェクト内のドキュメント（DataPlatform.md 等）やコードコメントを参照してください。必要であれば README を英語版にする、または追加の Usage examples / CLI スクリプトを作成する提案も可能です。