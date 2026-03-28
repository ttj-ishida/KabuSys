# KabuSys

日本株向け自動売買／データプラットフォーム用のライブラリ群です。  
データ取得（J-Quants）、ニュース収集・NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、ETL、監査ログ（DuckDB）などを提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- 必要要件
- セットアップ手順
- 環境変数（.env）
- 使い方（簡易サンプル）
- ディレクトリ構成（主要ファイル説明）
- 開発メモ / 注意点

---

プロジェクト概要
- 日本株自動売買システム（バックエンド・データ基盤・研究ツール群）を構成するモジュール群。
- データ取得（J-Quants）→ ETL → 品質チェック → 特徴量計算 → シグナル生成 → 監査ログ（発注/約定追跡）までのワークフローを想定。
- ニュースを収集して OpenAI (gpt-4o-mini 等) で銘柄/マクロのセンチメント評価を行う機能を備える。

主な機能一覧
- 環境設定管理（自動 .env ロード、必須チェック）: kabusys.config
- J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ・ページネーション）: kabusys.data.jquants_client
- ETL パイプライン（差分取得、保存、品質チェック）: kabusys.data.pipeline / kabusys.data.etl
- データ品質チェック（欠損・重複・スパイク・日付不整合）: kabusys.data.quality
- 市場カレンダー管理（営業日判定、バッチ更新）: kabusys.data.calendar_management
- ニュース収集（RSS -> raw_news、SSRF/サイズ制限/前処理）: kabusys.data.news_collector
- ニュース NLP（銘柄別センチメントを OpenAI で算出）: kabusys.ai.news_nlp
- 市場レジーム判定（ETF 1321 の MA とマクロセンチメント合成）: kabusys.ai.regime_detector
- 研究用モジュール（ファクター計算・特徴量探索・正規化）: kabusys.research
- 監査ログ（signal / order_request / executions のスキーマ作成）: kabusys.data.audit
- 汎用統計ユーティリティ（Zスコアなど）: kabusys.data.stats

必要要件
- Python 3.10 以上（| 型注釈、PEP 604 の union 型表記を使用）
- 推奨依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリで HTTP や XML を扱う実装が多く含まれますが、実行環境に合わせて依存パッケージをインストールしてください。

セットアップ手順（例）
1. リポジトリをクローン
   - git clone ...（プロジェクトルートに .git または pyproject.toml があると .env 自動ロードが有効になります）

2. 仮想環境作成・アクティベート
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください）

4. 環境変数（.env）を準備
   - プロジェクトルートに .env を置くと自動で読み込まれます（OS 環境変数が優先、.env.local は .env を上書き）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

環境変数（主なキー）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API 用パスワード
- KABU_API_BASE_URL (任意): デフォルト http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須): Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須): Slack チャネル ID
- OPENAI_API_KEY: OpenAI 呼び出しに使用（score_news, score_regime の api_key 引数で上書き可能）
- DUCKDB_PATH (任意): デフォルト data/kabusys.duckdb
- SQLITE_PATH (任意): デフォルト data/monitoring.db
- KABUSYS_ENV (任意): development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意): DEBUG, INFO, WARNING, ERROR, CRITICAL

.env の自動読み込みについて
- パッケージの config モジュールはプロジェクトルート（.git または pyproject.toml）を起点に .env → .env.local を読み込みます。
- OS 環境変数が常に優先されます。
- テストなどで自動ロードを抑制するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（簡単なサンプル）
- DuckDB 接続を作り ETL を実行する（日次ETL）
  - Python 例:
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースセンチメント（銘柄別）を生成する
  - score_news を使用（OpenAI APIキー必要）
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026,3,20))
    print("書き込み銘柄数:", n_written)

- 市場レジームを判定して保存する
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20), api_key="YOUR_OPENAI_KEY")

- 監査ログ DB を初期化する（監査専用）
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # conn 上でテーブルが作成されます

主な API（関数）リスト（抜粋）
- kabusys.config.settings: 設定アクセス（settings.jquants_refresh_token 等）
- kabusys.data.jquants_client:
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - save_daily_quotes(conn, records)
  - fetch_market_calendar(...)
  - save_market_calendar(conn, records)
- kabusys.data.pipeline:
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl(...), run_financials_etl(...), run_calendar_etl(...)
- kabusys.data.quality:
  - run_all_checks(conn, target_date=..., ...)
- kabusys.data.news_collector:
  - fetch_rss(url, source, timeout=30) など
- kabusys.ai.news_nlp:
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector:
  - score_regime(conn, target_date, api_key=None)
- kabusys.data.audit:
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

ディレクトリ構成（主要ファイルの説明）
- src/kabusys/__init__.py
  - パッケージ公開情報（__version__ 等）
- src/kabusys/config.py
  - 環境変数読み込み・Settings クラス（必須キー取得・検証）
- src/kabusys/data/
  - jquants_client.py: J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py: ETL パイプライン（run_daily_etl 等）
  - etl.py: ETL の公開インターフェース（ETLResult 再エクスポート）
  - news_collector.py: RSS 取得・正規化・SSRF対策・raw_news 保存ユーティリティ
  - calendar_management.py: 市場カレンダー管理、営業日判定ロジック
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - audit.py: 監査ログスキーマ初期化・init_audit_db 等
- src/kabusys/ai/
  - news_nlp.py: 銘柄別ニュースセンチメント算出（OpenAI 呼び出し・バッチ処理）
  - regime_detector.py: ETF MA とマクロセンチメントを合成して市場レジーム判定
- src/kabusys/research/
  - factor_research.py: Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py: forward returns, IC, rank, factor_summary
  - __init__.py: 便利関数の再エクスポート
- その他:
  - data/ 以下にデフォルト DB ファイル（duckdb, sqlite）を配置することを想定

開発メモ / 注意点
- Look-ahead バイアス回避:
  - 多くの関数で datetime.today() / date.today() を内部で参照せず、引数で target_date を受け取る設計です。バックテスト・研究用途ではこれを守って使用してください。
- .env 自動ロード:
  - プロジェクトルートの検出は .git / pyproject.toml を基準にしています。パッケージ配布後に動作させる場合は注意してください。
- OpenAI の呼出し:
  - news_nlp / regime_detector は gpt-4o-mini を想定し JSON Mode を使用します。API 障害時はフォールバックするロジック（スコア=0 等）が実装されていますが、APIキー設定やレート管理には注意してください。
- DuckDB 互換性:
  - 一部実装は DuckDB のバージョンに依存する細かい挙動（executemany の空リスト不可、ANY バインドの挙動等）を考慮しています。DuckDB のバージョン差異に注意してください。

---

貢献
- バグ報告や改善提案は Issue を立ててください。
- 新機能はまず Issue で相談の上、Pull Request をお願いします。

---

以上。必要に応じて README に実行コマンド例、.env.example のテンプレート、requirements.txt などを追加できます。どの形式（詳細な手順、テンプレートファイル等）を優先して出力しますか？