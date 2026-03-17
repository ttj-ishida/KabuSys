# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得・ETL・スキーマ管理、ニュース収集、監査ログ、品質チェックなどを提供するモジュール群です。

現状はライブラリ層の実装が中心で、運用用の CLI やサービスラッパーは別途作成して利用します。

---

## 主要機能概要

- 環境設定管理
  - `.env` / `.env.local` 自動ロード（必要に応じて無効化可能）
  - 必須環境変数の取得とバリデーション

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期）、JPX カレンダーの取得
  - API レート制御（120 req/min 固定間隔スロットリング）
  - 再試行（指数バックオフ、3回）、401 の自動トークンリフレッシュ
  - ページネーション対応、取得時刻（fetched_at）でトレーサビリティ保持
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・前処理・正規化
  - URL 正規化（トラッキングパラメータ除去）、記事ID は正規化 URL の SHA256（先頭32桁）
  - SSRF 対策（スキーム検証、プライベートアドレス検出、リダイレクト検査）
  - defusedxml による XML 攻撃対策、gzip サイズ上限チェック
  - DuckDB への冪等保存（INSERT ... RETURNING、トランザクション単位でチャンク挿入）
  - テキストからの銘柄コード抽出（既知コードセットによるフィルタ）

- データスキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 層までを想定した DuckDB DDL
  - テーブル初期化（init_schema）、接続取得ユーティリティ

- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日からの差分 or 初回は指定開始日）
  - backfill による直近再取得（API の後出し修正を吸収）
  - 市場カレンダー先読み
  - 品質チェックとの連携（欠損・重複・スパイク・日付不整合）

- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定・前後営業日検索・期間内営業日リスト取得
  - 夜間バッチでのカレンダー差分更新ジョブ

- 品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、将来日付/非営業日データ検出
  - QualityIssue 型で詳細を返却。重大度（error/warning）区分あり

- 監査ログ（kabusys.data.audit）
  - シグナル → 発注要求 → 約定 へとつながるトレーサビリティ用テーブル群
  - order_request_id を冪等キーとして二重発注防止
  - UTC 固定、トランザクション対応で初期化可能

---

## 必要条件 / 推奨環境

- Python 3.10 以上（PEP 604 の | 型注釈などを使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml

実際のプロジェクトでは pyproject.toml / requirements.txt に依存関係を明記してください。

---

## セットアップ手順（例）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトで requirements/pyproject があればそれを利用）

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成します（.env.example を参考に）。
   - 自動読み込みはデフォルトで有効。テスト等で無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   代表的な環境変数:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
   - SLACK_BOT_TOKEN (必須)
   - SLACK_CHANNEL_ID (必須)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - KABUSYS_ENV (development|paper_trading|live, デフォルト: development)
   - LOG_LEVEL (DEBUG|INFO|... , デフォルト: INFO)

   簡単な .env の例:
   ```
   JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
   KABU_API_PASSWORD="your_kabu_api_password"
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C01234567"
   DUCKDB_PATH="data/kabusys.duckdb"
   ```

---

## 使い方（主要な API / ワークフロー例）

※本ライブラリはライブラリ層です。運用時はこれらをラッパーするスクリプトやジョブスケジューラ（cron / Airflow 等）を用いて自動化してください。

1. スキーマ初期化（DuckDB）
   ```python
   from kabusys.data import schema
   from kabusys.config import settings

   conn = schema.init_schema(settings.duckdb_path)
   ```

2. 日次 ETL を実行
   ```python
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)  # 省略時は今日が対象日
   print(result.to_dict())
   ```

3. 市場カレンダーの夜間バッチ更新
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   updated = calendar_update_job(conn)
   print(f"saved calendar records: {updated}")
   ```

4. ニュース収集ジョブ
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   # known_codes: 銘柄抽出で使用する有効コードセット（例: 上場銘柄4桁リスト）
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set(["7203","6758"]))
   print(results)  # {source_name: 新規保存件数}
   ```

5. 監査ログ用スキーマ初期化（必要に応じて）
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn, transactional=True)
   ```

6. 品質チェックだけ実行
   ```python
   from kabusys.data.quality import run_all_checks
   issues = run_all_checks(conn)
   for i in issues:
       print(i)
   ```

注意点:
- jquants_client は内部でトークンを自動リフレッシュします。テストや明示的制御が必要な場合は id_token を引数で注入できます。
- news_collector のネットワーク呼び出しは `_urlopen` をモックすることでテスト可能です（SSRF 検査ロジックを含むため）。

---

## 使い方の補足（設計上の重要事項）

- 環境変数の自動読み込み
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml の場所）を探索し、`.env` と `.env.local` を自動で読み込みます。
  - OS 環境変数は保護され、`.env.local` の値で上書きできます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

- API レート制御 / 再試行
  - J-Quants API は 120 req/min に制約されています。実装では固定間隔のスロットリングでこれを守ります。
  - HTTP 408/429/5xx やネットワークエラーは指数バックオフで最大 3 回再試行します。429 の Retry-After ヘッダは尊重されます。

- データの冪等性
  - DuckDB への保存は ON CONFLICT（DO UPDATE / DO NOTHING）で実装され、重複挿入や再実行を安全に行えます。

- セキュリティ注意
  - RSS の解析は defusedxml を使用して XML Bomb 等に対策しています。
  - 外部 URL 呼び出しはスキーム検証とプライベートアドレス検出（SSRF 対策）を行います。
  - API トークンや証券パスワードなどは `.env` で管理し、リポジトリにコミットしないでください。

---

## ディレクトリ構成

（パッケージは src/kabusys 配下に配置されています。主要ファイル一覧）

- src/
  - kabusys/
    - __init__.py
    - config.py                     -- 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py           -- J-Quants API クライアント（取得・保存）
      - news_collector.py           -- RSS ニュース収集・保存
      - pipeline.py                 -- ETL パイプライン（差分取得・品質チェック統合）
      - calendar_management.py      -- 市場カレンダー管理・営業日ロジック
      - schema.py                   -- DuckDB スキーマ定義・初期化
      - audit.py                    -- 監査ログ（トレーサビリティ）スキーマ
      - quality.py                  -- データ品質チェック
    - strategy/
      - __init__.py                 -- 戦略関連（プレースホルダ）
    - execution/
      - __init__.py                 -- 発注実行関連（プレースホルダ）
    - monitoring/
      - __init__.py                 -- 監視・モニタリング関連（プレースホルダ）

---

## 開発・テストに関するメモ

- テストしやすい設計を意識しており、以下の点が容易にモック可能です:
  - jquants_client の id_token を外部から注入してテスト可能（401 リフレッシュロジックの分離）
  - news_collector._urlopen を差し替えれば HTTP レスポンスを模擬可能
  - DuckDB の ":memory:" 接続を使えばインメモリでスキーマ作成→検証が可能

- ロギングはモジュールロガーを使用。LOG_LEVEL で制御できます。

---

## 今後の拡張案（参考）

- 実際の発注実行モジュール（kabu API / broker adapter）の追加
- Slack 通知 / モニタリングダッシュボード連携
- Airflow / Prefect 等でのワークフロー化テンプレート
- より充実した CLI（start-etl / collect-news / init-db など）

---

この README はコードベースの公開 API と実装意図に基づいて作成しました。  
追加で README に含めたい運用手順やサンプルジョブ（cron / systemd / docker-compose）などがあれば教えてください。