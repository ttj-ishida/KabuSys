# KabuSys

KabuSys は日本株のデータプラットフォームと自動売買（バックエンド）向けのユーティリティ群です。  
ETL、データ品質チェック、ニュース収集・NLP（LLM 評価）、ファクター計算、監査ログ、マーケットカレンダー管理、J-Quants API クライアントなどを提供し、戦略層・実行層・モニタリングと連携するための基盤機能を揃えています。

バージョン: 0.1.0

---

## 主要機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（差分取得・ページネーション・トークン自動リフレッシュ・レート制御）
  - 日次 ETL パイプライン（株価、財務、マーケットカレンダーの差分取得・保存）
- データ品質管理
  - 欠損、重複、スパイク、日付不整合のチェック（QualityIssue を返す）
- マーケットカレンダー管理
  - 営業日判定、前後営業日の取得、カレンダー夜間更新ジョブ
- ニュース収集
  - RSS フィードの取得・前処理・raw_news 保存（SSRF 対策・トラッキング除去・サイズ上限）
- ニュース NLP（LLM）
  - 銘柄ごとのニュースセンチメント算出（gpt-4o-mini を想定、JSON mode）
  - マクロニュースを用いた市場レジーム判定（ma200 乖離 + LLM センチメントの合成）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリー、Zスコア正規化
- 監査（トレーサビリティ）
  - signal_events / order_requests / executions を含む監査スキーマの初期化・DB 作成ユーティリティ
- AI / OpenAI 統合（OpenAI SDK を利用）
- その他ユーティリティ（統計関数、DB 保存関数等）

パッケージはモジュール分割されています（例: kabusys.data, kabusys.ai, kabusys.research, kabusys.data.jquants_client など）。

---

## セットアップ手順

前提:
- Python 3.10+（型ヒントの `X | Y` 構文を使用）
- DuckDB（Python パッケージ duckdb）
- OpenAI (openai パッケージ)
- defusedxml（RSS パースの安全対策）
- その他標準ライブラリ

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate または .\.venv\Scripts\activate

2. パッケージのインストール（プロジェクトのルートで）
   - pip install -e . 
     - （プロジェクト配布に setup.cfg/pyproject.toml があれば上記で依存が入ります）
   - 依存がない場合は最低限:
     - pip install duckdb openai defusedxml

3. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動ロードされます（設定は kabusys.config が行います）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
   - 必須（実行に必要な主な変数）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN: Slack 通知を使う場合
     - SLACK_CHANNEL_ID: Slack チャンネル ID
     - KABU_API_PASSWORD: kabu API を使う場合のパスワード
   - 任意:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 で自動 .env ロードを無効化
     - OPENAI_API_KEY: OpenAI を使う場合（関数引数でも指定可能）
     - DUCKDB_PATH, SQLITE_PATH（DB ファイルパス。デフォルト: data/kabusys.duckdb / data/monitoring.db）

4. データベース初期化（監査 DB など）
   - 監査テーブルを作成する場合:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
   - その他テーブルは ETL 実行やスキーマ初期化コードに依存します。

---

## 使い方（主要 API と例）

以下は代表的な利用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect() が返す接続）を受けます。

- DuckDB 接続例:
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する:
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=None)  # target_date を指定するとその日を対象に実行
  - print(result.to_dict())

- J-Quants API を直接呼ぶ:
  - from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
  - records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  - saved = save_daily_quotes(conn, records)  # save_ 関数も同モジュールにあります

- ニュース収集:
  - from kabusys.data.news_collector import fetch_rss, preprocess_text
  - articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")

- ニュース NLP（銘柄ごとのスコア）:
  - from kabusys.ai.news_nlp import score_news
  - n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")  # api_key 省略時は環境変数 OPENAI_API_KEY

- 市場レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- データ品質チェック:
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=date(2026,3,20))
  - for i in issues: print(i)

- カレンダー関連:
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
  - is_trade = is_trading_day(conn, date(2026,3,20))

- 研究用:
  - from kabusys.research import calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
  - mom = calc_momentum(conn, date(2026,3,20))

注意:
- OpenAI 呼び出しは外部 API であるため rate limit やコストに注意してください。
- 多くの関数は外部キーや特定のテーブル（raw_prices, raw_news, ai_scores, prices_daily, raw_financials, market_calendar など）を前提とします。ETL やスキーマ初期化を行ってから使用してください。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD: kabu ステーション API 用パスワード
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

.kabusys.config.Settings からこれらを参照できます:
- from kabusys.config import settings
- settings.jquants_refresh_token, settings.is_live, settings.duckdb_path, ...

---

## ディレクトリ構成

プロジェクトは src/kabusys 以下でモジュール分割されています。主なファイルと役割:

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数読み込み・設定管理（.env 自動ロード機能を含む）
- src/kabusys/ai/
  - news_nlp.py: ニュースを LLM に投げて銘柄ごとのスコアを生成
  - regime_detector.py: ma200 とマクロニュース LLM を合成して市場レジーム判定
- src/kabusys/data/
  - jquants_client.py: J-Quants API クライアント（fetch / save 関数）
  - pipeline.py: ETL パイプライン（run_daily_etl など）
  - etl.py: ETL の公開型（ETLResult の再エクスポート）
  - news_collector.py: RSS 収集・前処理
  - calendar_management.py: マーケットカレンダー管理・判定ロジック
  - quality.py: データ品質チェック
  - stats.py: zscore_normalize など共通統計ユーティリティ
  - audit.py: 監査ログスキーマ初期化（signal_events / order_requests / executions）
- src/kabusys/research/
  - factor_research.py: モメンタム・ボラティリティ・バリュー計算
  - feature_exploration.py: 将来リターン、IC、統計サマリー、ランク関数
- src/kabusys/research/__init__.py
- src/kabusys/ai/__init__.py

（戦略層 / 実行層 / モニタリング用のモジュール名はパッケージ API に含まれていますが、実装の有無はリポジトリの内容に依存します: kabusys.__all__ = ["data", "strategy", "execution", "monitoring"]）

簡易ツリー（抜粋）:
- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - data/
      - jquants_client.py
      - pipeline.py
      - news_collector.py
      - calendar_management.py
      - quality.py
      - audit.py
      - stats.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - research/__init__.py

---

## 注意点 / 設計方針（要点）

- Look-ahead bias を避ける設計:
  - 内部処理は原則として datetime.today() や date.today() を関数内部で直接参照しない（外部から target_date を渡す）。
  - データ取得 / スコアリングは target_date 未満・以前のデータのみを参照するように注意。
- LLM 呼び出しはフォールバックあり:
  - API エラーやパースエラー時には例外を上げずフェイルセーフでゼロスコア等にフォールバックする部分が多い。
- DuckDB を積極活用:
  - SQL ウィンドウ関数や executemany を利用して高効率に処理。
- 冪等性:
  - ETL・保存処理は ON CONFLICT / DELETE → INSERT 等で冪等保存を意識している。
- セキュリティ:
  - RSS 収集に SSRF 対策、defusedxml を利用した XML パース、レスポンスサイズ制限などを実装。

---

## よくある利用フロー（例）

1. .env に必要なトークンを配置
2. DuckDB 接続を生成（settings.duckdb_path を使用）
3. run_daily_etl を呼んでデータを収集・保存
4. quality.run_all_checks でデータ品質を確認
5. research 関数でファクターを計算、戦略でシグナル生成
6. 生成されたシグナルを order_requests テーブルに保存し、実行層で証券 API に送信
7. executions を監査テーブルに記録してトレーサビリティを確保

---

## 開発 / 貢献

- バグ報告・機能改善提案は Issue を立ててください。
- コードスタイルはプロジェクト標準（型ヒント重視、単体テスト推奨）に従ってください。
- テスト時に環境変数自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

この README はリポジトリ内のソースコード（src/kabusys 以下）を基に作成しています。詳細な API ドキュメントやコード内の docstring を参照してください。必要であればサンプルスクリプトや .env.example のテンプレートも作成しますのでお知らせください。