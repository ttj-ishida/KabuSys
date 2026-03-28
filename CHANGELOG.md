CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは「Keep a Changelog」に準拠しています。  
このリポジトリの初回リリースとして以下の変更点を記載します。

[0.1.0] - 2026-03-28
-------------------

Added
- パッケージ初期リリースを追加
  - kabusys パッケージ初版を公開 (バージョン 0.1.0)。
  - パッケージメタ情報: __version__ = "0.1.0"、公開モジュール data/strategy/execution/monitoring を __all__ に指定。

- 環境設定管理 (kabusys.config)
  - .env/.env.local 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサはコメント、export プレフィックス、クォート／エスケープ対応を実装。
  - Settings クラスを導入し、環境変数をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development, paper_trading, live のいずれかを検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL を検証）
  - is_live / is_paper / is_dev のユーティリティプロパティを提供。

- AI モジュール (kabusys.ai)
  - ニュースセンチメント解析 (kabusys.ai.news_nlp)
    - raw_news / news_symbols から指定ウィンドウのニュースを集約し、OpenAI (gpt-4o-mini) を使って銘柄ごとのセンチメントを算出。
    - 時間ウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive datetime で扱う）。
    - バッチサイズ、文字数・記事数上限、JSON Mode 利用、厳格なレスポンスバリデーションを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフとリトライ。
    - レスポンスパースエラーや API 失敗はフェイルセーフでスキップ（例外を上げずに処理継続）。
    - DuckDB への書き込みは idempotent（DELETE → INSERT）で、部分失敗時に既存データを保護。
    - テスト用に _call_openai_api をパッチ可能に設計。
    - 公開関数: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
    - 公開関数: calc_news_window(target_date) → 対応するウィンドウを返す。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、ニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジームを判定（'bull' / 'neutral' / 'bear'）。
    - マクロセンチメント取得は gpt-4o-mini を JSON 出力で使用。記事がない場合は LLM 呼び出しをスキップして macro_sentiment=0.0。
    - API リトライ・フェイルセーフ戦略を実装。例外発生時は macro_sentiment=0.0 にフォールバックして継続。
    - レジーム計算式、閾値、重みは定数として明確化（MA 重み 0.7、マクロ重み 0.3、スケール等）。
    - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。
    - 公開関数: score_regime(conn, target_date, api_key=None) → 1（成功）を返す。

- Research モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離を計算。データ不足時は None を返す設計。
    - calc_volatility(conn, target_date): 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等を計算。必要行数未満は None として扱う。
    - calc_value(conn, target_date): raw_financials から最新財務を取得して PER/ROE を算出（EPS=0/欠損時は None）。
    - 設計上、DuckDB の prices_daily / raw_financials のみを参照し、本番発注等にアクセスしない。
  - 特徴量解析 (kabusys.research.feature_exploration)
    - calc_forward_returns(conn, target_date, horizons=None): 指定ホライズンの将来リターンを計算（horizons のバリデーションあり）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を計算。十分なデータがない場合は None。
    - rank(values): 同順位は平均ランクを返すランク付けユーティリティ（丸めで ties の安定化）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリー。
  - research パッケージの __all__ で主要関数を再エクスポート。

- Data モジュール (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を用いた営業日判定とユーティリティ:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB にデータがない場合は曜日ベースのフォールバック（土日を非営業日扱い）。
    - 最大探索範囲 (_MAX_SEARCH_DAYS) を設けて無限ループを防止。
    - calendar_update_job(conn, lookahead_days=90): J-Quants からカレンダーを差分取得して market_calendar を更新。バックフィルや健全性チェックを実装。
    - jquants_client からの fetch/save を呼び出し、例外はロギングして 0 を返すフェイルセーフ。
  - ETL パイプライン (kabusys.data.pipeline)
    - ETLResult dataclass を実装（取得件数・保存件数・品質問題・エラーリスト等を保持）。
    - 差分取得、バックフィル、品質チェック（kabusys.data.quality 連携）を想定した設計。
    - 内部ユーティリティ: テーブル存在チェック・最大日付取得など。
    - kabusys.data.etl で ETLResult を再エクスポート。

- その他
  - テスト容易性を考慮した設計点:
    - OpenAI 呼び出しを行う内部ヘルパー (kabusys.ai.news_nlp._call_openai_api / kabusys.ai.regime_detector._call_openai_api) はテスト時に patch して差し替え可能。
  - DuckDB を主要なデータストアとして利用することを前提に実装（関数引数で DuckDB 接続を受け取る設計）。

Changed
- 初回リリースのためなし。

Deprecated
- なし。

Removed
- なし。

Fixed
- 初回リリースのためなし。

Security
- 初回リリースのためなし。

注意 / 補足
- OpenAI の利用:
  - デフォルトのモデルは gpt-4o-mini。JSON Mode を利用して厳格な JSON 応答を期待するが、実運用では LLM の出力ばらつきに備えたパース耐性とフォールバックを実装。
  - API キーは関数引数で注入可能。引数未指定時は環境変数 OPENAI_API_KEY を参照する。
- 環境変数の取り扱い:
  - 必須環境変数が未設定の場合は ValueError を送出する箇所がある（例: score_news / score_regime / Settings の必須プロパティ）。
- DB 書き込みは可能な限り冪等化されている（DELETE→INSERT、ON CONFLICT想定の保存関数など）。
- ログや警告を活用して、外部 API 失敗時にプロセス全体を停止させないフェイルセーフ設計となっている。

今後の予定（例）
- strategy / execution / monitoring パッケージの具体的実装とドキュメント追加。
- テストカバレッジ強化（ユニット・統合テスト）。
- J-Quants / kabu API クライアント実装とエンドツーエンド ETL ワークフローの自動化。

---