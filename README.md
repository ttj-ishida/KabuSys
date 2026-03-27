# KabuSys

KabuSys は日本株向けの自動売買／データ基盤ライブラリです。  
J-Quants や各種ニュースソースからデータを取得・整形し、DuckDB をバックエンドにして ETL、品質チェック、ファクター／リサーチ、AI（LLM）によるニュース解析、監査ログ（発注〜約定トレース）を提供します。

主な設計方針として、バックテストでのルックアヘッドバイアスを避けるために「現在日時を直接参照しない」実装や、API 呼び出し時の堅牢なリトライ・フォールバック処理、DuckDB への冪等保存（ON CONFLICT）などを採用しています。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（例）
- ディレクトリ構成
- 環境変数（主な設定）
- 開発・テスト時のヒント

---

プロジェクト概要
- 日本株データの ETL（J-Quants 経由）、ニュース収集、データ品質チェックを行う DataPlatform コンポーネント。
- ニュースを LLM（OpenAI）で解析して銘柄ごとのセンチメントを計算（news_nlp）。
- ETF とマクロニュースを合成して市場レジーム（bull / neutral / bear）を判定する機能（regime_detector）。
- 研究用のファクター計算・特徴量探索ユーティリティ（research）。
- 発注〜約定までをトレースする監査ログ（audit）スキーマと初期化ユーティリティ。
- DuckDB を主なデータストアとして想定。

機能一覧
- Data/ETL
  - 差分 ETL（株価日足 / 財務 / 市場カレンダー）: data.pipeline.run_daily_etl 等
  - J-Quants API クライアント（認証・ページネーション・レート制御・リトライ内蔵）
  - market_calendar の更新ジョブ / 営業日判定ユーティリティ（next_trading_day 等）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
- News
  - RSS 収集（SSRF 対策 / URL 正規化 / トラッキングパラメータ除去）
  - raw_news の保存・news_symbols 連携
- AI / LLM
  - ニュースセンチメントのバッチ解析（gpt-4o-mini を想定）: kabusys.ai.news_nlp.score_news
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）: kabusys.ai.regime_detector.score_regime
  - レスポンス検証 / 再試行 / フォールバック実装
- Research
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Spearman）や統計サマリー
  - Z スコア正規化ユーティリティ
- Audit（監査）
  - signal_events / order_requests / executions 等のスキーマ定義と初期化（init_audit_schema / init_audit_db）
  - 監査目的のインデックスや制約を含む冪等初期化

---

セットアップ手順（ローカル / 開発用）
1. リポジトリをクローン／チェックアウトしてください。

2. Python 環境を準備（推奨: venv）
   - 例:
     python -m venv .venv
     source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 最低限の依存例:
     pip install duckdb openai defusedxml
   - 実運用では logging, requests 等の追加やバージョン固定を行ってください。

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から .env/.env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime でも api_key パラメータで直接渡せます）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: （監視/通知がある場合）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（注文・接続関連）
   - 任意
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

   - .env のパースはシェル風の export KEY=VAL、クォート対応、コメント対応などに対応しています。

5. DuckDB 用ディレクトリを作成（必要に応じて）
   - README の例では data/ を使用しているため作成しておくと良いです:
     mkdir -p data

---

簡単な使い方（Python 例）
- 共通 preliminaries:
  from datetime import date
  import duckdb
  from kabusys.config import settings

- ETL（日次 ETL を実行）
  conn = duckdb.connect(str(settings.duckdb_path))
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントを計算して ai_scores に保存
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY が環境変数にあれば api_key=None で動きます
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"Written {n_written} scores")

- 市場レジームを判定して market_regime テーブルへ保存
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect(str(settings.duckdb_path))
  # api_key を明示的に渡すことも可能
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログ DB を初期化
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db(settings.duckdb_path)  # 指定パスに DuckDB を作成しスキーマ初期化

- ETL 内で J-Quants API を直接使う（トークンは settings.jquants_refresh_token による自動取得）
  from kabusys.data import jquants_client as jq
  records = jq.fetch_listed_info(date_=date(2026,3,1))
  print(len(records))

注意点（使用時）
- OpenAI 呼び出しは外部 API なのでレートやコストに注意してください。score_news / score_regime ではリトライや失敗時のフォールバック（スコア 0.0）を実装していますが、不要な実行は避けてください。
- run_daily_etl 等はローカルの DuckDB 接続を受け取り、内部で BEGIN/COMMIT を使う箇所があります。既にトランザクション中の接続で DDL を transactional に実行すると挙動が変わることに注意してください（DuckDB のトランザクション制約）。
- ETL の差分ロジックは最終取得日をベースに再取得（バックフィル）する仕様です。最初に初期ロードを行う場合は _MIN_DATA_DATE（2017-01-01）から取得されます。

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py                  : 環境変数・設定管理（.env 自動読み込み含む）
  - ai/
    - __init__.py
    - news_nlp.py              : ニュースセンチメント解析（score_news）
    - regime_detector.py      : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py        : J-Quants API クライアント + DuckDB への保存関数
    - pipeline.py              : ETL パイプライン（run_daily_etl 等）
    - etl.py                   : ETL の型再エクスポート（ETLResult）
    - news_collector.py        : RSS フィード収集・前処理
    - calendar_management.py   : 市場カレンダー管理 / 営業日判定
    - quality.py               : データ品質チェック（欠損・スパイク・重複・日付整合性）
    - stats.py                 : 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                 : 監査ログスキーマ（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py       : ファクター計算（momentum/value/volatility）
    - feature_exploration.py   : 将来リターン・IC・統計サマリー
  - ai/、data/、research/ はそれぞれ公開 API を __init__.py で制御しています。

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須) : J-Quants 用リフレッシュトークン
- OPENAI_API_KEY (必須 for LLM 実行) : OpenAI API キー
- KABU_API_PASSWORD (必須 for kabu API)
- KABU_API_BASE_URL (任意) : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (任意) : Slack 通知用
- DUCKDB_PATH (任意) : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意) : 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV : development | paper_trading | live（デフォルト development）
- LOG_LEVEL : ログレベル（INFO 等）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 : .env 自動読み込みを無効化

開発・テスト時のヒント
- テスト等で .env 自動読み込みを無効にしたい場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しや外部ネットワーク呼び出しはモックしやすい設計（内部の _call_openai_api / _urlopen 等を patch してテスト可能）。
- DuckDB をインメモリで使いたい場合は ":memory:" を init_audit_db に渡せます。
- news_collector.fetch_rss は SSRF やサイズ攻撃対策を組み込んでいるため、外部環境での動作に注意（User-Agent / gzip 対応、最大サイズなど）。

ライセンス・貢献
- （このリポジトリ固有の LICENSE 情報が無い場合はプロジェクトのポリシーに従ってください）

---

必要であれば、README に「CI 実行例」「cron による日次 ETL 実行」「監視・Slack 通知の設定方法」「デプロイ手順（paper/live）」などの追加セクションも作成できます。どの内容を詳しく載せたいか教えてください。