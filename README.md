# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（モジュール群）。  
データ収集・ETL、特徴量生成、リサーチユーティリティ、監査ログ、ニュース収集などを備え、DuckDB をバックエンドにして運用できる設計になっています。

バージョン: 0.1.0

---

## 特徴 (Features)

- データ取得
  - J-Quants API クライアント（株価日足・財務データ・JPX カレンダー）
  - RSS ベースのニュース収集（RSS 正規化、SSRF対策、記事ID生成）
- データ格納
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - 冪等な保存（ON CONFLICT / INSERT ... DO UPDATE）
  - 監査ログ用スキーマ（信号→発注→約定のトレース）
- ETL パイプライン
  - 差分更新（バックフィル対応）、市場カレンダーの先読み
  - 品質チェック（欠損・重複・スパイク・日付不整合検出）
- リサーチ / 特徴量
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン計算、IC（スピアマンのρ）計算、Z スコア正規化
- セキュリティ / 信頼性配慮
  - API レート制御・リトライ・トークン自動リフレッシュ
  - RSS パースに defusedxml を使用、SSRF 対策、レスポンスサイズ制限
- 環境管理
  - .env 自動読み込み（プロジェクトルートベース）、必須環境変数チェック

---

## 動作要件 (Requirements)

- Python 3.10+
  - （コード中で型ヒントに「X | Y」を使用しているため）
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml
- 標準ライブラリ：urllib, logging, datetime, pathlib, etc.

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# （任意）プロジェクトを editable install する場合:
# pip install -e .
```

---

## 環境変数（.env）について

自動読み込みはプロジェクトルート（.git または pyproject.toml の存在するディレクトリ）から行われます。自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN  (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      (必須) — kabuステーション API パスワード
- SLACK_BOT_TOKEN        (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       (必須) — Slack 送信先チャンネル ID

オプション:
- KABUSYS_ENV            (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL              (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- KABU_API_BASE_URL      — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — 監視用 SQLite パス（デフォルト: data/monitoring.db）

.sample .env（例）
```env
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
4. .env をプロジェクトルートに作成（上の例を参照）
5. DuckDB スキーマを初期化
   - Python REPL / スクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
6. （監査ログ専用 DB を別に用意する場合）
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主な API の例）

- ETL（日次ジョブ）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- J-Quants から株価取得（クライアントの直接利用）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758"}  # 既知の銘柄コードセット
  result = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(result)
  ```

- リサーチ / ファクター計算
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
  conn = init_schema(":memory:")  # もしくは実DB接続
  # calc_momentum/volatility/value は target_date と DuckDB 接続を受け取る
  mom = calc_momentum(conn, target_date=date(2024,1,31))
  vol = calc_volatility(conn, target_date=date(2024,1,31))
  val = calc_value(conn, target_date=date(2024,1,31))
  # 将来リターンとIC計算
  fwd = calc_forward_returns(conn, target_date=date(2024,1,31))
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

- 品質チェック（ETL 後に自動で呼ばれますが手動でも実行可能）
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2024,1,31))
  for i in issues:
      print(i)
  ```

- 環境自動読み込みを無効化
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## 主要モジュール（機能別）

- kabusys.config
  - 環境変数管理、.env 自動ロード、必須変数チェック
- kabusys.data.jquants_client
  - J-Quants API クライアント（取得・保存ユーティリティ）
- kabusys.data.schema / audit
  - DuckDB スキーマ定義・初期化、監査ログ初期化
- kabusys.data.pipeline / etl
  - 差分 ETL（prices / financials / calendar）と run_daily_etl
- kabusys.data.news_collector
  - RSS 取得・正規化・DB 保存・銘柄抽出
- kabusys.data.quality
  - 欠損・重複・スパイク・日付整合性チェック
- kabusys.research
  - factor_research（momentum/volatility/value）と feature_exploration（forward returns / IC / summary）
- kabusys.data.stats
  - zscore_normalize（クロスセクション正規化）

---

## ディレクトリ構成

（主要ファイルのみ抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - features.py
      - calendar_management.py
      - audit.py
      - etl.py
      - quality.py
      - stats.py
    - research/
      - __init__.py
      - feature_exploration.py
      - factor_research.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

---

## トラブルシューティング / 注意点

- Python バージョンは 3.10 以上を推奨（型ヒントの構文を使用）。
- DuckDB: large SQL を使うためローカルファイルへの書き込み権限とディスク容量を確認してください。
- J-Quants API のレート制限（120 req/min）に合わせた実装が入っています。過度な同時リクエストは避けてください。
- RSS 取得では外部 URL のリダイレクト先がプライベートアドレスの場合は拒否されます（SSRF 対策）。
- トークンの自動リフレッシュと再トライは実装されていますが、認証エラーが続く場合は J-Quants 側のトークンやネットワーク設定を確認してください。
- DuckDB の SQL 実行で権限やバージョン差による互換性問題が出る可能性があります（特に外部キーや ON DELETE 制約の取り扱いに注意）。

---

## 貢献 / 拡張案

- 取引実行部分（kabu ステーション接続、注文監視）の実装拡張
- 追加ソースの RSS / ニュースパーサー
- 機械学習モデルのスコアリング統合（ai_scores テーブル活用）
- Prometheus / Slack 連携による監視アラート機能強化

---

必要に応じて README を拡張し、運用手順（cron / Airflow によるスケジューリング）、テスト手順、CI 設定例などを追加できます。どの部分を詳しくしたいか教えてください。