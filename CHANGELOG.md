CHANGELOG
=========

All notable changes to this project will be documented in this file.

このプロジェクトの重要な変更点はすべてこのファイルに記載します。
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

[Unreleased]
------------

- （現時点のソースは初期リリース相当の内容を含みます。リリース予定の差分がある場合はここに記載します）

[0.1.0] - 2026-03-29
--------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)
  - パッケージメタ:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
    - パッケージの公開サブモジュールを __all__ で定義（data, strategy, execution, monitoring）。

- 環境変数・設定管理
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
    - 自動ロード: プロジェクトルート（.git または pyproject.toml を基準）を検出して .env / .env.local を順に読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサーを実装（export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理などに対応）。
    - .env.local の読み込みは override=True（OS 環境変数は保護）。既存 OS 環境変数を保護するため protected set を使用。
    - Settings による必須取得 (例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID) とデフォルト値（KABU_API_BASE_URL, DB パス等）を提供。
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）とユーティリティプロパティ（is_live / is_paper / is_dev）。

- AI（ニュースNLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約して銘柄ごとのニュースを抽出。
    - OpenAI (gpt-4o-mini, JSON Mode) を用いたバッチセンチメント評価を実装（最大 _BATCH_SIZE=20 銘柄/呼び出し）。
    - 時間ウィンドウ計算（JST ベースの前日 15:00 ～ 当日 08:30 相当を UTC に変換）を calc_news_window で提供。
    - 入力トリム（最大記事数・最大文字数）やレスポンス検証（JSON 抽出、results リスト、code/score 検証、数値チェック）を実装。
    - API エラー（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフとリトライを実装。失敗時はスキップして継続（フェイルセーフ）。
    - DuckDB 互換性考慮（executemany に空リストを渡さない等）および idempotent な DB 書込み（DELETE → INSERT）。
    - テスト容易性: OpenAI 呼び出し部分は _call_openai_api を patch で差し替え可能。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - calc_news_window を用いてマクロニュースのウィンドウを取得し、最大 _MAX_MACRO_ARTICLES 件を LLM に渡して macro_sentiment を算出。
    - LLM 呼び出しは独立実装（news_nlp と共有しない）で、API 失敗時は macro_sentiment=0.0 として継続。
    - レジームスコア算出後、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - ルックアヘッドバイアス防止設計（date 引数を使用し、datetime.today()/date.today() を参照しない）。

- データ（ETL / カレンダー等）
  - src/kabusys/data/pipeline.py
    - ETLResult データクラスを実装（ETL の取得数・保存数・品質問題・エラー等を集約）。
    - 差分取得、backfill（日数による再取得）、品質チェックのための基本ユーティリティ群を実装。
    - DuckDB の最大日付取得やテーブル存在チェックを提供。
    - エラーと品質検出結果を集約して to_dict でシリアライズ可能。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を公開インターフェースとして再エクスポート。
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダー管理（market_calendar テーブルの参照・更新、JPX/J-Quants からの差分取得ジョブ）を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の営業日判定ユーティリティを提供。
    - DB 登録値を優先しつつ、未登録日は曜日ベースでフォールバックする一貫したロジックを採用。
    - calendar_update_job により J-Quants から差分フェッチと保存を実行。バックフィル・健全性チェックを実装。

- Research（因子計算・特徴探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials を用いて計算する関数群を実装。
    - 計算は SQL ウィンドウ関数を活用して効率化。データ不足時の None 処理を明確化。
  - src/kabusys/research/feature_exploration.py
    - 将来リターンの計算（任意ホライズン） calc_forward_returns を実装。
    - ランク相関（Spearman の ρ）を用いた IC 計算 calc_ic、ランク変換ユーティリティ rank、ファクター統計 summary 関数 factor_summary を実装。
    - pandas 等外部ライブラリに依存しない純 Python 実装。

Changed
- N/A（初回リリースのため「追加」が主体）

Fixed
- N/A（初回リリース）

Security
- OpenAI API キーは引数から注入可能（api_key）か環境変数 OPENAI_API_KEY を使用。キー未指定時は明示的な ValueError を発生させて安全性を確保。

Notes / Implementation details（重要な設計・運用上の注意）
- ルックアヘッドバイアス防止:
  - AI モジュールと Research モジュールは内部で datetime.today()/date.today() を直接参照せず、必ず target_date を引数として受け取る設計です。運用時に意図しない将来データ参照が行われないよう配慮しています。
- フェイルセーフ設計:
  - OpenAI API の失敗時には例外をそのまま上げず、該当部分を 0.0 やスキップで補う設計を採用（ログを残す）。これにより一部 API 失敗でもパイプライン全体が停止しないようにしています。
- テスト容易性:
  - news_nlp と regime_detector の OpenAI 呼び出しは内部関数（_call_openai_api）を通すため、unittest.mock.patch で差し替え可能です。
- DuckDB 互換性:
  - DuckDB の executemany が空リストを受け取れない点や、list バインドの互換性に注意した実装（個別 DELETE の executemany）としています。
- .env パーシングの挙動:
  - export プレフィックス、クォート内エスケープ、インラインコメントの扱い（クォート有無での挙動差）、および .env.local が .env を上書きする際に OS 環境変数を保護する仕組みを実装しています。
- デフォルトパス:
  - duckdb: data/kabusys.duckdb
  - sqlite: data/monitoring.db
  - これらは環境変数で上書き可能（DUCKDB_PATH, SQLITE_PATH）。

Known limitations / TODO
- 一部の財務指標（PBR・配当利回りなど）は未実装（calc_value の注記参照）。
- 外部 API 呼び出し（J-Quants, OpenAI）のレート制限・課金に留意して運用すること。
- news_nlp の出力フォーマットは LLM に依存するため、将来的なモデル差異に備えた更なる堅牢化が必要かもしれません。

References
- ドキュメントや実装上の設計意図は各モジュールの docstring に記載しています。実運用前に該当 docstring を参照してください。