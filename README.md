# KabuSys

日本株向け自動売買プラットフォーム（ライブラリ群）。  
データ収集（J-Quants）、データ基盤（DuckDB スキーマ／ETL）、ニュース収集、研究用ファクター計算、監査ログなどを含むモジュール群を提供します。

主要設計方針の要点
- DuckDB を中心としたローカルデータレイヤ（Raw / Processed / Feature / Execution）
- J-Quants API 経由の株価・財務・カレンダー取得（レート制御・リトライ・トークン自動更新）
- RSS ベースのニュース収集（SSRF 保護、トラッキングパラメータ除去、冪等保存）
- Research 用のファクター計算（モメンタム・バリュー・ボラティリティ）と IC / サマリー
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order → execution のトレースを保証）

---

## 機能一覧（主なモジュール）
- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - 必須設定取得と環境（development/paper_trading/live）判定
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存関数、ページネーション、レート制御、リトライ）
  - news_collector: RSS 取得・前処理・DuckDB への冪等保存・銘柄抽出
  - schema: DuckDB のスキーマ定義と初期化（Raw/Processed/Feature/Execution）
  - pipeline / etl: 差分 ETL と日次パイプライン（品質チェック統合）
  - quality: データ品質チェック群（欠損・重複・スパイク・日付不整合）
  - calendar_management: 市場カレンダー管理 / 営業日ユーティリティ
  - audit: 監査ログ（signal / order_request / executions）用スキーマ初期化
  - stats / features: Z スコア正規化などの統計ユーティリティ
- kabusys.research
  - factor_research: モメンタム/バリュー/ボラティリティの計算
  - feature_exploration: 将来リターン計算・IC（Spearman）・ファクターサマリー
- strategy, execution, monitoring
  - モジュール初期化用パッケージが用意されています（実装はプロジェクト固有で拡張）

---

## 要件
- Python 3.10 以上（型アノテーションに | を利用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリを広く利用（urllib / datetime / math / logging 等）

インストール例:
```
python -m pip install duckdb defusedxml
```

（プロジェクト固有の追加依存がある場合は pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置

2. Python 環境を準備・依存をインストール
   - Python 3.10+
   - pip install duckdb defusedxml など

3. 環境変数（.env）を用意  
   プロジェクトルート（.git か pyproject.toml のあるディレクトリ）に `.env`（および必要なら `.env.local`）を配置すると自動読み込みされます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例（.env.example）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで初期化します。

   例:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイルパスの親ディレクトリは自動作成されます
   ```

5. 監査ログ用スキーマ（オプション）
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（主要ユースケース）

- 日次 ETL 実行
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # settings.jquants_refresh_token が必須
  print(result.to_dict())
  ```

  run_daily_etl は次を順に実行します:
  1. 市場カレンダー ETL（先読み）
  2. 株価データ ETL（差分・バックフィル）
  3. 財務データ ETL（差分・バックフィル）
  4. 品質チェック（オプション）

- J-Quants から株価データ取得（単発）
  ```python
  from kabusys.data import jquants_client as jq
  recs = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,10))
  ```

- 取得データを DuckDB に保存（冪等）
  ```python
  saved = jq.save_daily_quotes(conn, recs)
  ```

- ニュース収集ジョブ実行
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  # known_codes: 銘柄抽出に使う有効銘柄コードの集合（例: {"7203", "6758", ...}）
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set_of_codes)
  print(results)  # {source: saved_count, ...}
  ```

- Research（ファクター計算 / IC）
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

  mom = calc_momentum(conn, target_date=date(2024,1,10))
  vol = calc_volatility(conn, target_date=date(2024,1,10))
  val = calc_value(conn, target_date=date(2024,1,10))

  fwd = calc_forward_returns(conn, target_date=date(2024,1,10), horizons=[1,5,21])
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

- Z スコア正規化（data.stats.zscore_normalize）
  ```python
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, columns=["mom_1m", "ma200_dev"])
  ```

---

## 環境変数（主要）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須 for kabu API)
- KABU_API_BASE_URL (オプション): デフォルト http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須 for Slack 通知)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (オプション): デフォルト data/kabusys.duckdb
- SQLITE_PATH (オプション): デフォルト data/monitoring.db
- KABUSYS_ENV: one of development/paper_trading/live (デフォルト development)
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

設定は .env, .env.local, あるいは OS 環境変数で行います。自動読み込みはプロジェクトルートを基準に行われ、.env.local は .env を上書きします。

---

## 開発時の注意点・設計メモ
- J-Quants API はレート制限（120 req/min）を守るため、クライアント側で固定間隔スロットリングとリトライを実装しています。401 を受けた場合はリフレッシュトークンで自動更新します。
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）を基本とし、ETL は差分・バックフィルで後出し訂正に耐える設計です。
- news_collector は SSRF / XML bomb / 大きなレスポンス対策を実装しています（スキーム検証、プライベートホスト拒否、サイズ上限、defusedxml の使用など）。
- Research モジュールは外部ライブラリに依存しない（標準ライブラリで実装）ため軽量に試験できます。
- audit スキーマは UTC を前提とし、監査トレースを UUID 連鎖で確保します。

---

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - etl.py
    - features.py
    - stats.py
    - calendar_management.py
    - audit.py
    - quality.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（上記は本コードベースに含まれているファイル群の抜粋です）

---

## よくある質問 / トラブルシュート
- .env が読み込まれない場合:
  - プロジェクトルートが __file__ の親階層から .git か pyproject.toml を探す方式です。テストなどで自動読み込みを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のテーブルが作成されない:
  - `init_schema(db_path)` を呼んでいるか確認してください。初回はスキーマ初期化が必要です。
- J-Quants の認証エラー:
  - `JQUANTS_REFRESH_TOKEN` の値を確認、また get_id_token の例外やログを精査してください。HTTP 401 は自動でリフレッシュを試みますが、トークンが無効な場合は手動対応が必要です。

---

## ライセンス / 貢献
本ドキュメントはコードベースの構造を説明するための README です。実際のプロジェクトではライセンス・貢献ガイドラインをプロジェクトルートに追加してください。

---

必要であれば、この README を英語版に翻訳したり、セットアップ手順に Docker / GitHub Actions 用の例を追加したりできます。どの追加情報がほしいか教えてください。