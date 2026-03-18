# KabuSys

日本株向けの自動売買 / データプラットフォーム向けライブラリ群です。  
DuckDB をデータ層に用い、J-Quants API から市場データ・財務データ・マーケットカレンダーを取得・保存し、特徴量計算や品質チェック、ニュース収集、監査ログなどの基盤機能を提供します。

バージョン: 0.1.0

---

## 目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（基本例）
- 環境変数（.env）
- ディレクトリ構成（主要ファイル）

---

## プロジェクト概要
KabuSys は以下の層で構成された日本株自動売買 / リサーチ基盤ライブラリです。

- Data layer（DuckDB）: 生データ（raw）→ 整形済み（processed）→ 特徴量（feature） → 実行（execution）を想定したスキーマを提供
- ETL パイプライン: J-Quants API から差分取得して DuckDB に冪等保存
- データ品質チェック: 欠損・スパイク・重複・日付不整合を検出
- ニュース収集: RSS 取得、前処理、記事保存、銘柄抽出
- ファクター計算・研究用ユーティリティ: モメンタム・ボラティリティ・バリュー等の計算、将来リターン・IC（Spearman）計算
- 監査ログ（audit）: シグナル→オーダー→約定のトレーサビリティ用テーブル

設計方針の一部:
- DuckDB を使った SQL + Python 実装（外部データフレームライブラリに依存しない）
- API 呼び出しはレート制御・リトライ・トークンリフレッシュ対応
- DB 書き込みは冪等（ON CONFLICT）で実装
- 本番発注等の外部ブローカー接続は別モジュールで扱う想定

---

## 主な機能一覧
- data.schema
  - DuckDB のスキーマ定義と初期化（raw_prices, prices_daily, raw_financials, market_calendar, features, signals, etc.）
  - init_schema(db_path) で初期化
- data.jquants_client
  - J-Quants API からのデータ取得（daily quotes / financial statements / trading calendar）
  - ページネーション対応・レート制御・リトライ・トークン自動リフレッシュ
  - DuckDB への冪等保存用関数（save_daily_quotes, save_financial_statements, save_market_calendar）
- data.pipeline
  - run_daily_etl: 市場カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl 分割ジョブ
- data.quality
  - 欠損（missing_data）、スパイク（spike）、重複（duplicates）、日付不整合（future_date/non_trading_day）検出
- data.news_collector
  - RSS 取得（SSRF・ gzip・レスポンスサイズ上限対策）
  - 前処理（URL除去・空白正規化）、記事ID生成（URL 正規化→SHA-256）、DB 保存（冪等）
  - 銘柄コード抽出（4桁数字、既知銘柄リストでフィルタ）
- research
  - calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を参照）
  - calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize の再エクスポート
- audit
  - 監査用テーブル定義・初期化（signal_events, order_requests, executions 等）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に `|` を使用しているため）
- システムに DuckDB を利用するための Python パッケージが必要

1. リポジトリをクローン
   - git clone ...

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（最低限）
   - pip install duckdb defusedxml
   - 他にログやテスト用途で必要なパッケージがあれば追加でインストールしてください。

   （プロジェクト配布時に requirements.txt / pyproject.toml があればそちらを利用してください。）

4. パッケージのローカルインストール（オプション）
   - pip install -e .

5. DuckDB データベース初期化例
   - Python REPL かスクリプトで:
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")

   監査ログ専用 DB を初期化する場合:
     from kabusys.data import audit
     conn = audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 環境変数（.env）
パッケージは起動時にプロジェクトルートの `.env` / `.env.local` を自動ロードします（OS 環境変数を上書きしない挙動、`.env.local` は上書き可）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API パスワード（発注モジュールで使用）
- KABU_API_BASE_URL: kabu API ベース URL （デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack Bot トークン（監視通知等）
- SLACK_CHANNEL_ID (必須): 通知先チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

.env ファイルの読み込みルール（概略）
- 空行や `#` で始まる行を無視
- export KEY=val 形式に対応
- 値はクォート（シングル/ダブル）をサポート（エスケープあり）
- 行内コメントはクォートがない場合にのみ '#' の直前が空白ならコメントとみなす

---

## 使い方（基本例）

- DuckDB スキーマ初期化
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（J-Quants からの差分取得・品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を渡せます
  print(result.to_dict())

  ETLResult には fetched/saved カウント、quality_issues、errors が格納されます。

- ニュース収集（RSS）
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄抽出に用いる既知銘柄集合（例: {"7203","6758",...}）
  res = run_news_collection(conn, sources=None, known_codes=known_codes)
  print(res)  # {source_name: saved_count, ...}

- ファクター計算 / 研究用関数
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
  from datetime import date
  momentum = calc_momentum(conn, date(2024, 1, 1))
  forward = calc_forward_returns(conn, date(2024, 1, 1), horizons=[1,5,21])
  ic = calc_ic(momentum, forward, "mom_1m", "fwd_1d")

- J-Quants から生データを直接取得して保存したい場合
  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)

注意点:
- API リクエストは内部でレート制御・リトライ・トークンリフレッシュを行います。
- DuckDB に書き込む関数は冪等設計（ON CONFLICT）になっています。
- research / data モジュールは本番発注 API へはアクセスしません（read-only な処理）。

---

## 追加ノート / 運用上のヒント
- KABUSYS_ENV を "live" にすると実行時に本番モード判定が可能です（settings.is_live）。
- ETL の差分取得は DB に格納されている最終日を基に自動算出されます。初回は J-Quants 提供開始日（コード中で定義された _MIN_DATA_DATE）から取得されます。
- ニュース収集は RSS のサイズ上限、gzip 解凍後のサイズチェック、SSRF 対策を備えています。
- 品質チェック（data.quality）は致命的なエラー（error）と警告（warning）を分けて報告します。ETL 呼び出し元で判断してください。
- 監査ログ（audit）を使用すると、シグナル→オーダー→約定のトレーサビリティが確保できます。監査テーブルは UTC タイムスタンプで保存します。

---

## ディレクトリ構成（主要）
（パッケージルート: src/kabusys）

- __init__.py
  - パッケージバージョンとサブモジュールのエクスポート

- config.py
  - 環境変数の読み込み・管理（.env 自動ロード、settings オブジェクト）

- data/
  - __init__.py
  - jquants_client.py       : J-Quants API クライアント + 保存ユーティリティ
  - news_collector.py      : RSS 取得・前処理・保存・銘柄抽出
  - schema.py              : DuckDB スキーマ定義 / init_schema / get_connection
  - pipeline.py            : ETL パイプライン（run_daily_etl など）
  - quality.py             : データ品質チェック（missing/spike/duplicates/date consistency）
  - stats.py               : zscore_normalize 等の統計ユーティリティ
  - features.py            : 特徴量ユーティリティ（再エクスポート）
  - calendar_management.py : market_calendar の管理・更新ロジック
  - audit.py               : 監査ログ（signal_events/order_requests/executions）の定義と初期化
  - etl.py                 : ETLResult の公開（pipeline からの再エクスポート）

- research/
  - __init__.py            : 研究用関数の再エクスポート（calc_momentum 等）
  - factor_research.py     : モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py : 将来リターン計算・IC・統計サマリー

- strategy/
  - (戦略実装用プレースホルダ: 将来的に StrategyModel 等を配置)

- execution/
  - (注文実行 / ブローカー連携用プレースホルダ)

- monitoring/
  - (モニタリング / アラート用プレースホルダ)

---

## ライセンス / 貢献
README に含めるライセンス情報やコントリビューションガイドはリポジトリのルートにある LICENSE / CONTRIBUTING を参照してください（本コードスニペットには含まれていません）。

---

この README はコードベースの主要機能と基本的な利用方法をまとめたものです。実運用や拡張を行う際は、各モジュールの docstring を参照の上、環境変数や ETL スケジュール、監査/バックアップ方針を整備してください。