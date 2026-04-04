# KabuSys

日本株向けの自動売買 & データ基盤ライブラリ（Python）。  
ETL、ニュース NLP（LLM ベース）スコアリング、リサーチ用ファクター計算、監査ログ（トレーサビリティ）、JPX カレンダー管理などを含むモジュール群を提供します。

---

## 主な特徴（機能一覧）

- データ収集 / ETL
  - J-Quants API から株価（OHLCV）、財務情報、マーケットカレンダーを差分取得・保存（DuckDB）
  - 差分更新・バックフィル・ページネーション対応、ID トークン自動リフレッシュ、レート制御、リトライ
- データ品質チェック
  - 欠損、重複、スパイク、将来日付／非営業日データ検出
- ニュース収集
  - RSS 収集・前処理（URL 正規化・トラッキング除去）・SSRF 対策
- ニュース NLP（LLM 統合）
  - 銘柄ごとのニュースセンチメントを OpenAI（gpt-4o-mini）で取得し ai_scores テーブルへ保存
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA + LLM）
  - JSON Mode を用いた堅牢なレスポンス検証・リトライ実装
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー
  - 汎用 z-score 正規化ユーティリティ
- 監査（Audit）
  - シグナル → 発注 → 約定までを UUID 連鎖でトレースする監査テーブル群（DuckDB）
  - 冪等・時刻は UTC 保存
- 運用監視 / 設定管理
  - 環境変数による設定管理、.env / .env.local の自動ロード（無効化可）

---

## 前提条件

- Python 3.9+（型アノテーションのユニオンや typing 機能を使用）
- 必要なパッケージ（一例）:
  - duckdb
  - openai
  - defusedxml
- J-Quants / OpenAI 等の外部 API キーが必要（用途に応じて）

実行時に利用する DB は DuckDB（ファイルまたはメモリ）を想定しています。

---

## セットアップ手順

1. リポジトリをクローン / パッケージをインストール
   ```
   git clone <this-repo>
   cd <this-repo>
   pip install -e .                # setup.py / pyproject が用意されている想定
   pip install duckdb openai defusedxml
   ```

2. .env の作成
   - プロジェクトルートに .env（または .env.local）を作成します。
   - 自動ロード仕様: OS 環境変数 > .env.local > .env の順で読み込みされます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

3. 必須の環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須、ETL 等で使用）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（発注連携がある場合）
   - （任意）KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, など

   設定可能な環境変数の例（デフォルト値があるものも含む）:
   - KABUSYS_ENV (development / paper_trading / live)
   - LOG_LEVEL (DEBUG / INFO / ...)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
   - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT

---

## 使い方（主要な利用例）

以下はモジュールの代表的な使用例です。実行前に設定値（環境変数）を用意してください。

- DuckDB 接続の作成例
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（市場カレンダー、株価、財務、品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース NLP スコア（銘柄ごとの ai_scores への書き込み）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {count}")
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM スコアを合成）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ（監査用 DuckDB 初期化）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")  # :memory: も可
  ```

- RSS フィード取得（ニュース収集の下位ユーティリティ）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  ```

- J-Quants クライアント（データ取得 / 保存）
  ```python
  from kabusys.data import jquants_client as jq

  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date.today())
  saved = jq.save_daily_quotes(conn, records)
  ```

注意：上記の多くの関数は OpenAI / J-Quants API キーを環境変数（または引数）で参照します。未設定時は ValueError などが発生します。

---

## 重要な設計上の注意点（運用上のポイント）

- Look-ahead bias を避ける
  - モジュール内部は target_date を明示的に受け取り、datetime.today()/date.today() を直接参照しない設計を優先しています（バックテスト用）。
- 冪等性
  - DuckDB への保存は基本的に ON CONFLICT DO UPDATE / INSERT ... DO NOTHING 等で冪等になっています。
- エラーハンドリングとフォールバック
  - LLM / API 呼び出しはリトライ（指数バックオフ）を行い、致命的な例外が発生しても他処理を継続する設計（フェイルセーフ）。
  - LLM 呼び出し失敗時はスコアを 0.0 にフォールバックする箇所があります（設定済み）。
- セキュリティ対策
  - RSS取得は SSRF 対策（ホストのプライベート判定、リダイレクト検査）を実装しています。
  - XML パースに defusedxml を使用。
- レート制御
  - J-Quants API は固定間隔スロットリングで制御（120 req/min）。
- テスト差し替えポイント
  - OpenAI 呼び出しや URL オープン部分はモックしやすいように設計されています（ユニットテストの差し替えが容易）。

---

## ディレクトリ構成（概要）

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数 / 設定読み込み（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                    -- ニュース NLP（銘柄スコア取得）
    - regime_detector.py             -- 市場レジーム判定（MA + マクロ LLM）
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント（fetch / save）
    - pipeline.py                    -- ETL パイプライン（run_daily_etl など）
    - etl.py                         -- ETLResult のエクスポート
    - news_collector.py              -- RSS 取得・前処理・保存ユーティリティ
    - calendar_management.py         -- JPX カレンダー管理（is_trading_day 等）
    - quality.py                     -- データ品質チェック
    - stats.py                       -- z-score 等の統計ユーティリティ
    - audit.py                       -- 監査ログ用テーブル定義と初期化
  - research/
    - __init__.py
    - factor_research.py             -- モメンタム / バリュー / ボラティリティ
    - feature_exploration.py         -- 将来リターン / IC / 統計サマリー
  - monitoring/  (未列挙の可能性あり)
  - execution/   (発注関連モジュール等、概要)

（各モジュールは DuckDB 接続を引数で受け取る設計が多く、外部副作用を最小化しています）

---

## よく使う環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
- OPENAI_API_KEY (必須 for LLM): OpenAI API キー（score_news / score_regime）
- KABU_API_PASSWORD: kabu API パスワード
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト data/monitoring.db）
- KABUSYS_ENV: environment (development / paper_trading / live)
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動ロードを無効化

環境変数は .env / .env.local から自動ロードされます（プロジェクトルートは .git または pyproject.toml を基準に探索）。

---

## 貢献・拡張

- 新しい ETL データソース / ニュースソースの追加は、jquants_client / news_collector に沿って実装してください。
- OpenAI モデルやプロンプトは news_nlp / regime_detector 内の定数で管理されています。プロンプト改善やモデル切替はそこを編集します。
- 単体テストは API 呼び出し部分をモックして行ってください（_call_openai_api や _urlopen など差し替え可能）。

---

README に記載のない細かい実装詳細は各モジュールの docstring / ソースをご参照ください。追加で README の改善点や、利用例のサンプル（CLI スクリプト、Docker コンテナ化、運用手順など）を希望される場合は教えてください。