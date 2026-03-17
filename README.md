# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）です。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、DuckDBスキーマ、監査ログ等を含む基盤コンポーネント群を提供します。

## 概要
- J-Quants API から株価（日足）・財務情報・市場カレンダーを取得して DuckDB に保存する ETL パイプラインを提供します。
- RSS からニュースを収集して記事を正規化・保存し、銘柄コード抽出と紐付けを行います（ニュース収集モジュールは SSRF や XML 攻撃対策を実装）。
- データ品質チェック（欠損、スパイク、重複、日付整合性）を行い、問題を検出してレポート化します。
- 監査ログ用スキーマ（シグナル → 発注 → 約定のトレーサビリティ）を提供します。
- レート制御・リトライ・トークン自動リフレッシュ等、外部 API に対する堅牢な実装を含みます。

## 主な機能一覧
- J-Quants クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務データ取得（四半期 BS/PL、ページネーション対応）
  - 市場カレンダー取得（祝日・半日・SQ）
  - レートリミッタ（120 req/min）・再試行（指数バックオフ）・401時トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT を利用）
- ニュース収集（RSS）
  - URL 正規化（トラッキングパラメータ除去）→ SHA-256 ハッシュで記事ID生成（先頭32文字）
  - XML の安全パース（defusedxml）
  - SSRF 対策（スキーム検査・プライベートIP拒否・リダイレクト検査）
  - レスポンスサイズ上限、gzip 解凍チェック
  - DuckDB への冪等保存（INSERT ... RETURNING / トランザクション）
  - テキスト前処理（URL 除去・空白正規化）と銘柄コード抽出
- ETL パイプライン
  - 差分更新（DB の最終取得日に基づく差分取得）
  - バックフィルによる後出し修正吸収
  - 市場カレンダーの先読み取得
  - 品質チェックの実行（複数チェックをまとめて実行）
- データ品質チェック
  - 欠損データ検出、スパイク検出（前日比閾値）、重複検出、日付不整合検出
  - 問題は QualityIssue オブジェクト群として返却
- スキーマ（DuckDB）
  - Raw / Processed / Feature / Execution / Audit の各レイヤに対応するテーブル群・インデックス
  - init_schema による初期化（冪等）

## 要求環境
- Python 3.10 以上（型ヒントで | 演算子を利用）
- 主な依存パッケージ:
  - duckdb
  - defusedxml
- 標準ライブラリで urllib 等を使用

（実際の requirements.txt があればそれに従ってください）

## セットアップ手順

1. リポジトリをクローン、またはパッケージを配置
   - この README はパッケージが `src/kabusys` にある想定です。

2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ化されていれば pip install -e .）

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` / `.env.local` を配置できます。
   - 自動ロード順序（優先度高 → 低）:
     - OS 環境変数
     - .env.local（.env を上書き）
     - .env（未上書きのキーのみ設定）
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルト:
     - KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
     - LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL) — デフォルト: INFO
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

5. データベーススキーマ初期化
   - Python から DuckDB スキーマを作成します:
     - 例:
       - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   - 監査ログスキーマを追加する場合:
     - python -c "import duckdb; from kabusys.data.schema import init_schema; conn=init_schema('data/kabusys.duckdb'); from kabusys.data.audit import init_audit_schema; init_audit_schema(conn)"

## 使い方（簡単な例）
- 日次ETL を実行する（J-Quants からデータ取得→保存→品質チェック）
  - 例（REPL / ワンライナー）:
    - python -c "from kabusys.data.schema import init_schema; from kabusys.data.pipeline import run_daily_etl; conn = init_schema('data/kabusys.duckdb'); res = run_daily_etl(conn); print(res.to_dict())"
  - パラメータ例:
    - run_daily_etl(conn, target_date=date(2024,1,1), id_token=None, run_quality_checks=True, spike_threshold=0.5)

- ニュース収集（RSS）を実行して保存する
  - 例:
    - python -c "from kabusys.data.schema import init_schema; from kabusys.data.news_collector import run_news_collection; conn = init_schema('data/kabusys.duckdb'); print(run_news_collection(conn))"
  - 既定の RSS ソースは `DEFAULT_RSS_SOURCES` に定義されています（例: Yahoo Finance のカテゴリ RSS）。

- 市場カレンダー夜間更新ジョブ
  - calendar_update_job を使ってカレンダーを差分更新できます:
    - python -c "from kabusys.data.schema import init_schema; from kabusys.data.calendar_management import calendar_update_job; conn=init_schema('data/kabusys.duckdb'); print(calendar_update_job(conn))"

- 品質チェック単体実行
  - from kabusys.data.quality import run_all_checks
  - run_all_checks(conn, target_date=date.today())

- J-Quants の ID トークンを取得（手動）
  - from kabusys.data.jquants_client import get_id_token
  - get_id_token()  # settings.jquants_refresh_token を使用

注: 実運用での発注・Kabu API との連携部分は本リポジトリの execution / strategy モジュールに拡張して利用してください（現在はパッケージ骨格が用意されています）。

## 設定と動作に関する注意点
- 自動 .env ロード
  - パッケージは起動時にプロジェクトルートを .git または pyproject.toml で探索し、.env / .env.local を自動的に読み込みます（OS 環境変数を保護）。無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
- 環境（KABUSYS_ENV）
  - development / paper_trading / live のいずれかを指定。live にすると実発注等の挙動を変える実装を想定しています。
- ロギング
  - LOG_LEVEL でログレベルを指定します（デフォルト INFO）。
- J-Quants 呼び出し
  - レート制御（120 req/min）と再試行ロジック、401 時の自動トークンリフレッシュが組み込まれています。
- ニュース収集の安全性
  - XML を defusedxml でパース、リダイレクト先検査やプライベートIP 拒否、レスポンスサイズ制限等により安全性を高めています。

## ディレクトリ構成（概要）
（主要ファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数・設定管理 (.env 自動ロード等)
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py               — RSS ニュース収集・保存・銘柄紐付け
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py          — 市場カレンダー管理・夜間更新
    - schema.py                       — DuckDB スキーマ定義 / init_schema
    - audit.py                        — 監査ログ（信頼トレーサビリティ）スキーマ
    - quality.py                      — データ品質チェック
  - strategy/
    - __init__.py                      — 戦略関連の拡張ポイント（骨格）
  - execution/
    - __init__.py                      — 発注 / 実行関連の拡張ポイント（骨格）
  - monitoring/
    - __init__.py                      — 監視関連の拡張ポイント（骨格）

## 開発 / 貢献
- ユニットテストやモックを用いて外部API呼び出し（_urlopen、get_id_token 等）を差し替えやすい設計になっています。
- PR の際は、.env.example を付ける、必要な依存を requirements-dev.txt や pyproject.toml に記載してください。

## ライセンス / 免責
- この README はコードベースの説明であり、実際の運用前に十分なテストと監査を行ってください。
- 実際の発注機能を有効にする際はリスク管理・二重発注防止・監視を必ず実装してください。

---

問題や追加したいドキュメント（例: .env.example、運用手順、監視設定、CI/CD 用の起動スクリプトなど）があれば指示ください。README を用途に合わせて拡張します。