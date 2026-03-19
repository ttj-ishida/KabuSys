# KabuSys

日本株向けの自動売買 / データプラットフォーム基盤ライブラリです。  
データ収集（J-Quants）、DuckDB ベースのスキーマ、ETL パイプライン、品質チェック、ニュース収集、特徴量計算、監査ログなどの機能を備えています。

---

## 主要機能（概要）

- J-Quants API クライアント
  - 日足（OHLCV）・財務データ・マーケットカレンダー取得（ページネーション対応）
  - レート制限・リトライ・トークン自動リフレッシュ対応
- データ層（DuckDB）スキーマ定義と初期化
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - インデックス・制約付きの冪等的なテーブル作成
- ETL パイプライン
  - 差分取得（最終取得日からの差分）・バックフィル対応
  - 日次 ETL（カレンダー／株価／財務）と品質チェック統合
- データ品質チェック
  - 欠損、重複、スパイク（急騰・急落）、日付不整合チェック
- ニュース収集
  - RSS からの記事収集・前処理・重複排除・記事→銘柄紐付け（正規化・SSRF 対策・サイズ制限等）
- ファクター / 研究用ユーティリティ
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログ（Audit）
  - シグナル→発注→約定のトレーサビリティを保持する監査用テーブル群

---

## 必要条件（Prerequisites）

- Python 3.10+
- 必要な Python パッケージ（主なもの）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API を使用する場合）
- （オプション）kabuステーション等外部ブローカー API の設定

依存関係はプロジェクトの pyproject.toml / requirements に記載されている想定です。手動で必要なパッケージをインストールする例:

pip install duckdb defusedxml

または、プロジェクトとして配布されていればルートで:

pip install -e .

を実行してください。

---

## 環境変数 / .env

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動で読み込まれます（`kabusys.config`）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主に使用される環境変数（例）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment（development / paper_trading / live。デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

簡単な `.env` 例（プロジェクトルートに設置）:

JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - もし pyproject.toml があるなら: pip install -e .

4. 環境変数を設定（`.env` ファイルをプロジェクトルートに作成）

5. DuckDB スキーマ初期化（次節の使い方参照）

---

## 使い方（簡単なコード例）

以下は Python インタプリタやスクリプト上での簡単な使用例です。

1) DuckDB スキーマ初期化（最初に一度だけ）

from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # or ":memory:" for in-memory
# これで必要な全テーブルとインデックスが作成されます

2) 監査ログ用 DB 初期化（監査専用 DB が必要な場合）

from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")

3) 日次 ETL 実行（J-Quants から差分取得して保存）

from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を与えれば任意日で実行可
print(result.to_dict())

4) ニュース収集ジョブを実行

from kabusys.data.news_collector import run_news_collection
# conn は DuckDB 接続
known_codes = {"7203", "6758", "9432"}  # 例: 有効な銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)

5) 研究/特徴量計算（例: モメンタム）

from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
# conn は DuckDB 接続、target_date は datetime.date
momentum = calc_momentum(conn, target_date)
forward = calc_forward_returns(conn, target_date, horizons=[1,5,21])
ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(momentum, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])

6) J-Quants の生データ取得（デバッグ目的）

from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
quotes = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
fins = fetch_financial_statements(code="7203")

注意:
- J-Quants API を呼ぶ関数は認証トークンを内部キャッシュから自動取得します（settings.jquants_refresh_token が必要）。
- ネットワーク／API エラーは例外やログで通知されます。

---

## 主なモジュール・API 概要

- kabusys.config
  - Settings オブジェクト経由で環境設定を取得（settings.jquants_refresh_token 等）
  - 自動的にプロジェクトルートの .env / .env.local を読み込む

- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar

- kabusys.data.schema
  - init_schema(db_path) / get_connection(db_path)

- kabusys.data.pipeline
  - run_daily_etl(...)（日次 ETL のメイン）

- kabusys.data.news_collector
  - fetch_rss(url, source), save_raw_news, run_news_collection

- kabusys.data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks

- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize

- kabusys.data.audit
  - init_audit_schema, init_audit_db（監査ログの初期化）

---

## ディレクトリ構成（主なファイル）

（プロジェクトルートの `src/` 配下にパッケージがあります）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - stats.py
      - pipeline.py
      - etl.py
      - features.py
      - calendar_management.py
      - audit.py
      - quality.py
    - research/
      - __init__.py
      - feature_exploration.py
      - factor_research.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

主要な機能は上記モジュールに分かれています。詳細は各モジュールのドキュメンテーション文字列（docstring）を参照してください。

---

## 運用上の注意点

- 環境変数・シークレットは適切に管理してください（.env を git 管理しない等）。
- DuckDB ファイルはファイルロックやバックアップを適切に扱ってください（複数プロセスでの同時書き込みは注意）。
- J-Quants の API レート制限（120 req/min）を守る設計になっていますが、大量並列での呼び出しは避けてください。
- news_collector は外部 URL を扱うため SSRF 回避・受信サイズ制限を実装していますが、運用環境では追加のセキュリティ対策を検討してください。
- KABUSYS_ENV により production（live）/paper_trading/ development の挙動を切り替えられます。ライブ運用時は特に確認を行ってください。

---

## 開発・コントリビュート

- コードのスタイルは PEP8 準拠を推奨します。
- ユニットテストや統合テストを用意し、外部 API 呼び出しはモックしてテストしてください。
- 大きな設計変更は設計文書（StrategyModel.md / DataPlatform.md 等）に合わせて行ってください（リポジトリ内参照を想定）。

---

README は簡潔に要点をまとめています。さらに詳しい使用例や API 仕様が必要であれば、用途（例: ETL の定期実行設定、監査ログの参照方法、戦略との連携方法）を指定してください。