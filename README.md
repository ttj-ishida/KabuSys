KabuSys — 日本株自動売買 / データプラットフォーム
概要
- KabuSys は日本株向けのデータパイプライン・リサーチ・AI（ニュースNLP）・監査ログ・市場レジーム判定・ETL を備えたライブラリ群です。  
- DuckDB をデータストアとして使い、J-Quants API から株価・財務・カレンダーを取得、ニュースは RSS から収集して OpenAI（gpt-4o-mini）でセンチメント評価を行う設計になっています。  
- バックテストや研究用途のファクター計算、品質チェック（quality）、監査ログ（audit）や発注周りの構成要素も含みます。

主な機能
- データ取得 / ETL
  - J-Quants から株価（日足）、財務、JPX マーケットカレンダーを差分取得・保存（ETL パイプライン）  
  - run_daily_etl による日次一括 ETL（カレンダー→株価→財務→品質チェック）
- ニュース処理 / AI
  - RSS 収集（news_collector）と前処理（URL削除・正規化・SSRF対策）  
  - OpenAI を用いたニュース銘柄別センチメント（news_nlp.score_news）  
  - マクロニュース＋ETF（1321）MA200 乖離を合成した市場レジーム判定（regime_detector.score_regime）
- 研究 / ファクター
  - モメンタム / バリュー / ボラティリティ等のファクター計算（research.*）  
  - 将来リターン計算 / IC（Information Coefficient） / 統計サマリー
- 品質管理 / 監査
  - データ品質チェック（欠損・スパイク・重複・日付不整合）  
  - 監査ログスキーマの生成・初期化（audit.init_audit_schema / init_audit_db）
- クライアント実装
  - J-Quants クライアント（jquants_client）: レートリミット・リトライ・トークン自動更新・ページネーション対応

前提 / 必要環境
- Python 3.10+（PEP 604 の union 型などを使用）を推奨（3.11 推奨）。  
- 主な依存パッケージ（プロジェクトの requirements.txt がある想定）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス：J-Quants API、OpenAI、RSS ソース などへのアクセス権

セットアップ手順（ローカル開発）
1. リポジトリをクローン／チェックアウト
   - git clone ...
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクト配布で requirements.txt / pyproject.toml があればそちらを使用）
4. パッケージを編集可能インストール（任意）
   - pip install -e .

環境変数 / 設定
- .env 自動読み込み:
  - パッケージ import 時にプロジェクトルート（.git または pyproject.toml を探索）から .env を自動ロードします。読み込み順は OS 環境変数 > .env.local > .env（.env.local は上書き）。  
  - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 主要な環境変数（config.Settings で参照）
  - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
  - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
  - DUCKDB_PATH: デフォルトデータベース path（data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 sqlite path（data/monitoring.db）
  - PAPER_FILL_MODE: paper trading の fill モード（instant|partial|never|reject）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 sqlite path（data/paper_trading.db）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 監視関連
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視しきい値
  - KABUSYS_ENV: environment（development|paper_trading|live）
  - LOG_LEVEL: ログレベル（DEBUG, INFO, ...）
- サンプル .env（例）
  - JQUANTS_REFRESH_TOKEN=xxxxxxxx
  - OPENAI_API_KEY=sk-xxxxxxxx
  - DUCKDB_PATH=data/kabusys.duckdb
  - KABUSYS_ENV=development
  - LOG_LEVEL=INFO

基本的な使い方（コード例）
- DuckDB 接続を作り ETL を実行（run_daily_etl）
  - from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())
- ニューススコアの実行（OpenAI API キーが必要）
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect(str(settings.duckdb_path))
    count = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None→環境変数参照
    print(f"scored {count} codes")
- 市場レジーム判定
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026,3,20), api_key=None)
- 監査データベース初期化（監査ログ専用 DB）
  - from kabusys.data.audit import init_audit_db
    conn_audit = init_audit_db("data/audit.duckdb")
- J-Quants クライアントを直接利用してデータ取得（テストやプレロード）
  - from kabusys.data.jquants_client import fetch_listed_info, get_id_token
    token = get_id_token()  # settings.jquants_refresh_token を用いる
    infos = fetch_listed_info(id_token=token, date_=date(2026,3,20))

注意点 / 運用上のポイント
- Look-ahead bias 防止:
  - AI と ETL モジュールは内部で datetime.today()/date.today() をむやみに参照せず、呼び出し側が対象日を明示する設計です。バックテストでは target_date を意識して利用してください。
- OpenAI 呼び出し:
  - gpt-4o-mini を JSON mode（response_format={"type":"json_object"}）で呼び出す想定です。API エラー時はフォールバックを行う設計で例外を投げ落とさない箇所もありますが、API キーが必須の関数は未設定時に ValueError を送出します。
- .env パース仕様:
  - export KEY=val 形式に対応。引用符やエスケープ、行末コメントの扱いなどに配慮したパーサを実装しています。
- テスト時のフック:
  - news_nlp / regime_detector の OpenAI 呼び出し部分は内部関数を差し替え（patch）してテスト可能です（_call_openai_api をモック）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント（score_news）
    - regime_detector.py      — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント / 保存関数
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult エクスポート
    - news_collector.py       — RSS 収集・正規化
    - calendar_management.py  — マーケットカレンダー管理 / 営業日判定
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - quality.py              — データ品質チェック
    - audit.py                — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py      — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py  — forward returns / calc_ic / factor_summary / rank
  - ai and research modules import relevant data utilities
- その他: README（本ファイル）、pyproject.toml / requirements.txt（プロジェクトにあれば）

開発・デバッグ
- ログレベルは環境変数 LOG_LEVEL で制御できます。開発時は DEBUG に設定してください。  
- 自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして、テスト用に明示的に os.environ を操作してください。  
- OpenAI など外部 API はテストでモックすることを推奨します（モジュール内部に差し替えポイントあり）。

補足
- この README はコードベースの実装ドキュメントに基づく簡易ガイドです。運用や本番導入時は権限・ネットワーク・シークレット管理・監査要件に沿った追加設定（CI/CD、シークレットストア、監視、障害時のオペレーション）を行ってください。  

必要であれば、README に含めるサンプル .env.example、requirements.txt の候補、具体的な初期 SQL スキーマ（raw_prices 等）や実行スクリプトの例を作成します。どれを優先しましょうか？