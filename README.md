# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
DuckDB をデータレイヤに用い、J-Quants など外部データソースからの ETL、ニュース収集、ファクター計算、品質チェック、監査ログ（発注〜約定トレース）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能群を持つモジュール群で構成されています。

- データ取り込み（J-Quants API クライアント、ニュース RSS 収集）
- DuckDB ベースのスキーマ・初期化と ETL パイプライン
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 研究向けユーティリティ（将来リターン計算、IC 計算、統計サマリ）
- 発注・実行・監査レイヤ（スキーマ・監査ログ定義）
- 環境変数／設定管理（.env の自動読み込み、必須設定の検査）

設計方針として、本番 API（発注等）へは直接アクセスしない構成（ETL、研究モジュールは read-only）や、冪等（idempotent）操作、Look-ahead bias 対策（fetched_at の記録）、API レート制御等が組み込まれています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API からの株価・財務・カレンダー取得（ページネーション対応、リトライ、トークン自動更新、レートリミット管理）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- data/news_collector.py
  - RSS 取得・前処理・ID生成（URL 正規化 + SHA-256）・SSRF 対策・raw_news 保存・銘柄抽出
- data/schema.py
  - DuckDB 用スキーマ（Raw / Processed / Feature / Execution 層）定義と init_schema()
- data/pipeline.py
  - 差分 ETL（prices / financials / calendar）と run_daily_etl() による一括実行
- data/quality.py
  - 欠損、スパイク、重複、日付不整合チェック（QualityIssue を返す）
- data/stats.py / data/features.py
  - Z スコア正規化等の統計ユーティリティ
- research/factor_research.py / research/feature_exploration.py
  - モメンタム・ボラティリティ・バリューのファクター計算、将来リターン計算、IC 計算、統計サマリ
- data/audit.py
  - 発注→約定をトレースする監査テーブル定義と初期化ユーティリティ
- config.py
  - .env 自動読み込みロジック（プロジェクトルート検出）と Settings による環境変数ラッパ

---

## セットアップ手順

前提
- Python 3.9+（ソースは型ヒントに union 型等を使用）
- DuckDB が利用可能（pip パッケージ duckdb を推奨）
- ネットワークアクセス（J-Quants API、RSS 取得用）

1. リポジトリをクローン（またはパッケージをコピー）
2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # (Linux/macOS)
   .venv\Scripts\activate     # (Windows)
   ```
3. 必要パッケージのインストール
   - 最低限の外部依存:
     - duckdb
     - defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - （プロジェクトで追加の依存があれば適宜インストールしてください）
4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（詳細は下記）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API 用パスワード（発注周りを使う場合）
     - SLACK_BOT_TOKEN: Slack 通知を使う場合
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意:
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
5. スキーマ初期化
   - Python REPL やスクリプトで DuckDB スキーマを作成:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ":memory:" でインメモリ
     ```
   - 監査ログ専用 DB の初期化:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（簡単な例）

- 日次 ETL を実行する（J-Quants から差分取得→保存→品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())  # ETLResult を返す
  print(result.to_dict())
  ```

- ニュース収集ジョブを実行する
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- ファクター計算（モメンタム）を実行する
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2025, 3, 1))
  # records は list[dict]（date, code, mom_1m, mom_3m, mom_6m, ma200_dev）
  ```

- 将来リターンと IC 計算
  ```python
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

  fwd = calc_forward_returns(conn, target_date=date(2025,3,1), horizons=[1,5,21])
  # factor_records は calc_momentum 等の出力
  ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

- Z スコア正規化
  ```python
  from kabusys.data.stats import zscore_normalize
  normed = zscore_normalize(records, columns=["mom_1m", "mom_3m"])
  ```

---

## 設定（.env 自動読み込みについて）

- config.py はプロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` と `.env.local` を自動で読み込みます。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - テスト等で自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- .env の書式は一般的なもの（コメント行 `#`、export プレフィックス、シングル/ダブルクォートをサポート）です。
- Settings の主なプロパティ:
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live / is_paper / is_dev

例（.env.example）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py

src/kabusys/data/
- __init__.py
- jquants_client.py         — J-Quants API クライアント（fetch / save）
- news_collector.py         — RSS 取得・前処理・保存
- schema.py                 — DuckDB スキーマ定義 / init_schema / get_connection
- pipeline.py               — ETL パイプライン（run_daily_etl 等）
- features.py               — 特徴量ユーティリティ（再エクスポート）
- stats.py                  — 統計ユーティリティ（zscore_normalize）
- calendar_management.py    — マーケットカレンダー管理
- audit.py                  — 監査ログスキーマ & 初期化
- etl.py                    — ETLResult 再エクスポート
- quality.py                — データ品質チェック

src/kabusys/research/
- __init__.py
- factor_research.py        — モメンタム / ボラティリティ / バリュー計算
- feature_exploration.py    — 将来リターン / IC / サマリー

src/kabusys/strategy/
- __init__.py               — ストラテジ関連（空の初期化、拡張ポイント）

src/kabusys/execution/
- __init__.py               — 発注実行レイヤ（拡張ポイント）

src/kabusys/monitoring/
- __init__.py               — モニタリング関連（拡張ポイント）

---

## 注意事項 / 実運用に向けたポイント

- J-Quants API のレート制限（120 req/min）に対応するレートリミッタとリトライ処理が実装されていますが、運用時はさらにバッチ設計やスケジューラの設定を検討してください。
- DuckDB のトランザクション管理やファイルパス周りは init_schema / init_audit_db の挙動を理解した上で使用してください（親ディレクトリ自動作成等）。
- ニュース収集は外部 URL を扱うため SSRF 対策やレスポンスサイズ制限、XML の安全パーシング（defusedxml）等の保護が組み込まれていますが、追加のセキュリティ要件がある場合は適宜強化してください。
- 発注まわり（kabu ステーションの実行）は本コードベースの一部にスキーマや設定があるものの、実際の注文送信ロジックは別途実装・安全検証が必要です（paper/live モードの扱い等）。

---

## 貢献・拡張ポイント

- strategy / execution / monitoring パッケージは拡張ポイントとして空の初期化が用意されています。独自の戦略ロジックやブローカーラッパ、監視ダッシュボードを実装して統合できます。
- research モジュールは標準ライブラリ中心で実装されているため、pandas 等を用いた高速化や追加ファクターの導入が容易です。
- テストや CI、ロギング設定（LOG_LEVEL）を整備することで、運用信頼性を向上できます。

---

もし README に含めたいサンプル .env.example、追加の使用例、あるいは特定の機能（例えば発注フローや Slack 通知）の使い方を詳述したい場合は、その旨を教えてください。必要に応じてサンプルコードやコマンドを追加します。