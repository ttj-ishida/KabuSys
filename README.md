KabuSys
=======

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
本リポジトリはデータ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログなどを統合して提供します。

主な目的
- J-Quants からの株価・財務・カレンダーデータの差分取得と DuckDB への保存（冪等）
- RSS ベースのニュース収集とニュース単位・銘柄単位の前処理
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント付与（銘柄ごと / マクロ）
- 日次 ETL パイプラインとデータ品質チェック
- 研究用途のファクター計算・IC / フォワードリターン解析
- 発注フローの監査ログ（監査テーブル定義・初期化）

機能一覧
- 環境設定管理（.env の自動読み込み／settings API）
- J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- 市場カレンダー管理（営業日判定・next/prev_trading_day 等）
- ニュース収集（RSS, URL 正規化, SSRF 対策, gzip/サイズ制限）
- ニュース NLP（銘柄別センチメント -> ai_scores テーブルへ保存）
- マクロ＋価格指標による市場レジーム判定（score_regime）
- 研究用モジュール（モメンタム／バリュー／ボラティリティ計算、forward returns, IC, 統計サマリー）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ生成・監査DB初期化（signal_events / order_requests / executions）
- DuckDB を想定した SQL 実装（インメモリやファイル DB に対応）

セットアップ手順（開発環境）
1. Python インタプリタの用意（推奨: 3.10+）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - requirements.txt がない場合は最低限以下を入れてください:
     - duckdb
     - openai
     - defusedxml
     - （その他、ロギング用途や HTTP 標準ライブラリのみで動く実装）
   例:
     pip install duckdb openai defusedxml
4. パッケージをインストール（開発）
   - pip install -e .
     （プロジェクトをパッケージとして使う場合）
5. 環境変数の設定
   - プロジェクトルートに .env を置くと自動読み込みされます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN  (J-Quants リフレッシュトークン)
     - KABU_API_PASSWORD       (kabuステーション用パスワード、必要時)
     - SLACK_BOT_TOKEN         (Slack 通知を使う場合)
     - SLACK_CHANNEL_ID        (Slack チャンネルID)
     - OPENAI_API_KEY          (OpenAI を使う処理を行う場合)
   - 任意（デフォルトあり）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト INFO
     - KABU_API_BASE_URL — デフォルト http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db
   - 簡単な .env 例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

使い方（主要 API の例）
- 設定を参照する
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path

- DuckDB 接続（ファイル DB）
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL の実行
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアの付与（OpenAI キーが必要）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} symbols")

- 市場レジーム判定（OpenAI キーが必要）
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査 DB の初期化（監査専用 DB を作成）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

- 研究用関数の呼び出し例
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  records = calc_momentum(conn, target_date=date(2026, 3, 20))

注意点 / 実運用上の留意事項
- OpenAI 呼び出しは API 料金が発生します。テスト時はモック化することを推奨します（コード中で _call_openai_api を patch 可能）。
- J-Quants API はレート制限があり、本クライアントは固定間隔レート制御とリトライを実装しています。ID トークンは自動リフレッシュされます。
- ETL / 研究処理はルックアヘッドバイアスを避ける設計になっています（内部で datetime.today()/date.today() を安易に参照しない等）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）基準で行われます。テスト時など自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB executemany は空リストを受け付けないバージョンの挙動に対応するため各所で空チェックがあります。

ディレクトリ構成（主なファイルと簡単な説明）
- src/kabusys/
  - __init__.py  -- パッケージ情報（バージョンなど）
  - config.py    -- 環境変数 / 設定管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py        -- ニュースを銘柄ごとに集約して OpenAI でスコアリング
    - regime_detector.py -- ETF MA とマクロニュースを合成して市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - etl.py                 -- ETLResult の再エクスポート
    - jquants_client.py      -- J-Quants API クライアント（fetch/save）
    - news_collector.py      -- RSS 収集・前処理・raw_news 保存
    - calendar_management.py -- 市場カレンダー管理（営業日判定・更新ジョブ）
    - stats.py               -- zscore_normalize 等の統計ユーティリティ
    - quality.py             -- データ品質チェック（欠損・スパイク等）
    - audit.py               -- 監査ログテーブル定義と初期化関数
  - research/
    - __init__.py
    - factor_research.py     -- Momentum / Value / Volatility / Liquidity 計算
    - feature_exploration.py -- forward returns, IC, factor summary, rank
  - monitoring/ (README では省略。監視用 DB/ロギング等を想定)
  - strategy/  (戦略定義・シグナル生成は別途実装想定)
  - execution/ (発注ロジックは別途実装想定)

開発・テスト
- OpenAI や J-Quants など外部 API 呼び出しがある箇所はユニットテストでモックして実行してください。特に news_nlp._call_openai_api / regime_detector._call_openai_api はテスト用に差し替え可能です。
- 自動環境変数読み込みがテストに影響する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化できます。

ライセンス / 責任
- 本 README ではライセンス記載がありません。実運用・公開時は適切なライセンスを付与してください。
- 市場参加・実取引に使用する場合は十分な検証とリスク管理を行ってください（本コードは参考実装であり、注文実行や資金管理は使用者の責任です）。

補足
- さらに詳細なドキュメント（DataPlatform.md / StrategyModel.md 等）が想定されています。本コード内の docstring やモジュール冒頭コメントが実装意図を説明しているので参照してください。

---  
質問や README に追加してほしい項目（例: サンプル .env.example、requirements.txt の具体的な内容、CI/デプロイ手順など）があれば教えてください。