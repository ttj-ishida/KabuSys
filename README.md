# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants）→ データ品質チェック → ファクター算出 → ニュースNLP / レジーム判定 → 監査ログまで、トレード運用およびリサーチに必要な主要機能を含みます。

バージョン: 0.1.0

---

## 目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（代表的な API と例）
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株の自動売買システム／データプラットフォーム向けユーティリティ群です。  
主に次を提供します。

- J-Quants API からの差分 ETL（株価、財務、JPX カレンダー）
- DuckDB を用いたデータ保存・監査スキーマ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ファクター計算（モメンタム、バリュー、ボラティリティ 等）
- ニュースの収集・NLP（OpenAI を用いた銘柄別センチメント）
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- 監査ログ（signal → order_request → executions のトレース）

設計方針としては、Look-ahead bias の回避、冪等性（DB 書き込み）、外部 API の堅牢なリトライ・レート制御を重視しています。

---

## 機能一覧（主なモジュール）
- kabusys.config
  - .env / 環境変数自動読み込み（プロジェクトルート検出）
  - 必須設定の収集（settings オブジェクト）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得／保存／認証）
  - pipeline: 日次 ETL パイプライン（run_daily_etl 等）
  - quality: データ品質チェック（run_all_checks 等）
  - news_collector: RSS 収集と raw_news 保存ユーティリティ
  - calendar_management: JPX カレンダー判定・更新ロジック
  - audit: 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - stats: 共通統計ユーティリティ（zscore_normalize）
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores に保存
  - regime_detector.score_regime: 市場レジームを market_regime に書き込み
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

前提:
- Python 3.10+（typing | union を活用）
- DuckDB を使用（ローカルファイルまたは :memory:）

1. 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

2. 依存パッケージのインストール  
   （プロジェクトに requirements.txt がない場合の最低推奨例）
   ```bash
   pip install duckdb openai defusedxml
   ```
   - J-Quants API 用に urllib/標準ライブラリで実装済み
   - OpenAI SDK は gpt-4o-mini などの呼び出しに使用しています

3. ソースを editable インストール（任意）
   ```bash
   pip install -e .
   ```

4. 環境変数 / .env の準備  
   プロジェクトルートに `.env`（および `.env.local`）を置くと自動読み込みされます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
   - OPENAI_API_KEY — OpenAI API キー（news/regime の呼び出しで使用）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 通知用（任意）
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db
   - KABUSYS_ENV — development | paper_trading | live（デフォルト development）
   - LOG_LEVEL — DEBUG/INFO/...（デフォルト INFO）

   .env のサンプルはプロジェクトに .env.example を用意してください（存在を想定しています）。

---

## 使い方（代表 API とサンプル）

以下は主要機能の簡単な利用例です。関数は多くが DuckDB 接続（duckdb.connect(...) の戻り値）を受け取ります。

- DuckDB 接続の作成
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコア（OpenAI を使用）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY は環境変数に設定するか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"ai_scores に書き込んだ銘柄数: {n_written}")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（例：モメンタム）
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # records は dict のリスト（date, code, mom_1m, mom_3m, mom_6m, ma200_dev）
  ```

- 監査ログ（監査DB の初期化）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # init_audit_db はスキーマを作成して接続を返す
  ```

- J-Quants の生 API 呼び出し（必要に応じて直接使用）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

  id_token = get_id_token()  # settings.jquants_refresh_token を使用
  recs = fetch_daily_quotes(id_token=id_token, date_from=date(2026,1,1), date_to=date(2026,3,1))
  ```

- データ品質チェック
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

注意:
- OpenAI 呼び出しは API エラー時にフォールバックやリトライを行う設計ですが、API キーの管理は利用者側で行ってください。
- 多くの関数は Look-ahead バイアスを避けるため内部で date.today() を安易に使わない設計です。必ず target_date を指定してテスト／バッチ処理を行うことを推奨します。

---

## ディレクトリ構成

主要ファイル／ディレクトリ（src 配下の kabusys パッケージ）:

- kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュース NLP（score_news）
    - regime_detector.py               — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント（fetch/save）
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - quality.py                       — データ品質チェック
    - news_collector.py                — RSS 収集・前処理
    - calendar_management.py           — 市場カレンダーの管理
    - stats.py                         — zscore_normalize 等統計ユーティリティ
    - audit.py                         — 監査ログスキーマ初期化
    - etl.py                           — ETL 結果型エクスポート
    - pipeline.py                       (メイン ETL 実装)
  - research/
    - __init__.py
    - factor_research.py               — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py           — calc_forward_returns / calc_ic / factor_summary / rank

その他:
- .env / .env.local （プロジェクトルートに置くことで自動的に読み込まれます。）
- data/（デフォルトの DuckDB/SQLite ファイル保存先）

---

## 補足・運用上の注意
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。テスト時に自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API はレート制限（120 req/min）があります。jquants_client は内部に RateLimiter を実装していますが、大規模並列処理時は注意してください。
- DuckDB 側の executemany の挙動（空リストの扱い等）に注意する実装になっています（互換性向上のため）。

---

README に書かれている以外にも多数のユーティリティ関数・設計上の考慮事項がソース内にコメントとして記載されています。API の詳細な使用方法は各モジュールの docstring を参照してください。必要であれば、利用ケース別の詳細ドキュメントやサンプルスクリプト作成を支援します。