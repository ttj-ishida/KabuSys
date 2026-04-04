# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリ群です。  
J-Quants や RSS、OpenAI（LLM）などを組み合わせ、データ収集（ETL）・品質チェック・ニュース NLP・市場レジーム判定・ファクター計算・監査ログ管理などを提供します。

主な用途
- 日次 ETL（株価、財務、マーケットカレンダー）の差分取得・保存
- ニュース記事の収集と LLM による銘柄別センチメント付与
- マクロニュース＋ETF MA による市場レジーム判定
- ファクター計算（モメンタム、バリュー、ボラティリティ等）および研究用ユーティリティ
- 取引監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化

---

## 機能一覧

- 環境変数管理（.env 自動ロード・保護機能）
- J-Quants API クライアント（株価、財務、マーケットカレンダー、上場銘柄情報）
  - レートリミット・リトライ・トークン自動リフレッシュ対応
  - DuckDB へ冪等保存（ON CONFLICT …）
- ETL パイプライン（差分取得、バックフィル、品質チェックの一括実行）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集（RSS）と前処理（URL 正規化・SSRF 対策）
- ニュース NLP（OpenAI による銘柄別センチメント算出、バッチ処理／リトライ実装）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの組合せ）
- 監査ログ管理（監査用テーブルの初期化／独立 DuckDB DB 作成ユーティリティ）
- 研究用モジュール（ファクター計算、forward returns、IC、Z-score 正規化 等）
- 共通統計ユーティリティ（zscore_normalize 等）

---

## 必要条件 / 依存パッケージ（抜粋）

本リポジトリに requirements.txt がない場合の最低限の例（環境に応じて調整してください）:

- Python 3.10+
- duckdb
- openai
- defusedxml

例:
pip install duckdb openai defusedxml

（実運用では他にもログ・テスト用パッケージ等が必要になる可能性があります）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存関係をインストール
   ```
   pip install -r requirements.txt
   ```
   requirements.txt が無い場合は最低限以下を入れておくと動作確認ができます:
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（優先順位: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

   主な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須：ETL 実行時）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時）
   - KABU_API_PASSWORD: kabuステーション API パスワード（注文実行用）
   - KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - PID_FILE_PATH / KILL_FLAG_PATH: 実行監視用のパス
   - KABUSYS_ENV: 実行環境 (development|paper_trading|live)
   - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

5. データディレクトリの作成（必要であれば）
   ```
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下は Python REPL やスクリプトから各機能を呼び出す例です。関数の引数や戻り値は各モジュールの docstring を参照してください。

- DuckDB 接続と日次 ETL 実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  # target_date を指定しない場合は today（実運用時は ETL のタイミングに注意）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコア付与（OpenAI API キーが環境変数 OPENAI_API_KEY に設定されている前提）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {written} codes")
  ```

  - api_key を直接渡すことも可能:
    score_news(conn, date(2026,3,20), api_key="sk-...")

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ用 DuckDB 初期化
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events, order_requests, executions 等のテーブルが作成される
  ```

- 研究用ファクター計算（例: momentum）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  print(len(records))
  ```

注意点
- LLM（OpenAI）を呼び出す関数（score_news / score_regime）は API キーが必要です。引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- DuckDB のスキーマ（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_calendar, prices_daily 等）は ETL や別の初期化スクリプトで作成しておく必要があります。audit.init_audit_db は監査ログ用スキーマを初期化しますが、全体スキーマはプロジェクト付属のスキーマ初期化コード（data/schema など）がある想定です。

---

## 自動環境読み込みの挙動

- 実行時、パッケージはプロジェクトルート（.git または pyproject.toml を含む親ディレクトリ）を探索し、`.env` と `.env.local` を自動で読み込みます。
  - 優先順位: OS 環境 > .env.local > .env
  - `.env.local` は `.env` を上書きできます（override=True）。
- 自動ロードを無効化したい場合は環境変数を設定:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## 主要モジュール・ディレクトリ構成

以下は主要なモジュールとその役割の一覧（リポジトリ内の src/kabusys 配下を中心に抜粋）:

- kabusys/
  - __init__.py
    - パッケージ初期化・公開モジュール定義
  - config.py
    - .env の解釈、環境変数の読み込み、Settings クラス（設定取得ユーティリティ）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの LLM による銘柄別センチメント算出（score_news）
    - regime_detector.py
      - ETF(1321) の 200日 MA とマクロニュースを統合した市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ロジック、レート制御、リトライ、ID トークン管理）
    - pipeline.py
      - 日次 ETL の実装（run_daily_etl, 個別 ETL 実行関数）
    - etl.py
      - ETLResult の再エクスポート
    - quality.py
      - データ品質チェック（欠損、スパイク、重複、日付整合性）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - news_collector.py
      - RSS 取得・前処理・raw_news 保存ロジック（SSRF 対策等）
    - calendar_management.py
      - 市場カレンダー管理、営業日判定、calendar_update_job（J-Quants からの差分取得）
    - audit.py
      - 監査ログスキーマ定義・初期化（signal_events, order_requests, executions）
  - research/
    - __init__.py
    - factor_research.py
      - momentum / value / volatility 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー等
  - monitoring/, execution/, strategy/, その他
    - パッケージ __all__ では data/research/ai/monitoring 等を想定（コードベースに応じて追加）

（上記は本 README に含まれる主要ファイルの抜粋です。完全なファイル一覧はリポジトリを参照してください。）

---

## 開発・拡張メモ

- DuckDB を用いた SQL ベースの処理が中心です。性能改善やスキーマ変更を行う際は DuckDB のバージョン特性に注意してください（executemany の空リスト等）。
- LLM 呼び出しはリトライ＆フェイルセーフ設計（API が失敗してもプロセス全体を停止しない）になっています。運用設定（リトライ回数、バッチサイズ等）はモジュール定数で調整可能です。
- Look-ahead bias を避ける設計指針が一貫して適用されています（target_date を明示する、DB クエリで date < target_date を徹底する等）。
- セキュリティ面: RSS 取得や外部 URL 処理は SSRF 対策・XML 攻撃対策（defusedxml）を含みます。外部連携を追加する際は同等の安全設計を徹底してください。

---

## ライセンス / 貢献

この README にはライセンス情報を含めていません。実際のリポジトリでは LICENSE を確認してください。バグ修正や機能追加はプルリクエストでお願いします。大きな設計変更前には issue を立てて議論してください。

---

README に書いた以外の詳細は各モジュールの docstring を参照してください。必要であれば、サンプルスクリプトや schema 初期化スクリプトの雛形も作成できますのでご要望をお知らせください。