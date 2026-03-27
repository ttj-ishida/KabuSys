Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは "Keep a Changelog" のガイドラインに従っています。

Unreleased
----------

（現在なし）

0.1.0 - 2026-03-27
-----------------

Added
- パッケージ初期リリース。
  - パッケージ名: kabusys、バージョン: 0.1.0
  - src/kabusys/__init__.py による公開: data, strategy, execution, monitoring（strategy/execution/monitoring は公開インターフェースの一部として確保）

- 設定・環境変数管理
  - src/kabusys/config.py を追加。
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を起点）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - export KEY=val 形式やシングル/ダブルクォート、エスケープに対応した堅牢な .env パーサを実装。
    - OS 環境変数を保護するための protected 上書き制御を実装（.env.local は上書き、.env は上書きしない既定動作）。
    - 必須設定取得ヘルパー (_require) と Settings クラスを提供。主なプロパティ:
      - jquants_refresh_token (JQUANTS_REFRESH_TOKEN 必須)
      - kabu_api_password (KABU_API_PASSWORD 必須)
      - kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
      - slack_bot_token / slack_channel_id (必須)
      - duckdb_path / sqlite_path（デフォルトパスを提供）
      - env / log_level の値検証（許容値チェック）
      - is_live / is_paper / is_dev のユーティリティプロパティ

- AI（ニュース NLP / レジーム検出）
  - src/kabusys/ai/news_nlp.py を追加。
    - raw_news / news_symbols を集約して銘柄ごとのニュースを OpenAI（gpt-4o-mini）へ送信してセンチメントを算出。
    - JSON Mode を利用し厳格なレスポンスバリデーションを実施（results 配列、code/score のチェック）。
    - バッチ処理（最大 20 銘柄／チャンク）、1銘柄あたりの最大記事数・文字数によるトリムを実装。
    - レート制限 (429)、ネットワーク断、タイムアウト、5xx に対する指数バックオフリトライ。
    - スコアは ±1.0 にクリップ。部分失敗時の DB 保護（対象コードのみ DELETE → INSERT）を実装。
    - calc_news_window(target_date) により JST ベースのニュースウィンドウ（前日 15:00 ～ 当日 08:30）を UTC naive datetime で返す。
    - score_news(conn, target_date, api_key=None) を公開。api_key 未指定時は OPENAI_API_KEY 環境変数を参照し、未設定なら ValueError を送出。

  - src/kabusys/ai/regime_detector.py を追加。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照して ma200_ratio を計算、マクロキーワードでニュースを抽出し LLM（gpt-4o-mini）で macro_sentiment を算出。
    - API エラー時はフェイルセーフで macro_sentiment = 0.0 を採用。
    - レジームデータを market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。score_regime(conn, target_date, api_key=None) を公開。
    - OpenAI 呼び出しに対するリトライ/バックオフを実装。

- Data（ETL / カレンダー）
  - src/kabusys/data/pipeline.py を追加。
    - ETL の結果を表現する ETLResult dataclass を導入（取得数・保存数・品質問題・エラーの集約）。
    - テーブル存在チェック、最大日付取得などのヘルパーを実装。
    - 差分更新・backfill・品質チェックの設計方針を反映（J-Quants クライアント経由での差分取得を想定）。

  - src/kabusys/data/etl.py で ETLResult を再エクスポート。

  - src/kabusys/data/calendar_management.py を追加。
    - market_calendar テーブルを用いた営業日判定ロジックを実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB 登録がない日（または NULL）に対しては曜日ベース（土日非営業日）でフォールバックする一貫した挙動。
    - calendar_update_job(conn, lookahead_days=90) を実装し、J-Quants API から差分取得して market_calendar を冪等的に更新（バックフィル・健全性チェックを含む）。
    - 最大探索日数 (_MAX_SEARCH_DAYS) などの安全対策を実装。

- Research（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py を追加。
    - モメンタム（1m/3m/6m リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR、相対 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）を DuckDB 上で計算する関数を提供:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - 各関数は prices_daily / raw_financials を使用し、データ不足時は None を扱う。
    - 設計上、本番の発注 API などへアクセスしない（分析専用）。

  - src/kabusys/research/feature_exploration.py を追加。
    - 将来リターン算出 (calc_forward_returns)、IC（Information Coefficient）計算 (calc_ic)、ランク付けユーティリティ (rank)、ファクター統計サマリ (factor_summary) を実装。
    - calc_ic はスピアマンのランク相関を計算し、サンプルが不足する場合は None を返す。
    - pandas 等に依存せず標準ライブラリ + DuckDB で完結する設計。

- パッケージ公開/初期化
  - src/kabusys/ai/__init__.py および src/kabusys/research/__init__.py を追加し、主要関数をエクスポート。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / Migration
- OpenAI API の利用:
  - score_news / score_regime は OPENAI_API_KEY の設定（または api_key 引数の注入）を必須とする。未設定の場合 ValueError を送出。
  - モデルは gpt-4o-mini を前提とし、JSON Mode（response_format）での利用を想定している。
- データベース（DuckDB）の想定テーブル:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar などを利用。
- .env 自動読み込み:
  - プロジェクトルートの判定はパッケージファイル位置を起点に行われるので、パッケージ配布後も安定して動作する設計。
  - 自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ルックアヘッドバイアス対策:
  - AI・リサーチ・ETL の各モジュールは内部で datetime.today()/date.today() を直接参照しないように設計されています（外部から target_date を注入する方式）。これにより過去情報のみで評価することが保証されています。

Acknowledgements
- 初回リリース。

---
（この CHANGELOG はソースコードの実装とドキュメント文字列から推測して作成しています。実際のリリースノートとして採用する際は、実際のコミットや変更履歴と照合してください。）