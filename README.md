# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
DuckDB をデータレイクとして用い、J-Quants API / RSS / kabuステーション 等と連携してデータ収集、品質チェック、特徴量生成、監査ログ管理、研究用ユーティリティを提供します。

---

## 目次
- プロジェクト概要
- 主な機能一覧
- 必要な環境変数
- セットアップ手順
- 使い方（簡単な例）
- ディレクトリ構成（主要モジュールの説明）
- 備考（自動 .env ロード等）

---

## プロジェクト概要
KabuSys は、日本株のデータ収集（J-Quants / RSS）、DuckDB ベースのスキーマ管理、ETL パイプライン、品質チェック、ファクター計算（モメンタム、ボラティリティ、バリュー等）、ニュース収集と銘柄抽出、監査ログ（発注→約定のトレーサビリティ）を統合したライブラリです。  
研究（research）用のユーティリティや戦略（strategy）／発注（execution）レイヤーのプレースホルダも含まれます。

設計方針の要点：
- DuckDB を単一データベースとして利用（Raw / Processed / Feature / Execution 層）
- J-Quants API のレート制御・リトライ・トークンリフレッシュを実装
- データ品質チェックを通じた ETL の安定化
- ニュース収集時の SSRF 対策・XML デコード対策などセキュリティ配慮
- すべての DB 保存は冪等（ON CONFLICT）を意識して実装

---

## 主な機能一覧
- データ取得・保存
  - J-Quants から日足（OHLCV）、財務データ、マーケットカレンダーを取得（data/jquants_client.py）
  - RSS からニュース収集 → raw_news 保存・銘柄紐付け（data/news_collector.py）
- DB スキーマ管理
  - DuckDB のスキーマ定義・初期化（data/schema.py）
  - 監査ログ用スキーマ（発注／約定／監査）を初期化（data/audit.py）
- ETL パイプライン
  - 差分取得・バックフィル・品質チェックを含む日次 ETL（data/pipeline.py）
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合チェック（data/quality.py）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research/factor_research.py）
  - 将来リターン計算・IC（スピアマン）計算・統計サマリー（research/feature_exploration.py）
  - z-score 正規化など汎用統計ユーティリティ（data/stats.py）
- 実運用向けの設計要素
  - 環境変数ベースの設定（config.py）
  - 自動 .env ロード（プロジェクトルートとして .git または pyproject.toml を検出）
  - KABUSYS_ENV により動作モード（development / paper_trading / live）を区別

---

## 必要な環境変数
必須（Settings._require により未設定時はエラー）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API 用パスワード
- SLACK_BOT_TOKEN: Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意（デフォルト値あり）:
- KABUS_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 動作環境 (development / paper_trading / live)、デフォルト development
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

自動 .env 読み込みを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例（.env）:
```
JQUANTS_REFRESH_TOKEN=あなたの_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順
1. Python 環境を用意（推奨: 3.10+）
2. 仮想環境の作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存関係のインストール
   - requirements.txt がプロジェクトにある場合:
     - pip install -r requirements.txt
   - パッケージとして使う場合:
     - pip install -e .
   ※ 本コードは duckdb, defusedxml などを使用します。実際の requirements はプロジェクトに合わせて用意してください。
4. 環境変数の設定
   - .env をプロジェクトルートに置くか、環境に直接設定してください。
   - 自動ロードは .git または pyproject.toml を基準にプロジェクトルートを検出します。
5. DuckDB スキーマ初期化
   - Python インタプリタまたはスクリプトから:
     ```
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```
6. 監査ログスキーマ初期化（必要に応じて）
   - init_schema で初期化した conn を渡して次を実行:
     ```
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)
     ```
   - または専用 DB を作る場合:
     ```
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/kabusys_audit.duckdb")
     conn.close()
     ```

---

## 使い方（簡単な例）

- 日次 ETL を実行する（Python で呼び出し）:
  ```
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- J-Quants から日足を直接取得して保存する:
  ```
  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date.today())
  saved = jq.save_daily_quotes(conn, records)
  print("saved:", saved)
  conn.close()
  ```

- RSS ニュース収集ジョブ:
  ```
  from kabusys.data.news_collector import run_news_collection
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758", ...}  # 有効銘柄コードのセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  conn.close()
  ```

- 研究用: モメンタム計算 + Z スコア正規化 + IC 計算:
  ```
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, zscore_normalize

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2025,1,15)
  factors = calc_momentum(conn, target)
  fwd = calc_forward_returns(conn, target)
  # 正規化例
  factors_norm = zscore_normalize(factors, ["mom_1m", "mom_3m", "mom_6m"])
  ic = calc_ic(factors_norm, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  conn.close()
  ```

環境変数は Settings 経由で取得され、未設定の必須値は ValueError を送出します。

---

## ディレクトリ構成（主要ファイルの説明）
（プロジェクトの Python パッケージは src/kabusys 以下にあります）

- src/kabusys/
  - __init__.py: パッケージのバージョン・エクスポート
  - config.py: 環境変数・設定の読み込みロジック（自動 .env ロード、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py: J-Quants API クライアント（レート制御・リトライ・保存ユーティリティ）
    - news_collector.py: RSS 取得・前処理・raw_news 保存・銘柄抽出・紐付け
    - schema.py: DuckDB スキーマ定義と init_schema / get_connection
    - stats.py: zscore_normalize 等、統計ユーティリティ
    - pipeline.py: 日次 ETL の実装（run_daily_etl 等）
    - features.py: 特徴量ユーティリティ（再エクスポート）
    - calendar_management.py: マーケットカレンダー管理・営業日判定・calendar_update_job
    - audit.py: 監査ログ（signal_events / order_requests / executions）スキーマ初期化
    - etl.py: ETL 結果クラスの再エクスポート
    - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - research/
    - __init__.py: 研究用 API のエクスポート（calc_momentum 等）
    - factor_research.py: モメンタム / ボラティリティ / バリューなどのファクター計算
    - feature_exploration.py: 将来リターン計算・IC 計算・サマリー等
  - strategy/: 戦略レイヤー（初期化ファイル、戦略実装を配置）
  - execution/: 発注／約定関連（プレースホルダ）
  - monitoring/: 監視用モジュール（初期化ファイル）

---

## 備考
- .env 自動読み込み:
  - プロジェクトルートを __file__ の親から探索し、.git または pyproject.toml を見つけると自動で .env を読み込みます。
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます（テスト向け）。
  - 読み込み順: OS 環境変数 > .env.local (override) > .env（override=False なので既存の OS 環境を上書きしません）。
- J-Quants クライアント:
  - 120 req/min の制限に合わせた RateLimiter とリトライ（指数バックオフ、最大3回）を備えています。
  - 401 を受けた場合は refresh token から id_token を自動でリフレッシュして再試行します。
- セキュリティ:
  - RSS 取得は SSRF 対策（リダイレクト先の検査、プライベートIPブロック）、defusedxml による XML の安全パース、レスポンスサイズ制限等を行っています。
- DuckDB の TIMESTAMP / 時刻は audit.init_audit_schema で UTC に固定する処理があります。運用時はタイムゾーンの扱いに注意してください。

---

この README はコードの主要な使い方・構成をまとめたものです。実際の運用スクリプトや CLI、CI/CD の設定、requirements.txt 等はプロジェクトに合わせて整備してください。質問やサンプルスクリプトの追加を希望する場合は、用途（ETL 実行頻度・監視フロー・運用口座の有無）を教えてください。