KabuSys
======

日本株向けのデータプラットフォーム／自動売買支援ライブラリです。  
DuckDB をデータ層に使い、J-Quants や RSS / OpenAI（LLM）を組み合わせてデータ収集・品質チェック・特徴量生成・ニュース NLP・市場レジーム判定・監査ログ管理までを包括的に提供します。

主な目的
- 日次 ETL による株価・財務・マーケットカレンダーの差分取得と保存
- ニュースの収集と LLM を用いた銘柄センチメント評価（ai_score）
- マーケットレジーム判定（株価 MA とマクロニュースセンチメントの合成）
- 研究用のファクター計算・特徴量探索ユーティリティ
- 発注〜約定に至る監査ログ（監査テーブル）初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）

機能一覧
- config: 環境変数/.env の自動読み込みとアプリ設定（settings）
- data:
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（トークン刷新・ページネーション・レートリミット・保存関数）
  - news_collector: RSS 取得・前処理・raw_news 保存（SSRF対策・サイズ制限）
  - calendar_management: JPX カレンダー管理と営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats: zscore_normalize 等の統計ユーティリティ
  - audit: 監査ログテーブル定義と初期化（init_audit_schema / init_audit_db）
- ai:
  - news_nlp.score_news: RSSで収集したニュースを LLM に送り銘柄ごとのセンチメントを ai_scores に書込
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して market_regime に書込
- research:
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
- （高レイヤ）strategy / execution / monitoring などのための基盤（パッケージ公開インターフェース）

セットアップ手順（開発環境向け）
1. Python 環境
   - 推奨: Python 3.10+（コードは型ヒントと標準ライブラリの新機能を利用）
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - 依存リストファイルがない場合は最低限以下をインストールしてください:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   （実際のプロジェクトでは pyproject.toml / requirements.txt に合わせてください）
4. ソースをインストール（開発モード）
   - pip install -e .
   （この手順はパッケージ化されたリポジトリで有効です）

環境変数
- 自動読み込み:
  - パッケージロード時にプロジェクトルート（.git または pyproject.toml）を探索し、.env → .env.local の順で環境変数を読み込みます。
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 必須 / 主要な変数:
  - JQUANTS_REFRESH_TOKEN : J-Quants 用リフレッシュトークン（必須）
  - OPENAI_API_KEY        : OpenAI（LLM）APIキー（score_news / score_regime で使用）
  - KABU_API_PASSWORD     : kabu API パスワード（発注連携がある場合）
  - SLACK_BOT_TOKEN       : Slack 通知（使用する場合）
  - SLACK_CHANNEL_ID      : Slack 通知（使用する場合）
  - DUCKDB_PATH           : デフォルト: data/kabusys.duckdb
  - SQLITE_PATH           : デフォルト: data/monitoring.db
  - PID_FILE_PATH         : デフォルト: data/execution.pid
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT : 監視閾値
  - KABUSYS_ENV           : development / paper_trading / live
  - LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL

簡単な使い方（コード例）
- 基本: DuckDB 接続を作って ETL を回す
  from kabusys.config import settings
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=None)  # target_date を指定可能
  print(result.to_dict())

- news_nlp（ニューススコアリング）
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数で指定

- regime_detector（市場レジーム）
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI キーは env または api_key 引数で指定

- 監査ログ初期化
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")

- 研究用関数例
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  res = calc_momentum(conn, target_date=date(2026,3,20))

注意点 / 運用上のポイント
- Look-ahead バイアス対策:
  - 多くの関数は内部で datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る設計です。バックテストでは target_date を過去に固定して利用してください。
- OpenAI API:
  - score_news と regime_detector は OpenAI の JSON Mode を使いモデル（gpt-4o-mini）へプロンプトを送り、厳密な JSON を期待してパースしています。
  - API 呼び出しはリトライやフォールバックロジックを備えますが、API キーは必ず設定してください。
- J-Quants API:
  - トークンは refresh トークンから id_token を取得して使用します。_get_cached_token によるキャッシュと自動リフレッシュ機構があります。
  - レートリミット（120 req/min）を考慮した RateLimiter を内蔵しています。
- RSS ニュース収集:
  - SSRF 対策・応答サイズ制限・XML パースに対する堅牢化（defusedxml）などの保護を行っています。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py               # 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py           # ニュースの LLM スコアリング
    - regime_detector.py    # マーケットレジーム判定
  - data/
    - __init__.py
    - pipeline.py           # ETL パイプライン（run_daily_etl 等）
    - etl.py                # ETL 公開インターフェース（ETLResult）
    - jquants_client.py     # J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py     # RSS 取得・前処理・保存
    - calendar_management.py# 市場カレンダー管理・営業日ロジック
    - quality.py            # 品質チェックモジュール
    - stats.py              # 統計ユーティリティ（zscore）
    - audit.py              # 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py    # モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py# 将来リターン / IC / 統計サマリー 等
  - （その他）
    - strategy/
    - execution/
    - monitoring/
      （上位レイヤはパッケージ公開インターフェースに含まれますが、詳細は実装参照）

ライセンス／貢献
- コードベースのライセンスや貢献方法はリポジトリルートの LICENSE / CONTRIBUTING を参照してください（本 README は実装から推測したものです。実際のファイルをプロジェクトに合わせて調整してください）。

トラブルシューティング
- .env 自動読み込みを行っているため、意図せず環境変数が読み込まれる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動で読み込んでください。
- OpenAI レスポンスのパース失敗や API エラー時はフェイルセーフでゼロ値（中立）にフォールバックする実装が多くあります。ログをチェックして問題の切り分けを行ってください。
- DuckDB へ書き込み中にエラーが発生した場合、該当処理はトランザクション制御（BEGIN/COMMIT/ROLLBACK）を行っている関数とそうでない関数があるため、ログとスタックトレースを参照してください。

以上。プロジェクトの利用・拡張にあたっては、各モジュールの docstring（ソースコード）を参照すると実装の詳細や設計意図が記載されています。必要であれば README の英語版や各モジュールの使用例を追加で作成します。