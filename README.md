# KabuSys

日本株向けのデータパイプライン・リサーチ・自動売買基盤の一部実装。  
DuckDB をデータレイクに、J-Quants / OpenAI / RSS 等を外部ソースとして利用し、ETL、データ品質チェック、ニュース NLP、ファクター計算、監査ログなどを提供します。

主な設計方針
- ルックアヘッドバイアスを避ける（関数内で datetime.today()/date.today() を直接参照しない）
- DuckDB を使った SQL + Python のハイブリッド実装
- 冪等性（ON CONFLICT / idempotent 保存）とトランザクション管理
- フェイルセーフ：外部 API 失敗時は重大例外を投げずに続行する設計（必要に応じてログ警告）

---

## 機能一覧

- 環境設定管理
  - .env の自動読み込み（プロジェクトルート検出）と必須環境変数チェック
- データ取得（J-Quants クライアント）
  - 株価日足（OHLCV）、財務データ、JPX カレンダー、上場情報の取得・ページネーション対応
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン
  - daily ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新・バックフィル制御・品質チェック（欠損・重複・スパイク・日付不整合）
  - ETL 結果を表す ETLResult
- ニュース収集
  - RSS 取得（SSRF 対策、トラッキングパラメータ削除、gzip 対応）
  - raw_news / news_symbols への冪等保存ロジック（ID は正規化 URL のハッシュ）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメントを LLM（gpt-4o-mini）で評価し ai_scores に格納
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 と LLM センチメントの合成）
  - JSON Mode（厳密 JSON レスポンス）・リトライ・バリデーション実装
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - z-score 正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
  - 監査 DB 初期化（UTC タイムゾーン固定）とトランザクショナル作成

---

## 必要な環境変数

（.env または OS 環境変数で設定）

必須（アプリケーションの使用機能に依存して必要）
- JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン（jquants API 用）
- KABU_API_PASSWORD - kabuステーション API のパスワード（注文実行を行う場合）
- SLACK_BOT_TOKEN - Slack 通知用 Bot トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID - Slack チャンネル ID（通知先）

任意 / デフォルトあり
- KABUSYS_ENV - 環境（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL - ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）。デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD - 自動 .env ロードを無効化（1 で無効）
- KABU_API_BASE_URL - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH - データ格納用 DuckDB パス（例: data/kabusys.duckdb）。デフォルト: data/kabusys.duckdb
- SQLITE_PATH - 監視用 SQLite パス（デフォルト: data/monitoring.db）
- OPENAI_API_KEY - OpenAI 呼び出しに使用（score_news / score_regime は引数でも指定可能）

.env.example（簡易）
- JQUANTS_REFRESH_TOKEN=
- KABU_API_PASSWORD=
- SLACK_BOT_TOKEN=
- SLACK_CHANNEL_ID=
- OPENAI_API_KEY=
- KABUSYS_ENV=development
- LOG_LEVEL=INFO
- DUCKDB_PATH=data/kabusys.duckdb

---

## セットアップ手順

前提
- Python 3.10+（typing の | 演算子や annotations の使い方に対応）
- Git, pip 等

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトが pyproject.toml / requirements を持つ場合はそれに従ってください。上は主要ランタイム依存のみ示しています）

4. 環境変数設定
   - プロジェクトルートに .env を作成するか、OS 環境変数で設定
   - 自動読み込みは .env / .env.local をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

5. データベース初期化（監査テーブルなど）
   - 監査ログ専用 DB を初期化する例:
     - Python から:
       from kabusys.data.audit import init_audit_db
       conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（主要な例）

以下は Python スクリプトや REPL から呼び出す利用例です。適宜環境変数やパスを調整してください。

- 設定と DuckDB 接続
  - from kabusys.config import settings
    import duckdb
    conn = duckdb.connect(settings.duckdb_path)

- 日次 ETL 実行（カレンダー→株価→財務→品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn)  # target_date を指定することも可能
    print(result.to_dict())

- ニュースセンチメント（指定日分）
  - from kabusys.ai.news_nlp import score_news
    from datetime import date
    # OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
    written = score_news(conn, date(2026, 3, 20))  # 書き込んだ銘柄数を返す

- 市場レジーム判定（マクロニュース + ETF MA200）
  - from kabusys.ai.regime_detector import score_regime
    from datetime import date
    score_regime(conn, date(2026, 3, 20))  # market_regime テーブルへ書き込み

- ファクター計算 / 研究用ユーティリティ
  - from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
    m = calc_momentum(conn, date(2026, 3, 20))
    v = calc_value(conn, date(2026, 3, 20))

- 監査テーブルの初期化（既存接続へ追加）
  - from kabusys.data.audit import init_audit_schema
    init_audit_schema(conn, transactional=True)

注意点
- score_news / score_regime など OpenAI を呼ぶ処理は API キー必須（引数で渡すか OPENAI_API_KEY を環境変数で設定）
- ETL や calendar 更新は外部 API（J-Quants）に依存するため、JQUANTS_REFRESH_TOKEN が必要
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと .env の自動ロードを無効化できます

---

## ディレクトリ構成（概要）

- src/kabusys/__init__.py
  - パッケージ定義（version, __all__）
- src/kabusys/config.py
  - 環境変数ロード・Settings クラス
- src/kabusys/ai/
  - news_nlp.py       - ニュースの LLM スコアリング（score_news）
  - regime_detector.py- マクロ + MA を合成した市場レジーム判定（score_regime）
  - __init__.py       - score_news のエクスポート
- src/kabusys/data/
  - jquants_client.py      - J-Quants API クライアント（fetch/save）
  - pipeline.py            - ETL 実装と run_daily_etl, run_prices_etl, run_financials_etl 等
  - quality.py             - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector.py      - RSS 取得と前処理、raw_news への保存ロジック
  - calendar_management.py - 市場カレンダー管理 / 営業日判定機能
  - stats.py               - 汎用統計ユーティリティ（zscore_normalize）
  - audit.py               - 監査ログスキーマ定義と初期化ユーティリティ
  - etl.py                 - ETLResult の再エクスポート
- src/kabusys/research/
  - factor_research.py     - ファクター計算（momentum/value/volatility）
  - feature_exploration.py - 将来リターン・IC・統計サマリー
  - __init__.py            - 研究ユーティリティの公開 API
- src/kabusys/ai/__init__.py
- ほか：strategy, execution, monitoring, などの名前空間が README に触れられているが、このコードベース内では主に data / ai / research に重点を置いています。

---

## テスト・開発時のヒント

- 自動 .env ロードはプロジェクトルート検出（.git または pyproject.toml）に基づき行われます。CI / テストで明示的に環境を制御するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し箇所は内部で _call_openai_api を定義しており、テスト時にはこの関数をモックして API コストや外部依存を排除できます（unittest.mock.patch を使用）。
- DuckDB を使う関数は接続オブジェクトを引数で受け取るため、インメモリ DB (":memory:") を使った単体テストが容易です。
- news_collector は defusedxml, SSRF 対策、レスポンスサイズチェックなどセキュリティに配慮した実装です。テストでは fetch_rss 内の _urlopen をモックして外部接続を避けてください。

---

以上がこのコードベースの概要と主要な使い方です。特定の機能や API の使い方（例: ETL の細かなオプション、news_nlp のプロンプト挙動、監査スキーマの拡張など）について詳しく知りたい項目があれば教えてください。必要に応じて README を拡張します。