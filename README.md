# KabuSys

日本株自動売買プラットフォーム用ライブラリ（KabuSys）のリポジトリ向け README。  
このドキュメントはコードベースの構成・セットアップ・代表的な使い方をまとめたものです。

注意: この README はソースコード（src/kabusys/*.py）を参照して作成しています。実際に運用する際は環境や秘密情報の扱いに十分ご注意ください。

---

## プロジェクト概要

KabuSys は日本株のデータ収集・品質管理・特徴量生成・リサーチ・監査ログ・ETL パイプライン等を含む自動売買プラットフォーム用モジュール群です。設計方針として以下を重視しています。

- DuckDB を用いたローカルデータレイヤ（Raw / Processed / Feature / Execution）
- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動更新）
- RSS ベースのニュース収集（SSRF 保護、サイズ制限、正規化、銘柄抽出）
- ETL の差分更新・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order → execution のトレース）
- 本番／ペーパー／開発モード切替とログレベル制御

ライブラリは内部的に外部ライブラリ（例: duckdb, defusedxml）を用いますが、研究/統計ユーティリティの多くは標準ライブラリのみで実装されています。

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants からの株価日足、財務（四半期 BS/PL）、JPX カレンダー取得（fetch_*）と DuckDB への冪等保存（save_*）
- ETL パイプライン
  - run_daily_etl を用いた市場カレンダー・株価・財務の差分取得、品質チェック
- データ品質チェック
  - 欠損（OHLC）、スパイク（前日比）、重複（主キー）、日付不整合（未来日付・非営業日のデータ）
- ニュース収集
  - RSS フィード取得、URL 正規化、記事ID生成、raw_news 保存、記事→銘柄の紐付け
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- リサーチ / ファクター計算
  - momentum / volatility / value 等のファクター計算、将来リターン計算、IC（スピアマン）計算、統計サマリー
- 監査ログ（Audit）
  - signal_events / order_requests / executions とインデックス・初期化ユーティリティ
- ユーティリティ
  - Z スコア正規化、統計関数、.env 自動読み込み・設定管理

---

## セットアップ手順

※ 以下は一般的な手順です。実際の運用では仮想環境やシークレット管理を推奨します。

1. Python バージョン
   - Python 3.10 以上を推奨（PEP 604 の型記法などを使用）

2. リポジトリをクローン
   - git clone <repo_url>

3. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

4. 依存パッケージをインストール
   - 必須例:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - パッケージ配布用の requirements.txt / pyproject.toml があればそちらに従ってください。

5. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml を基準）に `.env` または `.env.local` を置くと自動で読み込まれます（ただしテスト時などに KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化可能）。
   - 必須の環境変数（Settings で _require されるもの）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン（必要なとき）
     - SLACK_CHANNEL_ID: Slack 通知先のチャンネル ID
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注などを行う場合）
   - 任意・デフォルト値あり
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
   - .env のパース仕様はシェル形式風でコメントやクォートに対応しています（詳細は src/kabusys/config.py を参照）。

---

## 使い方（代表例）

以下は最小限の Python 例です。実際はロガー設定や例外処理、トークン管理などを行ってください。

- DuckDB スキーマ初期化

  ```python
  from kabusys.data.schema import init_schema

  # ファイル DB を初期化（親ディレクトリがなければ自動作成）
  conn = init_schema("data/kabusys.duckdb")
  ```

- 既存 DB に接続する（初回は init_schema を推奨）

  ```python
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  ```

- 日次 ETL 実行

  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブ実行（既知銘柄セットを指定して銘柄紐付けを行う例）

  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
  results = run_news_collection(conn, sources=None, known_codes=known_codes)
  print(results)  # {source_name: saved_count, ...}
  ```

- J-Quants API から日足データを直接取得（ページネーション対応）

  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes

  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
  print(len(records))
  ```

- リサーチ・ファクター計算の利用例

  ```python
  import duckdb
  from kabusys.research import calc_momentum, calc_forward_returns, zscore_normalize
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2024,1,4))
  forwards = calc_forward_returns(conn, target_date=date(2024,1,4))
  normalized = zscore_normalize(momentum, columns=["mom_1m", "mom_3m", "mom_6m"])
  ```

- カレンダー関連ユーティリティ

  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  print(is_trading_day(conn, date(2024,1,1)))
  print(next_trading_day(conn, date(2024,12,29)))
  ```

---

## .env 自動読み込みの挙動（要点）

- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env` と `.env.local` を自動探索して読み込みます。
- 読み込み順と優先度: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化する場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- .env のパースはシェルライクにコメント・クォート・エスケープを扱います（詳細は src/kabusys/config.py を参照）。

---

## ディレクトリ構成（概要）

リポジトリの主なファイル／パッケージ（src/kabusys 以下）:

- __init__.py
  - パッケージのバージョン等。__all__ に data, strategy, execution, monitoring を公開。

- config.py
  - 環境変数管理、.env 自動読み込み、Settings クラス（設定値のプロパティ化）

- data/
  - jquants_client.py: J-Quants API クライアント（取得・保存ロジック）
  - news_collector.py: RSS 収集、記事正規化、raw_news 保存、銘柄抽出
  - schema.py: DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution）
  - stats.py: 統計ユーティリティ（zscore_normalize 等）
  - pipeline.py: ETL パイプライン（差分更新・品質チェック・日次 ETL）
  - features.py: features インターフェース（zscore 再エクスポート）
  - calendar_management.py: カレンダーの維持・判定・夜間バッチ
  - audit.py: 監査ログテーブル定義・初期化
  - etl.py: ETL インターフェース（ETLResult の再エクスポート）
  - quality.py: 品質チェック（欠損・スパイク・重複・日付不整合）

- research/
  - __init__.py: 主要リサーチ関数を再エクスポート
  - feature_exploration.py: 将来リターン計算、IC、統計サマリー、rank
  - factor_research.py: momentum/volatility/value 等のファクター計算

- strategy/
  - （空のパッケージとして準備。戦略実装を置く想定）

- execution/
  - （空のパッケージとして準備。発注ロジック等を置く想定）

- monitoring/
  - （空または将来の監視機能）

---

## 運用上の注意

- API トークンやパスワードは環境変数やシークレットストアで安全に管理してください。
- DuckDB のファイルパス（DUCKDB_PATH）はバックアップや排他アクセスに注意してください（複数プロセスでの同時書き込み設計は環境依存）。
- run_daily_etl 等は外部 API に依存するため、ネットワークエラーや API レート制限の影響を受けます。ログとリトライ設定を監視してください。
- 実際の発注・約定を行うモジュールを実装する際は sandbox / paper_trading モードで十分なテストを行ってください（Settings.is_live / is_paper）

---

## 参考・開発メモ

- 主要ログ設定は LOG_LEVEL 環境変数で調整可能。
- KABUSYS_ENV = development | paper_trading | live により挙動を切り替えられる設計。
- DuckDB スキーマは冪等で作成され、init_schema() を使うことで簡単に初期化できます。
- ニュース収集は SSRF 対策、gzip サイズチェック、XML パースの安全化（defusedxml）を行っています。

---

この README はコードの主要部分を要約したものです。詳細な実装や追加のユーティリティはソースコード（src/kabusys 以下）を参照してください。質問や追加で README に載せたい項目があれば教えてください。