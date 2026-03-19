# KabuSys

日本株向け自動売買基盤ライブラリ / プロジェクト

このリポジトリは「KabuSys」と名付けられた、日本株を対象としたデータ収集・品質管理・特徴量抽出・戦略研究・発注監査を意識したモジュール群を提供します。DuckDB をデータ層に用い、J‑Quants API や RSS フィードなどからデータを取得して ETL → 前処理 → 研究/戦略へと渡すためのユーティリティを含みます。

主な設計方針
- DuckDB を用いたローカルデータベース中心アーキテクチャ
- ETL / 品質チェックは冪等性（ON CONFLICT）と差分更新を重視
- 研究モジュールは本番取引APIへ依存しない（バックテスト / リサーチ安全）
- ネットワーク処理での安全対策（SSRF、XML Bomb、サイズ制限など）

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート基準）。必要な環境変数を `kabusys.config.settings` 経由で取得。
- データ取得 / 保存（data.jquants_client）
  - J‑Quants API クライアント（ページネーション対応、トークン自動リフレッシュ、レート制限、リトライ）
  - 日足（OHLCV）、四半期財務データ、JPX カレンダー取得
  - DuckDB への冪等保存（raw_* テーブル）
- ETL パイプライン（data.pipeline）
  - 差分更新、バックフィル、品質チェック（data.quality）
  - 日次 ETL エントリポイント `run_daily_etl`
- データスキーマ管理（data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル DDL と初期化 `init_schema`
  - 監査ログ用スキーマ（data.audit）と専用 DB 初期化 `init_audit_db` / `init_audit_schema`
- ニュース収集（data.news_collector）
  - RSS から記事収集、前処理、ID生成、DuckDB への冪等保存、銘柄コード抽出
  - SSRF/サイズ/圧縮/XML に対する安全対策
- 研究用ユーティリティ（research）
  - ファクター計算: momentum / value / volatility（prices_daily / raw_financials 参照）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - 正規化ユーティリティ（zscore_normalize を再エクスポート）
- 統計ユーティリティ（data.stats）
  - Zスコア正規化など（外部依存なし、標準ライブラリのみ）

---

## セットアップ手順

前提:
- Python 3.9+（typing の一部表記に合わせてください）
- ネットワークアクセス（J‑Quants / RSS）

1. リポジトリをクローン / プロジェクトディレクトリへ移動
2. 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 必要パッケージをインストール
   - 必須（最低限）:
     - duckdb
     - defusedxml
   - 例:
     ```bash
     pip install duckdb defusedxml
     ```
   - 実プロダクションでは logging 設定や Slack 連携等に必要な追加パッケージがあるかもしれません。requirements.txt がある場合はそれを利用してください。

4. 環境変数を設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成すると自動で読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化）。
   - 主な環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注系を使う場合）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知を使う場合
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/…（デフォルト INFO）
   - 例 `.env`:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=DEBUG
     ```

5. データベース初期化
   - DuckDB スキーマを作成します:
     ```python
     >>> from kabusys.data.schema import init_schema
     >>> conn = init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ用 DB を初期化する場合:
     ```python
     >>> from kabusys.data.audit import init_audit_db
     >>> audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（主要な例）

以下はライブラリを利用する簡単な例です。各関数はモジュール内に docstring があるため、用途や引数はそちらを参照してください。

- 日次 ETL を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  # DB 初期化（初回のみ）
  conn = init_schema("data/kabusys.duckdb")

  # または既存接続を取得
  # conn = get_connection("data/kabusys.duckdb")

  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- J‑Quants から日足を直接取得して保存する（テスト／デバッグ用）
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print("saved:", saved)
  ```

- ニュース収集ジョブを実行する
  ```python
  from kabusys.data.news_collector import run_news_collection
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  # known_codes は銘柄抽出に使う有効コードセット（省略可）
  known_codes = {"7203", "6758", "6501"}
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- 研究用ファクター計算の例
  ```python
  from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, zscore_normalize
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  t = date(2024, 1, 31)
  momentum = calc_momentum(conn, t)
  forward = calc_forward_returns(conn, t, horizons=[1,5,21])
  # 例: mom_1m と fwd_1d の IC を計算
  ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)

  # Zスコア正規化
  normed = zscore_normalize(momentum, ["mom_1m","mom_3m","mom_6m"])
  ```

- 環境設定を参照する
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)  # 未設定なら例外
  print(settings.duckdb_path)            # Path オブジェクト
  ```

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - 環境変数のパースと settings オブジェクト（自動 .env 読み込み含む）
- data/
  - __init__.py
  - jquants_client.py
    - J‑Quants API クライアント、fetch_*, save_* 関数
  - news_collector.py
    - RSS 取得、前処理、DuckDB 保存、銘柄抽出
  - schema.py
    - DuckDB スキーマ定義 & init_schema / get_connection
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - pipeline.py
    - 差分 ETL（run_daily_etl, run_prices_etl, …）
  - features.py
    - features API（zscore_normalize の再エクスポート）
  - calendar_management.py
    - マーケットカレンダー更新 / 営業日判定 / next/prev_trading_day 等
  - audit.py
    - 監査ログスキーマ & init_audit_db/init_audit_schema
  - etl.py
    - ETLResult 再エクスポート
  - quality.py
    - データ品質チェック（欠損・重複・スパイク・日付不整合）
- research/
  - __init__.py
    - 研究機能のエクスポート（calc_momentum 等）
  - feature_exploration.py
    - 将来リターン計算、IC、統計要約
  - factor_research.py
    - momentum/value/volatility の計算
- strategy/ (未実装のエントリポイント用フォルダ)
- execution/ (発注・実行管理用フォルダ)
- monitoring/ (監視・メトリクス用フォルダ)

---

## 注意点・運用メモ

- 自動環境変数読み込み:
  - `kabusys.config` はプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を自動読み込みします。テスト等で自動読み込みを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB ファイルのデフォルトパス:
  - `DUCKDB_PATH` のデフォルトは `data/kabusys.duckdb`
- ネットワーク・セキュリティ:
  - news_collector は SSRF 対策、XML の安全パース、レスポンスサイズ制限、gzip 解凍後のサイズ検査などを実装しています。外部フィードの取り込みではこれらの制約により一部フィードが無視される場合があります。
- 本番発注:
  - 現状のコードベースはデータ取得 / 研究 / スキーマ管理に重点を置いています。発注系（kabuステーション連携等）を有効にする場合は `KABUS_API_PASSWORD` や `KABU_API_BASE_URL` の設定、追加の実装とリスク管理が必要です。`KABUSYS_ENV` により `is_live` / `is_paper` の切り替えが可能です。
- ロギング:
  - モジュールは適切に logger を生成しています。運用時は Python logging を適切に設定してログ出力を収集してください。
- テスト:
  - ネットワーク呼び出しや DB 書き込みを伴う関数群は依存注入（例: id_token の注入、_urlopen のモック）を想定しているため、ユニットテストでの差し替えが可能です。

---

## 貢献 / 拡張案

- 追加ファクター（PBR、配当利回り等）の実装
- strategy 層の戦略フレームワーク化（シグナル生成 → リスク制御 → 発注）
- 発注エンジン（execution）とブローカ連携の実装、テスト用モックブローカー
- メトリクス・監視（monitoring）モジュールの実装（Prometheus / Slack 通知）
- パッケージ化（pyproject.toml / setup.cfg）と CI/CD（自動 DB マイグレーション、テスト）

---

必要であれば、README に「利用例を含むサンプルスクリプト」「推奨依存関係の一覧（requirements.txt）」または「よくある問題と対処」を追記できます。どの情報を優先して追加しますか？