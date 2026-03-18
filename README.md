# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）のリポジトリ用 README。  
このドキュメントはコードベースから自動作成した概要・セットアップ・使い方を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株のデータパイプライン、特徴量計算、戦略リサーチ、監査ログ、ニュース収集、そして発注周りの構造を提供するライブラリ群です。主に以下の目的を想定しています。

- J-Quants API からの市場データ（OHLCV / 財務 / カレンダー）収集と DuckDB への保存（冪等）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 特徴量（Momentum / Volatility / Value 等）の計算と正規化ユーティリティ
- RSS ベースのニュース収集・前処理・銘柄紐付け
- 監査（signal → order → execution のトレーサビリティ）用スキーマ
- ETL の統合実行（差分更新・バックフィル対応）

設計上、DuckDB を中核のストレージに使用し、外部依存は最小限（例：duckdb, defusedxml）に抑えられています。また、本番口座や発注 API への直接アクセスを行わないモジュール（research / data）が多く、Look-ahead バイアスや安全性を意識した実装がなされています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
  - pipeline: 日次 ETL 実行（差分取得・保存・品質チェック）
  - schema: DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - news_collector: RSS 取得・前処理・DB 保存・銘柄抽出（SSRF 対策・gzip 制限）
  - quality: データ品質チェック群（欠損・スパイク・重複・日付不整合）
  - calendar_management: JPX カレンダー管理 / 営業日判定ユーティリティ
  - audit: 監査ログ（signal / order_request / executions）スキーマと初期化
  - stats, features: 統計・正規化ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB を参照）
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクター要約
- config: 環境変数管理（.env 自動読み込み・必須設定チェック・環境判定）
- execution / strategy / monitoring: 将来の発注・戦略・監視関連のプレースホルダ

---

## 要求環境・依存

- Python >= 3.10（型注釈や union 型記法に依存）
- 必要パッケージ（例）:
  - duckdb
  - defusedxml

pip で最低限インストールする場合の例:
```
pip install duckdb defusedxml
```
プロジェクトとして配布されている場合は requirements.txt / pyproject.toml に従ってください。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install -U pip
   pip install duckdb defusedxml
   # またはプロジェクトルートで
   pip install -e .
   ```
4. 環境変数（.env）を用意
   - 自動ロード: パッケージはプロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` / `.env.local` を自動で読み込みます（無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須環境変数（少なくとも以下は設定が期待されます）:
     - JQUANTS_REFRESH_TOKEN: J-Quants の refresh トークン
     - KABU_API_PASSWORD: kabu API パスワード（発注等で使用）
     - SLACK_BOT_TOKEN: Slack 通知用トークン
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - その他（任意／デフォルトあり）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）

   .env の簡単な例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. DuckDB スキーマ初期化
   Python REPL やスクリプトから:
   ```py
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイルを作成して全テーブルを作る
   conn.close()
   ```
   監査ログ専用 DB を初期化する場合:
   ```py
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/kabusys_audit.duckdb")
   conn.close()
   ```

---

## 使い方（主要ユースケース）

- 日次 ETL 実行（株価・財務・カレンダーの差分取得・品質チェック）
  ```py
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- ニュース収集ジョブ（RSS 取得 → raw_news に保存 → 銘柄紐付け）
  ```py
  from kabusys.data.news_collector import run_news_collection
  import duckdb
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes を渡すと本文から銘柄コード抽出して news_symbols に紐付け
  known_codes = {"7203", "6758", "8830"}
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)  # {source_name: saved_count}
  conn.close()
  ```

- ファクター計算（DuckDB 接続を渡して計算結果を取得）
  ```py
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = get_connection("data/kabusys.duckdb")
  res = calc_momentum(conn, target_date=date(2024, 1, 31))
  # res は [{ "date": ..., "code": "7203", "mom_1m": ..., "ma200_dev": ...}, ...]
  conn.close()
  ```

- 将来リターン・IC 計算例
  ```py
  from kabusys.research import calc_forward_returns, calc_ic, rank
  # calc_forward_returns(conn, date, horizons=[1,5,21]) -> forward records
  # calc_ic(factor_records, forward_records, factor_col, return_col) -> Spearman rho
  ```

- データ品質チェック（個別／まとめ実行）
  ```py
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)  # return list of QualityIssue
  ```

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数管理・Settings クラス
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch/save）
    - news_collector.py            — RSS 取得・前処理・DB 保存
    - schema.py                    — DuckDB スキーマ定義・init_schema
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - quality.py                   — データ品質チェック
    - calendar_management.py       — カレンダー更新・営業日ユーティリティ
    - audit.py                     — 監査ログテーブル（signal / order / execution）
    - stats.py                     — zscore_normalize 等
    - features.py                  — features 公開 API (zscore_normalize)
    - etl.py                       — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py           — Momentum/Volatility/Value ファクター
    - feature_exploration.py       — 将来リターン計算・IC・summary
  - execution/                      — 発注関連（未実装プレースホルダ）
  - strategy/                       — 戦略関連（未実装プレースホルダ）
  - monitoring/                     — 監視・メトリクス（未実装プレースホルダ）

---

## 補足・注意点

- .env 自動ロード: config.py はプロジェクトルート（.git または pyproject.toml）を探索し `.env` / `.env.local` を読み込みます。テスト時などに自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DB 初期化: init_schema は冪等で、既存テーブルは再作成しません。監査スキーマは init_audit_schema / init_audit_db を利用してください。
- セキュリティ: news_collector には SSRF 対策、受信サイズ制限、XML パースの安全化（defusedxml）等の対策があります。
- 本番発注: KabuSys の一部（execution/strategy）はプロジェクト内でプレースホルダがあります。実際に資金を動かす前にペーパー取引環境で十分な検証を行ってください（KABUSYS_ENV=paper_trading）。

---

問題点の報告や改善提案はリポジトリの Issue に記載してください。README の拡張やサンプルスクリプト作成など、必要に応じて追補します。