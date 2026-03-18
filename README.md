# KabuSys

KabuSys は日本株向けの自動売買プラットフォームの基盤ライブラリです。  
データ収集（J-Quants API、RSS ニュース）、DuckDB スキーマ管理、ETL パイプライン、データ品質チェック、ファクター計算（リサーチ用）、監査ログなど、戦略開発と運用に必要な共通処理を提供します。

バージョン: 0.1.0

---

## 主要な特徴（機能一覧）

- 環境変数/設定管理
  - プロジェクトルートの `.env` / `.env.local` を自動読み込み（必要に応じて無効化可）
  - 必須設定の検証（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）
- データ取得（J-Quants API クライアント）
  - 日次株価（OHLCV）、財務情報、マーケットカレンダーの取得
  - レートリミット制御、リトライ・トークン自動リフレッシュ、ページネーション対応
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ニュース収集
  - RSS フィードから記事収集、正規化、重複回避、記事→銘柄紐付け
  - SSRF 対策、XML インジェクション対策（defusedxml）、応答サイズ制限
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution / Audit 層を含むスキーマ
  - インデックス定義や監査ログ用テーブルの初期化ユーティリティ
- ETL パイプライン
  - 差分更新（最終取得日からの差分取得 + バックフィル）
  - 市場カレンダー、株価、財務データを順次取得・保存
  - 品質チェックの実行（欠損、重複、スパイク、日付不整合）
  - ETL 実行結果を ETLResult オブジェクトで返却
- データ品質チェック
  - 欠損データ、スパイク、重複、未来日付・非営業日データの検出
  - 検出結果は QualityIssue のリストで返却
- リサーチ / ファクター計算
  - Momentum, Value, Volatility 等の定量ファクター計算
  - 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ（クロスセクション）
- 監査ログ（Audit）
  - シグナル→発注→約定までのトレーサビリティを記録するテーブル群と初期化関数

---

## セットアップ手順

前提:
- Python 3.9+（typing |future annotations を使用しているため 3.9+ を想定）
- DuckDB を使用（ローカルファイルベースまたはインメモリ）

1. リポジトリをクローン／取得  
   （この README はソースツリーを前提とした手順を示します）

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存ライブラリをインストール  
   必要なパッケージ（最低限）:
   - duckdb
   - defusedxml
   - （標準ライブラリと urllib 等が使用されます）

   例:
   ```
   pip install duckdb defusedxml
   ```

   プロジェクトがパッケージ化されている場合は開発インストール:
   ```
   pip install -e .
   ```

4. 環境変数（.env）を準備  
   プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（CWD に依存せず package ファイル位置からプロジェクトルートを探索します）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（省略可, デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 環境 (development | paper_trading | live)
   - LOG_LEVEL: ログレベル（DEBUG, INFO, ...）

5. DuckDB スキーマの初期化（例）
   Python REPL やスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   # conn は DuckDB 接続オブジェクト
   ```

   監査ログ専用 DB を初期化するには:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主な API と例）

以下は代表的な利用例です。実運用ではエラーハンドリングやログ設定、ジョブスケジューラと組み合わせてください。

- 日次 ETL 実行（市場カレンダー / 株価 / 財務 / 品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  # DB 初期化済みなら get_connection、未なら init_schema
  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- J-Quants から日次株価をフェッチして保存（個別）
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print(f"saved: {saved}")
  ```

- RSS ニュース収集ジョブ実行
  ```python
  from kabusys.data.news_collector import run_news_collection
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  # known_codes は有効な銘柄コードセット（例: 全上場銘柄の4桁コード）
  known_codes = {"7203", "6758", "9433"}
  res = run_news_collection(conn, known_codes=known_codes)
  print(res)
  ```

- ファクター計算 / リサーチ利用例
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2024, 1, 31)

  momentum = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  value = calc_value(conn, target)
  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

  # 例: mom_1m と fwd_1d の IC
  ic = calc_ic(momentum, fwd, "mom_1m", "fwd_1d")
  print("IC:", ic)

  # 統計サマリー
  summary = factor_summary(momentum, ["mom_1m", "mom_3m", "ma200_dev"])
  print(summary)
  ```

- Zスコア正規化
  ```python
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m"])
  ```

---

## 注意点 / 運用上の留意事項

- J-Quants API のレートリミット（120 req/min）を守る設計になっています。大量取得を自動化する際は注意してください。
- ETL は「差分更新」式で動作します。初回ロードや大きなバックフィルは時間がかかる可能性があります。
- DuckDB のバージョンや機能（ON DELETE CASCADE などの制限）に依存する実装箇所があります。使用する DuckDB バージョンの互換性に注意してください。
- ニュース収集では SSRF や XML の脆弱性対策（defusedxml, ホスト検証, サイズ制限等）を施していますが、外部フィードの変化に伴う例外処理は必要に応じて拡張してください。
- 自動環境読み込みはプロジェクトルートを .git または pyproject.toml から探索します。CI やテストで自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                      — 環境変数 / Settings 管理
- data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント（取得・保存）
  - news_collector.py            — RSS ニュース収集・保存・銘柄抽出
  - schema.py                    — DuckDB スキーマ定義・初期化
  - stats.py                     — 統計ユーティリティ（zscore_normalize 等）
  - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
  - features.py                  — 特徴量インターフェース（再エクスポート）
  - calendar_management.py       — 市場カレンダー管理ユーティリティ
  - audit.py                     — 監査ログ（Signal/Order/Execution）初期化
  - etl.py                       — ETL ユーティリティの公開インターフェース
  - quality.py                   — データ品質チェック
- research/
  - __init__.py
  - factor_research.py           — Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py       — 将来リターン・IC・サマリー等
- strategy/
  - __init__.py
- execution/
  - __init__.py
- monitoring/
  - __init__.py

（上記は現状の主要なモジュール構成です。将来的に strategy や execution、monitoring パッケージに具体実装を追加してください。）

---

## 追加情報 / 開発者向けメモ

- ロギング: Settings.log_level でログレベルを制御できます。環境変数 `LOG_LEVEL` を設定してください。
- 環境（開発 / ペーパー / 本番）: `KABUSYS_ENV` に `development` / `paper_trading` / `live` のいずれかを設定すると、settings.is_dev / is_paper / is_live が利用可能です。
- テスト容易性: jquants_client などでトークンを引数注入できる設計（id_token 引数）になっており、モック注入による単体テストが容易です。
- セキュリティ: ニュース収集モジュールは SSRF・巨大レスポンス・XML インジェクション対策を実装していますが、外部入力を扱う場合は常に追加の監査・制限を行ってください。

---

もし README にサンプルの .env.example、requirements.txt、あるいは CI / デプロイ手順（systemd / cron ジョブ例など）を追加したい場合は、その内容の希望を教えてください。必要に応じて README を拡張して YAML や実運用向けの手順も書きます。