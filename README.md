# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants などの外部データソースからデータを取得して DuckDB に保管し、特徴量計算やリサーチ、ETL、ニュース収集、監査ログなどの基盤機能を提供します。

この README はリポジトリに含まれる主要モジュール群（data / research / strategy / execution / monitoring 等）の使い方とセットアップ手順、ディレクトリ構成をまとめたものです。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡単なサンプル）
- ディレクトリ構成（主要ファイル一覧）
- 環境変数と .env の読み込み挙動

---

## プロジェクト概要

KabuSys は以下を目的とした Python ベースのライブラリです。

- J-Quants API 等からのデータ取得（株価日足、財務、取引カレンダー）
- DuckDB を用いたデータスキーマ設計と永続化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース（RSS）収集と銘柄紐付け
- ファクター（モメンタム、バリュー、ボラティリティ等）の計算と探索（IC 計算など）
- 監査ログ（シグナル→発注→約定のトレース）
- カレンダー管理（営業日判定、翌営業日/前営業日取得）
- 発注・戦略・監視用の骨組み（strategy / execution / monitoring ディレクトリ）

設計方針として、本ライブラリの多くの部位は「本番口座やブローカー API へ直接アクセスしない」ことを前提にしており、DuckDB と標準ライブラリを中心に実装されています（必要最小限の外部依存のみ）。

---

## 機能一覧（主な機能）

- data/
  - jquants_client: J-Quants API クライアント（ページネーション、レートリミット、トークン自動リフレッシュ、取得→DuckDB 保存用ユーティリティ）
  - schema: DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層の DDL）
  - pipeline: 日次 ETL（市場カレンダー・株価・財務の差分取得、品質チェック）
  - news_collector: RSS 収集、前処理、記事ID生成、raw_news 保存、銘柄抽出・紐付け
  - calendar_management: 営業日判定・next/prev_trading_day 等のユーティリティ、カレンダーの夜間更新ジョブ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ用テーブル定義（signal_events / order_requests / executions）
  - stats: 汎用統計ユーティリティ（z-score 正規化等）
- research/
  - factor_research: モメンタム／ボラティリティ／バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー、rank ユーティリティ
- strategy/, execution/, monitoring/
  - 各層のエントリや将来の拡張向けのパッケージ（骨組み）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に `|` を多用しているため）
- Git リポジトリをクローン済みで、ルートに `pyproject.toml` または `.git` が存在すること（自動 .env ロードのためにプロジェクトルート検出を行います）

1. リポジトリをクローン
   git clone <repository-url>
   cd <repository>

2. 仮想環境の作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell 等)

3. 依存パッケージのインストール
   pip install --upgrade pip
   pip install duckdb defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があれば `pip install -e .` や `pip install -r requirements.txt` を利用してください）

4. 環境変数の設定
   必須環境変数やデフォルト値については次節「環境変数」を参照してください。開発時はプロジェクトルートに `.env`（および必要に応じて `.env.local`）を置くことで自動的に読み込まれます。

5. DuckDB スキーマ初期化
   Python REPL やスクリプトから以下を実行して DB を初期化します（デフォルトファイルは settings.duckdb_path）。
   from kabusys.data.schema import init_schema
   from kabusys.config import settings
   conn = init_schema(settings.duckdb_path)

---

## 環境変数

主な環境変数（ライブラリで参照されるもの）

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。jquants_client.get_id_token のデフォルトに使われます。

- KABU_API_PASSWORD (必須)  
  kabuステーションの API パスワード（execution 関連で使用予定）。

- KABU_API_BASE_URL (任意)  
  kabu API のベース URL。デフォルト: http://localhost:18080/kabusapi

- SLACK_BOT_TOKEN (必須)  
  Slack 通知用の Bot トークン。

- SLACK_CHANNEL_ID (必須)  
  Slack の通知チャネル ID。

- DUCKDB_PATH (任意)  
  DuckDB ファイルパス。デフォルト: data/kabusys.duckdb

- SQLITE_PATH (任意)  
  監視用 SQLite 等のパス（デフォルト: data/monitoring.db）

- KABUSYS_ENV (任意)  
  実行環境: development / paper_trading / live（デフォルト development）

- LOG_LEVEL (任意)  
  ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

読み込み挙動:
- 自動でプロジェクトルートを探索し、`.env` → `.env.local` を読み込みます。  
  優先順位: OS 環境変数 > .env.local > .env  
- 自動ロードを無効化したい場合:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定してください。

サンプル .env（プロジェクトルートに置く）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（簡単なサンプル）

以下はライブラリの主要機能を呼び出す最小サンプルです。実際はログ設定や例外処理を適宜追加してください。

- DuckDB スキーマ初期化
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  conn = init_schema(settings.duckdb_path)

- 日次 ETL の実行（市場カレンダー取得 → 株価・財務取得 → 品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

- 市場カレンダーのユーティリティ
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date
  print(is_trading_day(conn, date.today()))
  print(next_trading_day(conn, date(2026, 1, 1)))

- RSS ニュース収集
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)

- J-Quants からの取得・保存（日足の差分を手動で取得する場合）
  from kabusys.data import jquants_client as jq
  from datetime import date
  records = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,31))
  saved = jq.save_daily_quotes(conn, records)

- ファクター計算・リサーチ
  from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, factor_summary
  from datetime import date
  momentum = calc_momentum(conn, date(2025, 1, 31))
  forwards = calc_forward_returns(conn, date(2025, 1, 31))
  ic = calc_ic(momentum, forwards, factor_col="mom_1m", return_col="fwd_1d")
  summary = factor_summary(momentum, ["mom_1m", "mom_3m", "ma200_dev"])

- 統計ユーティリティ（Zスコア正規化）
  from kabusys.data.stats import zscore_normalize
  normed = zscore_normalize(momentum, ["mom_1m", "ma200_dev"])

---

## 主要な API（短い説明）

- data.schema.init_schema(db_path)  
  DuckDB スキーマを初期化して接続を返す（冪等）。

- data.jquants_client.fetch_daily_quotes(...) / save_daily_quotes(conn, records)  
  J-Quants から日足を取得し raw_prices に保存。

- data.pipeline.run_daily_etl(conn, ...)  
  日次 ETL を実行し ETLResult を返す。

- data.news_collector.run_news_collection(conn, sources=None, known_codes=None)  
  RSS から記事を収集して raw_news に保存し、銘柄紐付けを行う。

- data.quality.run_all_checks(conn, target_date=None, ...)  
  データ品質チェックの実行（欠損、スパイク、重複、日付不整合）。

- research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank  
  リサーチ用のファクター計算・探索ツール。

---

## ディレクトリ構成（抜粋）

以下はリポジトリ内の主要ファイル / モジュール一覧（この README に合わせて抜粋）です。

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
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

（上記のうち多くのモジュールは DuckDB 接続を受け取り SQL + Python の組合せで処理を行う設計です）

---

## 注意点・設計上のポイント

- DuckDB をメイン DB として利用しており、INSERT はできるだけ冪等にしている（ON CONFLICT 句を利用）ため、再投入による重複リスクが低く抑えられています。
- J-Quants API 呼び出しはレートリミット制御（120 req/min）とリトライ・トークン自動更新の仕組みを備えています。
- news_collector では SSRF 対策、XML の安全パース（defusedxml）、受信サイズ制限、トラッキングパラメータ除去などセキュリティと冪等性に配慮しています。
- カレンダー情報が DB に存在しない場合、土日ベースのフォールバックを用いるため、部分的なデータしかない状態でも一貫した振る舞いをします。
- Python の型注釈は比較的新しい構文（PEP 604）を使っているため Python 3.10 以上を想定しています。

---

何か追加したい内容や、README のフォーマット（例: API リファレンスやより詳細なコード例）を変えたい場合は教えてください。必要に応じて使用例のコードブロックや CI / テスト手順、デプロイ手順なども追記します。