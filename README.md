# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリ。  
J-Quants / RSS / OpenAI（LLM）等を利用してデータ収集・品質チェック・特徴量生成・ニュースセンチメント評価・市場レジーム判定・監査ログ管理などを行うコンポーネント群を提供します。

※ 本リポジトリはライブラリ的に設計されており、実際の発注ロジック（実際の売買を行うブローカー接続）は別実装を想定しています。

---

## 主な機能

- データ取得（J-Quants API）
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPXマーケットカレンダー
  - ページネーション・レートリミット・トークン自動リフレッシュ・リトライ付き
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL 実行エントリポイント（run_daily_etl）
- ニュース収集
  - RSS 取得、URL 正規化、SSRF 対策、前処理、raw_news への冪等保存（記事IDは正規化URLのハッシュ）
- ニュース NLP / LLM スコアリング
  - 銘柄ごとのセンチメント（gpt-4o-mini）を ai_scores テーブルへ保存（score_news）
  - マクロニュース + ETF(1321) の 200 日移動平均乖離を合成して市場レジーム判定（score_regime）
- リサーチ用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ、Zスコア正規化
- 監査ログ（監査テーブル）
  - signal_events / order_requests / executions テーブルとインデックスを作成・初期化する関数（init_audit_db / init_audit_schema）
  - 発注フローのトレーサビリティを確保する設計
- 設定管理
  - .env（プロジェクトルート）自動読み込み（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
  - settings から環境変数を型付きで参照（例: settings.jquants_refresh_token）

---

## 必要な環境変数（主なもの）

以下はライブラリ内で参照される主要環境変数の一覧です。プロジェクトルートに `.env` を置くことで自動で読み込まれます（ただしプロジェクトルートは .git または pyproject.toml を探索して決定されます）。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime のデフォルト）
- KABU_API_PASSWORD: kabuステーション等のパスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

.env の自動読み込みを無効化したい場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順（例）

1. リポジトリをクローン / ローカルに配置

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要ライブラリ（代表例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれを利用してください。）

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、OS 環境変数として設定
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     KABU_API_PASSWORD=secret
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

5. DuckDB / 監査 DB 初期化（必要に応じて）
   - Python REPL やスクリプトで:
     from kabusys.config import settings
     import duckdb
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db(str(settings.duckdb_path))  # 監査専用 DB を初期化して接続を返す
   - あるいは既存のデータベースにテーブルを追加する:
     conn = duckdb.connect(str(settings.duckdb_path))
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)

---

## 使い方（簡単な例）

- DuckDB 接続を作る例:
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する:
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定しなければ今日（設定された環境に依存）

- ニュースセンチメントを生成して ai_scores に書き込む:
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  written = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI キーは env の OPENAI_API_KEY を使用

- 市場レジームを判定して market_regime に保存:
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20))

- ファクター（モメンタム等）を計算:
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  mom = calc_momentum(conn, date(2026, 3, 20))

- ニュース RSS を取得する（ニュース収集）:
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")

- 設定参照:
  from kabusys.config import settings
  settings.log_level, settings.is_live など

注意:
- score_news / score_regime は OpenAI を利用するためコストが発生します。API キーの管理に注意してください。
- 多くの関数は DuckDB 接続を引数に取り、テーブルを読み書きします。事前にスキーマ（テーブル）を用意する必要があります。
- ライブラリはルックアヘッドバイアス防止のために内部で date.today() を直接参照しない設計が意識されています（target_date を明示的に渡すことが推奨）。

---

## 主要モジュール・ディレクトリ構成

概観（src/kabusys 配下）:

- kabusys/
  - __init__.py (バージョン情報)
  - config.py
    - 環境変数読み込みと settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py
      - score_news(conn, target_date, api_key=None): 銘柄別ニュースセンチメントを ai_scores に保存
    - regime_detector.py
      - score_regime(conn, target_date, api_key=None): ETF(1321) MA200 とマクロニュースを合成して market_regime に書き込み
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch/ save 関数群）
    - pipeline.py
      - ETL の主要実装（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
      - ETLResult クラス
    - etl.py
      - ETLResult を再エクスポート
    - news_collector.py
      - RSS 取得・前処理・安全対策（SSRF 等）
    - calendar_management.py
      - JPX カレンダー・営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック (欠損 / スパイク / 重複 / 日付整合性)
    - audit.py
      - 監査テーブル定義・初期化（signal_events / order_requests / executions）
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum, calc_value, calc_volatility
    - feature_exploration.py
      - calc_forward_returns, calc_ic, factor_summary, rank

---

## 実運用上の注意・設計上のポイント

- 環境変数・シークレットの管理は厳重に行ってください（.env はバージョン管理しない等）。
- OpenAI/API 呼び出しにはリトライやフェイルセーフが組み込まれているが、コストやレート制限を考慮した運用・監視が必要です。
- ETL と品質チェックは分離されており、品質問題が検出されても ETL 自体は継続する設計です（呼び出し元で判断してください）。
- DuckDB のバージョン依存（executemany の挙動等）に注意してください。コード内で互換性対策が施されていますが、実環境では検証を推奨します。
- news_collector は RSS を扱い、SSRF・サイズ・XML 攻撃等の対策を多数実装しています。外部フィードの追加時も同様の安全設計を守ってください。
- ライブラリはバックテスト等でのルックアヘッドバイアスを避ける方針で設計されています（target_date を明示する、取得ウィンドウは排他条件など）。

---

## 参考（小さなコードスニペット）

- ETL をスクリプトで回す最小例:
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- OpenAI キーを関数呼び出しで直接渡す例:
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  written = score_news(conn, date(2026,3,20), api_key="sk-...")

---

README は以上です。必要であれば、セットアップ手順の詳細化（requirements.txt / pyproject.toml の記載例、DuckDB スキーマ初期化 SQL、運用監視手順など）を追加で作成します。どの部分を詳しく書きたいか教えてください。