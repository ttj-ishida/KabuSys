# KabuSys

KabuSys は日本株のデータ収集・品質管理・特徴量生成・研究用ユーティリティを備えた自動売買基盤のライブラリ群です。J-Quants API を用いた市場データ取得（差分 ETL）、RSS ベースのニュース収集、DuckDB ベースのスキーマ定義、特徴量計算・リサーチ用ユーティリティ、データ品質チェック、監査ログスキーマなどを提供します。

主な設計方針は以下の通りです。
- DuckDB を中心にしてデータ永続化を行う（冪等性を考慮した保存処理）。
- J-Quants API のレート制限やリトライ、トークン自動リフレッシュに対応。
- 本番発注 API には依存せず、データ処理・研究機能のみでも利用可能。
- 標準ライブラリ優先で、外部依存は最小限（duckdb, defusedxml 等）。

## 機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - 差分 ETL（backfill 対応、カレンダー先読み）
  - DuckDB への冪等保存（ON CONFLICT / DO UPDATE）
- スキーマ管理
  - Raw / Processed / Feature / Execution 層を含む DuckDB スキーマ定義と初期化
  - 監査ログ（signal / order_request / executions）スキーマ
- ニュース収集
  - RSS フィード取得（SSRF 対策、gzip サイズチェック、XML パースの安全化）
  - 記事正規化、記事ID生成（URL 正規化 + SHA256）
  - raw_news テーブルへの冪等保存および銘柄紐付け
- データ品質チェック
  - 欠損検出・主キー重複・日付不整合・スパイク検出
  - 問題は QualityIssue オブジェクトとして集約
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 参照）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - Zスコア正規化ユーティリティ
- カレンダー管理
  - JPX カレンダーを元にした営業日判定・前後営業日探索・更新ジョブ
- その他
  - レートリミッタ、HTTP リトライ、トークンキャッシュ等の実装

---

## 要求環境

- Python 3.10 以上（型注釈に PEP 604 の 'X | Y' 形式を使用）
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml

（プロジェクト内で標準ライブラリから多くを実装しているため依存は最小限です。実行する機能に応じて他パッケージが必要になる可能性があります。）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. Python 仮想環境を作成して有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. 必要パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```
   ※プロジェクトに pyproject.toml / requirements.txt があればそれを使ってインストールしてください:
   ```
   pip install -e .
   # または
   pip install -r requirements.txt
   ```

4. 環境変数を設定（.env の作成）
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数例（.env）:
     ```
     # J-Quants
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

     # kabuステーション API
     KABU_API_PASSWORD=your_kabu_password
     # (オプション) カスタムベースURL
     KABU_API_BASE_URL=http://localhost:18080/kabusapi

     # Slack (通知等に使用)
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567

     # DB パス
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

     # 実行環境
     KABUSYS_ENV=development  # development | paper_trading | live
     LOG_LEVEL=INFO
     ```
   - 必須の変数は Settings を通して参照時にチェックされ、未設定の場合は例外が発生します。

5. DuckDB スキーマ初期化（例）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```
   監査用 DB を別途作る場合:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主要なユースケース）

以下は最小限の利用例です。実際にはログ設定や例外処理等を適宜追加してください。

- 日次 ETL 実行（市場カレンダー・株価・財務データ取得 + 品質チェック）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 市場カレンダー更新ジョブ（夜間バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- RSS ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # あらかじめ known_codes を用意しておくと銘柄紐付けが可能
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- 監査 DB の初期化（別 DB として）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- 研究用関数（ファクター計算・IC 計算など）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

  conn = duckdb.connect("data/kabusys.duckdb")  # スキーマは事前に初期化しておく
  target = date(2024, 1, 4)

  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  fwd = calc_forward_returns(conn, target)

  # IC（例: mom_1m と 1日先リターン）
  ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
  summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])
  print("IC:", ic)
  print("Summary:", summary)
  ```

- ETL の差分取得を利用した個別ジョブ呼び出し
  - run_prices_etl / run_financials_etl / run_calendar_etl など、細かく呼び出せます。

---

## 主要モジュール（概要）

- kabusys.config
  - 環境変数の自動ロード（.env / .env.local）と Settings クラス
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能

- kabusys.data
  - jquants_client.py : J-Quants API クライアント（取得・保存関数）
  - schema.py         : DuckDB スキーマ定義 / init_schema
  - pipeline.py       : 日次 ETL 実装（差分取得 / 品質チェック）
  - news_collector.py : RSS 収集・正規化・DB 保存
  - calendar_management.py : 営業日判定・カレンダー更新
  - audit.py          : 監査ログスキーマ初期化
  - quality.py        : データ品質チェック
  - stats.py          : zscore_normalize 等の統計ユーティリティ

- kabusys.research
  - factor_research.py   : momentum / volatility / value 計算
  - feature_exploration.py : 将来リターン・IC・サマリ等

- kabusys.strategy / kabusys.execution / kabusys.monitoring
  - パッケージエントリはあるが、プロジェクトの拡張ポイントとして構成されています。

---

## ディレクトリ構成（主要ファイル）

プロジェクトのソースは `src/kabusys` 配下にあります。主なツリーは以下のような構成です（抜粋）:

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
      - calendar_management.py
      - audit.py
      - etl.py
      - features.py
      - stats.py
      - quality.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      (戦略関連の実装を追加する場所)
    - execution/
      - __init__.py
      (発注/ブローカー連携の実装を追加する場所)
    - monitoring/
      - __init__.py

---

## 実運用上の注意 / Tips

- 環境変数は Settings により必須チェックされるため、API キー等は必ず設定してください（JQUANTS_REFRESH_TOKEN、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、KABU_API_PASSWORD など）。
- J-Quants API のレート制限（120 req/min）や 401/429/5xx に対するリトライが組み込まれていますが、大量データを取得する場合はレートやトークンの管理に注意してください。
- DuckDB のファイルはデフォルトで `data/kabusys.duckdb` に置かれます。バックアップやアクセス制御は運用で検討してください。
- news_collector は外部ネットワークアクセス（RSS）を行います。SSRF 対策やレスポンスサイズ制限が入っていますが、運用環境のネットワークポリシーと合わせて利用してください。
- audit スキーマは監査ログ用に設計されています。トランザクション、タイムゾーン（UTC）や FK 制約の扱いに注意してください。

---

もし README に追加してほしい内容（例: CI / テスト手順、具体的な .env.example ファイルのテンプレート、API 使用上のベストプラクティス等）があれば教えてください。必要に応じて用途別のチュートリアル（ETL 運用、戦略開発フロー、監査ログ参照方法など）も作成します。