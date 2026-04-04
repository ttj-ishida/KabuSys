# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
DuckDB をデータレイクとして用い、J-Quants / RSS / OpenAI を組み合わせたデータ収集・品質管理・ファクター計算・AIベースのニュースセンチメント評価・監査ログ等の機能を提供します。

---

## プロジェクト概要

KabuSys は日本株のデータプラットフォームと研究／実行に必要なユーティリティ群をまとめた Python パッケージです。主な目的は以下：

- J-Quants から株価・財務・カレンダーを差分取得して DuckDB に保存する ETL
- ニュース収集（RSS）→ raw_news 保存・銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュース NLP（銘柄別センチメント）と市場レジーム判定
- 研究向けファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログ（signal / order_requests / executions）用のスキーマ初期化ユーティリティ
- 設定は環境変数 / .env ファイルで管理（自動ロード機能あり）

パッケージはモジュール単位で分かれており、ETL／研究／AI／監査／データ処理のそれぞれを独立して利用できます。

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - プロジェクトルートの .env / .env.local を自動読み込み（優先度: OS 環境 > .env.local > .env）
  - 必須キー未設定時にエラーを投げるユーティリティ
  - 自動ロードを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- データ ETL（kabusys.data.pipeline）
  - run_daily_etl: カレンダー・株価・財務の差分取得、保存、品質チェック
  - 個別 ETL 関数: run_prices_etl, run_financials_etl, run_calendar_etl

- J-Quants クライアント（kabusys.data.jquants_client）
  - API 呼び出しのレート制御、リトライ、トークン自動リフレッシュ
  - fetch / save 系の関数（fetch_daily_quotes, save_daily_quotes, fetch_financial_statements 等）

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF/追跡パラメータ対策、raw_news への冪等保存前提実装

- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付整合性チェック
  - QualityIssue 型で問題を収集（severity: error/warning）

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化関数（init_audit_schema / init_audit_db）
  - 冪等／トレーサビリティを重視した設計

- 研究用モジュール（kabusys.research）
  - calc_momentum / calc_value / calc_volatility 等のファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（kabusys.data.stats）で正規化

- AI モジュール（kabusys.ai）
  - score_news: 銘柄別ニュースセンチメントの計算と ai_scores への書き込み
  - score_regime: ETF 1321 の MA200 乖離 + マクロニュース LLM で市場レジーム判定（bull/neutral/bear）
  - OpenAI 呼び出しはリトライやフェイルセーフを備える

---

## セットアップ手順

1. Python と依存ライブラリの準備
   - 推奨 Python バージョン: 3.10+
   - 必要な外部ライブラリ（例）:
     - duckdb
     - openai
     - defusedxml
   - 例: pip でのインストール
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発時はパッケージを editable インストールしておくと便利:
     ```
     pip install -e .
     ```

2. 環境変数 / .env の設定
   - プロジェクトルートに `.env`（必要に応じ `.env.local`）を置くと、kabusys.config が自動で読み込みます（デフォルト）。
   - 重要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN (必須: J-Quants のリフレッシュトークン)
     - OPENAI_API_KEY (OpenAI を使う場合)
     - KABU_API_PASSWORD (kabu API を使う場合)
     - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視DB など: data/monitoring.db)
     - LOG_LEVEL, KABUSYS_ENV (development/paper_trading/live)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知連携）
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

3. データベース準備
   - DuckDB ファイルパスは `DUCKDB_PATH` で指定。デフォルトは `data/kabusys.duckdb`。
   - 監査用独立 DB を初期化する場合は init_audit_db を使用（下で使用例あり）。

---

## 使い方（基本的な例）

以下は Python REPL / スクリプトから各主要機能を利用する例です。

- DuckDB 接続作成
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコア付与（OpenAI API キーが環境変数に設定されている前提）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")
  ```

  - api_key を引数で渡すこともできます:
    ```python
    score_news(conn, date(2026,3,20), api_key="sk-...")
    ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20))
  ```

- ファクター計算（例: モメンタム）
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, target_date=date(2026,3,20))
  # records は {date, code, mom_1m, mom_3m, mom_6m, ma200_dev} の dict リスト
  ```

- 監査ログ DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- データ品質チェック
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

注意点:
- OpenAI 呼び出しは API エラーやレート制限に対してリトライやフォールバック（ゼロスコア）を行います。API キーは引数で注入可能（テスト容易化）。
- 全ての操作は look-ahead bias を避ける設計になっており、内部で datetime.today()/date.today() に依存しない実装が基本です（関数には target_date を与えることを推奨）。

---

## 環境変数と .env 読み込みの挙動

- 自動読み込み:
  - パッケージ import 時に、`__file__` を起点に親ディレクトリを探索して `.git` または `pyproject.toml` を見つけたディレクトリをプロジェクトルートとみなし、以下の順で読み込みます:
    1. OS 環境変数（既定）
    2. `.env`（override=False: OS 環境を上書きしない）
    3. `.env.local`（override=True: .env の値を上書きするが OS 環境は保護）
- 自動ロードを無効にする場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- .env のパースは shell 風の簡易仕様（export KEY= val, コメント、クォート対応等）に準拠しています。
- 必須の環境変数を参照するときは Settings クラスが `_require` を通じてチェックを行い、未設定なら ValueError を投げます（例: JQUANTS_REFRESH_TOKEN）。

---

## 主要ディレクトリ構成

（リポジトリのルートに `src/kabusys` がある想定）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                — 銘柄別ニュースセンチメント / score_news
    - regime_detector.py         — 市場レジーム判定 / score_regime
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（fetch/save）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETL インターフェース（ETLResult 再エクスポート）
    - news_collector.py          — RSS 収集・前処理
    - calendar_management.py     — 市場カレンダー管理（is_trading_day 等）
    - quality.py                 — データ品質チェック
    - stats.py                   — 統計ユーティリティ（zscore_normalize）
    - audit.py                   — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py         — ファクター計算（momentum/value/volatility）
    - feature_exploration.py     — 将来リターン / IC / summary 等
  - monitoring/                   — （実行・監視関係モジュールを想定）
  - execution/                    — （注文実行・ブローカー連携を想定）
  - strategy/                     — （戦略ロジックを想定）

---

## 開発・運用上の注意

- テスト時は環境変数の自動ロードを無効にすると安定してテスト可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- OpenAI の呼び出しはネットワークエラーやレート制限を考慮しており、API 失敗時は安全側のデフォルト（例: macro_sentiment=0.0）で継続します。テストでは内部の呼び出し関数をモックして置き換え可能です（モジュール内に差し替えポイントあり）。
- DuckDB の executemany 周りはバージョン依存の挙動に配慮している箇所があります（空の executemany は回避）。
- 監査ログは削除しない前提（トレーサビリティ確保）。init_audit_db で独立 DB を作成できます。

---

## 参考：よく使う API サンプル

- run_daily_etl の最小呼び出し例（OS 環境に JQUANTS_REFRESH_TOKEN がある想定）:
  ```python
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- OpenAI を使う AI 処理（キーを直接渡す例）:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  score_news(conn, date(2026,3,20), api_key="sk-...")
  ```

---

この README はコードベースの主要機能と使用方法の概要を示しています。詳細は各モジュールの docstring を参照してください（kabusys/data/*.py, kabusys/ai/*.py, kabusys/research/*.py など）。必要であればセットアップの自動化スクリプト、CI 設定例、より詳細な運用手順（監視・ログローテーション・バックテスト向けの注意点等）も追加できます。