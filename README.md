# KabuSys

KabuSys は日本株向けの自動売買基盤（プロトタイプ）です。  
データ取得（J-Quants）、ETL、データ品質チェック、DuckDB ベースのスキーマ、監査ログ（シグナル→発注→約定のトレーサビリティ）などを備え、戦略／発注層と組み合わせて自動売買ワークフローを構築できるように設計されています。

バージョン: 0.1.0

---

## 特徴（機能一覧）

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得
  - API レート制御（120 req/min）、指数バックオフによるリトライ、401 時の自動トークンリフレッシュ
  - ページネーション対応、取得時刻（fetched_at）を UTC で記録
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ETL パイプライン
  - 差分更新（DB の最終取得日を基に未取得分のみ取得）
  - バックフィル（後出し修正の吸収）
  - 市場カレンダー先読み（デフォルト 90 日）
  - 単体関数（run_prices_etl / run_financials_etl / run_calendar_etl）と日次統合エントリ（run_daily_etl）

- データ品質チェック
  - 欠損データ、スパイク（前日比閾値）、主キー重複、日付不整合（将来日付・非営業日）を検出
  - 問題は QualityIssue オブジェクトのリストで返却。Fail-Fast ではなく全件収集

- DuckDB スキーマ
  - Raw / Processed / Feature / Execution の 3 層（＋監査テーブル）を定義
  - 頻出クエリ向けのインデックスを作成
  - init_schema() による初期化（冪等）

- 監査ログ（audit）
  - signal_events, order_requests, executions テーブルでシグナルから約定までを UUID で追跡
  - order_request_id を冪等キーとして扱い二重発注を防止
  - すべての TIMESTAMP は UTC で保存（監査 DB 初期化時に SET TimeZone='UTC'）

- 設定管理
  - .env（および .env.local）/ 環境変数から設定を自動ロード（プロジェクトルート判定）
  - 必須環境変数チェックとヘルパー（settings）

---

## セットアップ手順

前提:
- Python 3.9+（typing の | を使っているため 3.10 推奨）
- pip 等のパッケージ管理ツール
- DuckDB（Python パッケージ経由でインストール）

1. リポジトリをクローンしてパッケージをインストール
   - 開発時: pip install -e .
   - または必要な依存を requirements.txt からインストール（本リポジトリに記載がある場合）

2. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml がある位置）に `.env` または `.env.local` を置くと自動読み込みされます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。
   - 読み込み優先順位: OS 環境変数 > .env.local > .env

3. 必須環境変数（少なくともこれらを設定してください）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack 通知用 BOT トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネルID

   その他（任意／デフォルトあり）:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB など（デフォルト: data/monitoring.db）

4. DuckDB スキーマ初期化（例）
   - Python REPL またはスクリプト内で:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ専用 DB を作る場合:
     ```python
     from kabusys.data import audit
     conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（基本例）

以下は典型的なデータ取得 / ETL の流れの例です。

- DuckDB を初期化して日次 ETL を実行する:
  ```python
  from kabusys.data import schema, pipeline
  from kabusys.config import settings
  from datetime import date

  # DB 初期化（存在しない場合はファイルと親ディレクトリを作成）
  conn = schema.init_schema(settings.duckdb_path)

  # 日次 ETL（省略すると target_date は今日）
  result = pipeline.run_daily_etl(conn, target_date=date.today())

  # 結果確認
  print(result.to_dict())
  ```

- J-Quants API クライアントを直接使う（トークンは settings 経由で自動取得）
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.config import settings

  # トークンは内部で settings.jquants_refresh_token を使って取得・キャッシュされる
  daily = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
  ```

- データ品質チェックだけ実行する:
  ```python
  from kabusys.data import quality, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn, target_date=None)  # target_date を指定して絞り込める
  for i in issues:
      print(i)
  ```

- 監査スキーマの初期化（既存接続へ追加）
  ```python
  from kabusys.data import audit, schema
  conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB を利用
  audit.init_audit_schema(conn)
  ```

注意点:
- jquants_client はレート制限とリトライを内蔵していますが、アプリ側でも並列リクエストや大量取得時の制御を検討してください。
- run_daily_etl は各ステップで例外を捕捉し、他ステップは継続する設計です。戻り値の ETLResult で発生したエラーや品質問題を確認して対処してください。

---

## 設定（settings）について

settings は環境変数から値を取得するラッパーです。主なプロパティ:

- jquants_refresh_token: JQUANTS_REFRESH_TOKEN（必須）
- kabu_api_password: KABU_API_PASSWORD（必須）
- kabu_api_base_url: KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- slack_bot_token: SLACK_BOT_TOKEN（必須）
- slack_channel_id: SLACK_CHANNEL_ID（必須）
- duckdb_path: DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- sqlite_path: SQLITE_PATH（デフォルト: data/monitoring.db）
- env: KABUSYS_ENV（development / paper_trading / live）
- log_level: LOG_LEVEL（DEBUG/INFO/...）

.env.example を作成して必要事項を埋めてください。

自動ロードの振る舞い:
- プロジェクトルート（.git または pyproject.toml を探索）を起点に `.env` / `.env.local` を読み込みます。
- OS の環境変数が優先され、.env.local は .env を上書きできます。
- テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成

以下は主要なファイル・モジュールのツリー（抜粋）です。

- src/kabusys/
  - __init__.py                -- パッケージ定義（__version__ = "0.1.0"）
  - config.py                  -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py        -- J-Quants API クライアント（取得・リトライ・保存）
    - schema.py                -- DuckDB スキーマ定義・初期化（Raw/Processed/Feature/Execution）
    - pipeline.py              -- ETL パイプライン（差分更新、日次 ETL）
    - quality.py               -- データ品質チェック
    - audit.py                 -- 監査ログ（signal_events, order_requests, executions）
    - pipeline.py              -- ETL 実行フロー
  - strategy/
    - __init__.py              -- 戦略関連（未実装箇所のプレースホルダ）
  - execution/
    - __init__.py              -- 発注実行関連（未実装箇所のプレースホルダ）
  - monitoring/
    - __init__.py              -- 監視関連（プレースホルダ）

---

## 開発・運用に関する注意

- 設計上、ETL は冪等性を重視しており、同一データを何度書き込んでも上書きで正しく保たれます（ON CONFLICT DO UPDATE）。
- 監査ログテーブルは基本的に削除せず永続保存する前提です（ON DELETE RESTRICT による保護）。
- すべてのタイムスタンプは UTC を使用するよう設計されています。監査 DB 初期化時に TimeZone を UTC に設定します。
- KABUSYS_ENV が `live` の場合は本番挙動（発注など）に関する追加チェックを入れることを強く推奨します（本リポジトリは発注接続の保護やテスト機能実装が必要）。

---

## トラブルシューティング

- .env が読み込まれない場合:
  - プロジェクトルートが .git / pyproject.toml で検出できているか確認
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認
  - 必須環境変数が設定されていない場合は settings プロパティアクセス時に ValueError が発生します

- J-Quants リクエストで 401 が返る:
  - jquants_client は 1 回自動で token をリフレッシュして再試行します。リフレッシュに失敗する場合はリフレッシュトークン（JQUANTS_REFRESH_TOKEN）が正しいか確認してください。

- DuckDB 関連エラー:
  - DB ファイルの親ディレクトリが存在しない場合は init_schema が自動作成しますが、権限等で作成できない場合はパスを確認してください。

---

README は以上です。追加で以下を用意することを推奨します:
- .env.example（必要な環境変数一覧と説明）
- requirements.txt / pyproject.toml（依存管理）
- usage スクリプト例（run_daily_etl をスケジューラで回す例、ロギング設定、Slack 通知連携）