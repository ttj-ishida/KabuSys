# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants → DuckDB）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログ（取引トレーサビリティ）、研究用ファクター計算などを含むモジュール群を提供します。

---

## 概要

KabuSys は以下を目的としたライブラリです。

- J-Quants API から株価・財務・カレンダー等のデータを差分取得して DuckDB に保存する ETL パイプライン
- RSS を収集して raw_news を構築し、OpenAI を使って銘柄ごとのニュースセンチメント（ai_score）を付与
- ETF（1321）の 200 日移動平均乖離とマクロニュースセンチメントを組み合わせた市場レジーム判定
- 研究用ファクター（モメンタム・バリュー・ボラティリティ等）や統計ユーティリティ
- 監査ログ（signal_events / order_requests / executions）用スキーマと初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）

設計方針としては、Look-ahead bias を避ける設計、API の堅牢なリトライ／レート制御、DuckDB を用いた冪等保存といった点に注意しています。

---

## 機能一覧

- 環境設定管理（.env 自動読み込み／上書き制御）
- J-Quants API クライアント（rate limit 対応、トークン自動リフレッシュ、ページネーション）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / fetch_listed_info
  - save_* 系で DuckDB へ冪等保存
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
- ニュース収集（RSS の正規化 / 前処理 / SSRF 対策）
- ニュース NLP（score_news：OpenAI による銘柄別 sentiment → ai_scores へ保存）
- 市場レジーム判定（score_regime：ma200 乖離 + マクロニュース LLM）
- 研究用モジュール（calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize）
- データ品質検査（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
- 監査ログスキーマ初期化（init_audit_schema / init_audit_db）

---

## セットアップ手順

前提
- Python 3.10 以上（コードで型 Union | を使用）
- DuckDB が利用可能な環境

1. リポジトリをクローン（またはパッケージを配置）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   （プロジェクトに requirements.txt がない場合は下記の主要依存を入れてください）
   ```
   pip install duckdb openai defusedxml
   ```
   - DuckDB：ローカル分析・永続 DB
   - openai：LLM 呼び出し（gpt-4o-mini を想定）
   - defusedxml：RSS パース時の安全化

4. 環境変数を設定する
   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   最低限必要な環境変数（例）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # OpenAI
   OPENAI_API_KEY=sk-xxxx...

   # kabu Station API（注文実行などを使う場合）
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # システム
   KABUSYS_ENV=development          # development | paper_trading | live
   LOG_LEVEL=INFO

   # オプション（データベースパス等）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```
   注意:
   - .env のパースはシェルライクな簡易実装に対応（export 〜, クォート, コメント等）
   - OS 環境変数は .env の上位優先。上書きを許可するには .env.local を使う。

---

## 使い方（代表的な例）

以下は Python スクリプト / REPL での利用例です。実行前に必要な環境変数（特に JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY）を設定してください。

- DuckDB に接続して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  # target_date を省略すると本日が対象（内部で営業日調整あり）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアを生成する（OpenAI 必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # api_key を明示指定することも可能（None 時は env の OPENAI_API_KEY を使用）
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"scored {n_written} codes")
  ```

- 市場レジームをスコアリングする
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- カレンダー関連ユーティリティ
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  print(is_trading_day(conn, date(2026,3,20)))
  print(next_trading_day(conn, date(2026,3,20)))
  ```

- 監査ログ用 DB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は DuckDB 接続。テーブルは作成済み。
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026,3,20))
  value = calc_value(conn, date(2026,3,20))
  ```

ログレベルは環境変数 LOG_LEVEL で設定できます（DEBUG/INFO/...）。

---

## 重要な注意点

- Look-ahead bias の防止:
  - モジュールは内部で datetime.today() / date.today() を不用意に参照しない設計になっています（関数引数で対象日を渡す）。
  - ETL / スコアリングは必ず「対象日」を明示して使用してください。
- OpenAI の呼び出しには費用が発生します。API キーの管理と利用量には注意してください。
- J-Quants API の利用規約・レート制限を順守してください（モジュールは基本的なレート制御とリトライを実装していますが、過度な呼び出しは避けてください）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml の存在）を基準に行います。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主なファイル）

（プロジェクトの src/kabusys 配下を抜粋）

- kabusys/
  - __init__.py              （パッケージのバージョン・公開モジュール）
  - config.py                （環境変数 / 設定管理）
  - ai/
    - __init__.py
    - news_nlp.py            （ニュース NLP / score_news）
    - regime_detector.py     （市場レジーム判定 / score_regime）
  - data/
    - __init__.py
    - jquants_client.py      （J-Quants API クライアント + save_*）
    - pipeline.py            （ETL パイプライン / run_daily_etl 等）
    - etl.py                 （ETLResult エクスポート）
    - calendar_management.py （市場カレンダー管理）
    - news_collector.py      （RSS 収集・前処理）
    - stats.py               （zscore_normalize 等）
    - quality.py             （データ品質チェック）
    - audit.py               （監査ログスキーマ初期化）
  - research/
    - __init__.py
    - factor_research.py     （calc_momentum / calc_value / calc_volatility）
    - feature_exploration.py （forward returns / IC / summary）
  - monitoring/               （監視系（pid/killフラグ/閾値等）の実装想定ファイル群）
  - execution/                （発注実行ロジック想定ファイル群）
  - strategy/                 （戦略定義想定ファイル群）

（上記以外にユーティリティ・追加モジュールが含まれます）

---

## 開発者向けメモ

- 自動で .env を読み込む処理は config.py 内にあり、.env と .env.local の順で環境変数を設定します。OS の既存環境変数は保護されます。
- OpenAI 呼び出し関連関数はテスト時に差し替えやすいよう、内部で _call_openai_api を用意しています（unittest.mock.patch で置き換え可能）。
- DuckDB 向けの executemany に関する注意点（空リストを渡さない等）に留意して実装されています。
- audit.init_audit_db は transactional=True でスキーマとインデックスを原子的に作成します。

---

## ライセンス / 貢献

本リポジトリのライセンス情報や貢献ガイドラインはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

README に記載した以外で、具体的な使い方（CI、運用ジョブの cron 例、Kubernetes CronJob での運用、LINE 通知連携等）を追加で作成することも可能です。必要であれば運用手順や .env.example のテンプレートを作成します。どの部分を詳しく書きたいか教えてください。