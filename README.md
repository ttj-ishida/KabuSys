# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
J-Quants など外部データソースから市場データ・財務データ・ニュースを収集して DuckDB に蓄積し、特徴量生成・ファクター調査・ETL・監査ログなどを提供します。実際の発注処理やブローカー連携部分はモジュール分離されており、研究・バックテスト・本番運用まで段階的に利用できます。

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を基準）
  - 必須環境変数の検証（例: JQUANTS_REFRESH_TOKEN 等）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化

- データ収集（data.jquants_client）
  - J-Quants API 用クライアント（レートリミット、リトライ、トークン自動リフレッシュ対応）
  - 株価日足、財務データ、JPX カレンダーの取得・DuckDB への冪等保存（ON CONFLICT）

- ETL パイプライン（data.pipeline）
  - 差分取得（最後に取得した日付から必要分のみ取得）
  - バックフィル対応（API の後出し修正を吸収）
  - 市場カレンダー・株価・財務データの一括処理（run_daily_etl）

- データ品質チェック（data.quality）
  - 欠損、主キー重複、スパイク（前日比閾値超）や日付不整合チェック
  - QualityIssue として問題を列挙

- ニュース収集（data.news_collector）
  - RSS フィードの安全な取得（SSRF・XML Bomb 対策、gzip 対応）
  - 記事正規化、トラッキングパラメータ除去、記事ID（SHA-256 先頭32文字）
  - raw_news / news_symbols への冪等保存

- DuckDB スキーマ管理（data.schema）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化
  - インデックス、監査テーブル（signal_events / order_requests / executions）定義

- 研究用ユーティリティ（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（スピアマン）計算、Zスコア正規化
  - 外部ライブラリに依存しない純 Python 実装（標準ライブラリ + duckdb）

- 監査ログ（data.audit）
  - シグナル→発注→約定に至るトレーサビリティを担保する監査スキーマ
  - UTC タイムゾーン固定の設計、冪等キーなど運用向け設計

---

## 必要な環境（概要）

- Python 3.9+
- 必須ライブラリ（例）
  - duckdb
  - defusedxml

（プロジェクト配布時に pyproject.toml / requirements.txt を参照し、実際の依存をインストールしてください）

---

## セットアップ手順

1. レポジトリをクローン / コードを配置

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ配布がある場合は pip install -e . など）

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと、自動でロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須変数（例）
     - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
     - KABU_API_PASSWORD=<kabu_api_password>
     - SLACK_BOT_TOKEN=<slack_bot_token>
     - SLACK_CHANNEL_ID=<slack_channel_id>
   - 推奨（任意）
     - DUCKDB_PATH=data/kabusys.duckdb  (デフォルト)
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
     - LOG_LEVEL=INFO|DEBUG|...  (デフォルト: INFO)

   例 .env（参考）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=xxxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトで実行：
     ```
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)
     ```
   - 監査用 DB を分けたい場合：
     ```
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（主要な操作例）

- 日次 ETL の実行（市場カレンダー・株価・財務・品質チェック）
  ```
  from kabusys.config import settings
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)  # 初回: init_schema を呼ぶ
  result = run_daily_etl(conn)  # target_date を渡すことも可能
  print(result.to_dict())
  ```

- 個別 ETL（株価のみ）
  ```
  from kabusys.data.pipeline import run_prices_etl
  fetched, saved = run_prices_etl(conn, target_date=some_date)
  ```

- ニュース収集ジョブ
  ```
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄抽出時に使用する銘柄コード集合（例: {'7203','6758',...}）
  stats = run_news_collection(conn, sources=None, known_codes=known_codes)
  print(stats)  # {source_name: saved_count, ...}
  ```

- 研究用ファクター計算（例: モメンタム）
  ```
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  records = calc_momentum(conn, target_date=some_date)
  # z-score 正規化
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, columns=['mom_1m', 'mom_3m', 'mom_6m', 'ma200_dev'])
  ```

- 将来リターンと IC の計算
  ```
  from kabusys.research import calc_forward_returns, calc_ic
  fwd = calc_forward_returns(conn, target_date=some_date, horizons=[1,5,21])
  ic = calc_ic(factor_records=factor_records, forward_records=fwd, factor_col='mom_1m', return_col='fwd_1d')
  ```

- J-Quants API からのデータ取得（直接呼び出す場合）
  ```
  from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
  rows = fetch_daily_quotes(code='7203', date_from=..., date_to=...)
  ```

---

## 設計上の注意点 / 運用メモ

- 環境変数の自動読み込み
  - 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に `.env` / `.env.local` を読み込みます。テストや特殊な環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化してください。
  - 読み込み順: OS 環境変数 > .env.local > .env（.env.local が上書き）

- J-Quants API
  - レート制限 120 req/min をクライアント側で固定間隔スロットリングにより順守します。
  - リトライ（指数バックオフ）と 401 時のトークン自動リフレッシュに対応。

- DuckDB スキーマ
  - init_schema は冪等的にテーブル/インデックスを作成します。初回のみ実行してください。
  - 監査ログは別 DB に分けることが可能（init_audit_db）。

- ニュース取得の安全対策
  - RSS のリダイレクト先や最終ホストを検査してプライベートアドレスアクセスを防止（SSRF 対策）。
  - defusedxml を利用し XML ベースの攻撃を低減。
  - レスポンスサイズと gzip 解凍後のサイズを制限（メモリ DoS 防止）。

- 研究・分析用関数は本番口座発注 API にアクセスしない設計（prices_daily / raw_financials のみ参照）。安全にローカル分析可能。

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                        # 環境変数・設定管理
    - execution/
      - __init__.py
    - strategy/
      - __init__.py
    - research/
      - __init__.py
      - feature_exploration.py         # 将来リターン計算 / IC / summary
      - factor_research.py             # momentum / volatility / value 計算
    - data/
      - __init__.py
      - jquants_client.py              # J-Quants API クライアント + 保存ユーティリティ
      - news_collector.py              # RSS 収集・正規化・保存
      - schema.py                      # DuckDB スキーマ定義と init_schema
      - stats.py                       # zscore_normalize 等統計ユーティリティ
      - pipeline.py                    # ETL パイプライン（run_daily_etl 等）
      - features.py                    # features の公開インターフェース
      - calendar_management.py         # 市場カレンダー管理ユーティリティ
      - audit.py                       # 監査ログスキーマ初期化
      - etl.py                         # ETLResult の再エクスポート
      - quality.py                     # データ品質チェック
    - monitoring/
      - __init__.py

---

## よくある操作例 / トラブルシュート

- .env が読み込まれない
  - プロジェクトルートが検出できない（.git / pyproject.toml がない）と自動読み込みはスキップされます。手動で環境変数を設定するか、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード挙動を制御してください。

- DuckDB にテーブルが見当たらない
  - 初回は init_schema を必ず呼んでください。get_connection は既存 DB に接続するだけでスキーマを自動生成しません。

- API 呼び出しで 401 が返る
  - jquants_client は 401 を受け取るとリフレッシュトークンで自動的に ID トークンを再取得して 1 回リトライします。リフレッシュに失敗する場合は JQUANTS_REFRESH_TOKEN を再確認してください。

---

この README はコードベースの主要機能・使い方の概要をまとめたものです。実運用／本番接続前には十分な検証と権限・セキュリティ確認を行ってください。さらに詳細な設計仕様や API の挙動はソースコード内の docstring / モジュールコメントを参照してください。