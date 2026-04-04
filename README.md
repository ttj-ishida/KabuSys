# KabuSys

日本株向けの自動売買・データ基盤ライブラリ集です。  
ETL、ニュース収集・NLP、ファクター計算、監査ログ（トレーサビリティ）、市場カレンダーなど、運用に必要なコンポーネントをモジュール化して提供します。

主な設計方針:
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を直接参照しない）
- DuckDB を用いたローカルデータレイヤ
- 外部 API 呼び出しはリトライ・レート制御・フォールバックを厳格に実装
- 冪等的（idempotent）にデータ保存を行う（ON CONFLICT / DELETE→INSERT など）

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダーを取得
  - 差分取得（バックフィル含む）と冪等保存
  - ETL 結果の品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL パイプライン `run_daily_etl`

- ニュース収集 / NLP
  - RSS フィードからのニュース収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - OpenAI（gpt-4o-mini）を用いたニュースごとのセンチメントスコアリング（`score_news`）
  - マクロニュースと ETF（1321）MA200乖離を合成して市場レジーム判定（`score_regime`）

- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（`calc_momentum`, `calc_volatility`, `calc_value`）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化ユーティリティ

- カレンダー管理
  - JPX マーケットカレンダーの取得・保存・営業日判定ヘルパー（`is_trading_day`, `next_trading_day`, `get_trading_days` 等）
  - カレンダー更新バッチ（`calendar_update_job`）

- 監査ログ（Audit）
  - シグナル・発注・約定のトレーサビリティ（監査テーブルの初期化・専用 DB 初期化ヘルパー）

- 設定管理
  - .env / .env.local の自動読込（プロジェクトルートの検出）
  - 環境変数アクセスラッパー（`kabusys.config.settings`）

---

## セットアップ手順

前提:
- Python 3.10+（型ヒント等を利用）
- ネットワーク経由で J-Quants / OpenAI を呼べる環境

1. リポジトリをクローンしてパッケージをインストール（開発モード推奨）:
   ```bash
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   ```

2. 必要な外部パッケージ（主なもの）:
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリの urllib 等を使用）

   手動でインストールする場合:
   ```bash
   pip install duckdb openai defusedxml
   ```

3. 環境変数の設定:
   プロジェクトルートに `.env`（または `.env.local`）を作成すると自動読み込みされます。読み込みは OS 環境変数 > .env.local > .env の優先順位で行われます。自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に使用）
   - KABU_API_BASE_URL: kabu API のベース URL（省略時 http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知に使用（任意）
   - DUCKDB_PATH: データ用 DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
   - PID_FILE_PATH / KILL_FLAG_PATH: 実行監視用フラグファイルパス 等

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxx...
   DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
   ```

4. データディレクトリ作成（必要に応じて）:
   ```bash
   mkdir -p data
   ```

---

## 使い方（代表的な例）

以下は基本的な Python API 使用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect() が返す接続）を引数に取る設計です。

- DuckDB 接続を用意する:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアを作成する（OpenAI API キーは環境変数か引数で指定）:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {written} codes")
  ```

- 市場レジームを判定する:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB を初期化する:
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # 以降 audit_conn を使って order_requests / executions 等を操作
  ```

- RSS の取得（ニュース収集の一部）:
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  ```

注意点:
- OpenAI を使う関数（news_nlp.score_news / regime_detector.score_regime）は API 呼び出しに失敗した場合にフォールバック（スコア0）する設計ですが、API キーは必須です。キーは引数で渡すか環境変数 `OPENAI_API_KEY` を設定してください。
- DuckDB の executemany は空リストを受け付けないバージョン依存の挙動があるため、モジュール側で空チェックが実装されています（呼び出し側は特に意識する必要はありません）。

---

## ディレクトリ構成

主要ファイル（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュースセンチメント（OpenAI）/ score_news, calc_news_window
    - regime_detector.py     -- 市場レジーム判定（ETF 1321 MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント、保存関数（save_*）
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等） / ETLResult
    - etl.py                 -- ETLResult 再エクスポート
    - news_collector.py      -- RSS 収集、前処理、SSRF 対策
    - calendar_management.py -- 市場カレンダー管理、営業日判定、calendar_update_job
    - stats.py               -- zscore_normalize 等の統計ユーティリティ
    - quality.py             -- 品質チェック（欠損・スパイク・重複・日付整合性）
    - audit.py               -- 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py     -- calc_momentum / calc_value / calc_volatility
    - feature_exploration.py -- calc_forward_returns / calc_ic / factor_summary / rank
  - ai/ and research/ は研究・戦略開発向けの機能を提供

その他:
- 環境変数自動ロード: config._find_project_root は .git または pyproject.toml を基点に .env/.env.local を探索します。
- 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 開発・寄稿の注意点

- ルックアヘッドバイアス防止設計のため、日付処理・DB クエリは target_date を明示して呼ぶこと。
- OpenAI / J-Quants の呼び出しはネットワーク障害やレート制限を考慮したリトライロジックを持ちます。テスト時には該当モジュールの内部 _call_openai_api などをモックしてください。
- DuckDB のバージョン差異（executemany の空リスト扱い等）に注意。モジュール内で対応済みの箇所があります。

---

もし README に追加したい具体的な使用例（戦略のフロー、CLI 実行方法、.env.example のテンプレート等）があれば教えてください。それに合わせてサンプルを追記します。