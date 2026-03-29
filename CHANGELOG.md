# Keep a Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは SemVer を採用します。

## [Unreleased]
- 

## [0.1.0] - 2026-03-29
初回リリース。本リリースでは日本株自動売買システムのコアライブラリを導入します。主要なサブパッケージ、データ ETL、研究用ファクター計算、ニュース/NLP と LLM を用いたスコアリング等の基盤機能を含みます。

### Added
- パッケージ初期化
  - kabusys パッケージの基本メタデータを追加（__version__ = "0.1.0"）。トップレベルで data / strategy / execution / monitoring を公開対象に指定。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む仕組みを実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）により、CWD に依存しない自動ロードを実現。
  - .env/.env.local の読み込み順序と上書きルール（OS 環境変数保護）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env のパースは export 形式、引用符、エスケープ、インラインコメントなどに対応。
  - 必須環境変数検査（_require）を提供。以下の主要設定をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH (デフォルト data/kabusys.duckdb), SQLITE_PATH (デフォルト data/monitoring.db)
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の妥当性検査、および is_live/is_paper/is_dev ヘルパー

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約して銘柄ごとのテキストを作成し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメントを算出。
    - チャンクバッチ（最大 20 銘柄/コール）、1 銘柄あたり最大記事数・文字数制限を実装。
    - API リトライ（429／ネットワーク断／タイムアウト／5xx を指数バックオフ）、レスポンス検証、スコアの ±1.0 クリップ、部分失敗時に既存スコアを保護するための個別 DELETE → INSERT ロジックを実装。
    - テスト用に内部 API 呼び出し点（_call_openai_api）をパッチ可能に設計。
    - calc_news_window: タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）をUTC naive datetime で計算するユーティリティを提供。
    - score_news: 書き込み件数を返す。API キー注入（引数 or OPENAI_API_KEY）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - prices_daily / raw_news を参照し、計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - LLM 呼び出しは独立実装でモジュール結合を避け、API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。OpenAI クライアントは引数あるいは環境変数 OPENAI_API_KEY で解決。
    - リトライやエラー処理のポリシー（429/タイムアウト/5xx の再試行、非5xx は即時フォールバック）を明示。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを用いた営業日判定 API（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。DB 登録がない場合は曜日（平日）ベースでフォールバック。
    - 次/前営業日探索は最大探索日数を設定して無限ループを防止。
    - calendar_update_job: J-Quants API からの差分取得と market_calendar への冪等保存、バックフィル（直近数日再取得）、健全性チェックを実装。
  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを導入（取得件数・保存件数・品質問題・エラーの集計、シリアライズ用 to_dict）。quality モジュールの品質検査結果を収集・格納。
    - 差分更新・backfill の概念をサポートするユーティリティ。DB 存在チェック・最大日付取得ユーティリティを提供。
    - jquants_client と連携して Idempotent な保存フローを想定（save_*）。
    - kabusys.data.etl で ETLResult を再エクスポート。

- 研究 (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - モメンタム（1M/3M/6M、ma200 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）等の計算を実装。prices_daily / raw_financials を参照し、(date, code) キーの dict リストを返す。
    - 欠損・データ不足時の扱いを明確化（必要データ不足で None を返す）。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応）、IC（スピアマンρ）計算、ランク化ユーティリティ、統計サマリー（count/mean/std/min/max/median）を実装。
    - 外部依存を持たせず、標準ライブラリと DuckDB クエリで完結する設計。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Security
- OpenAI API キーや外部シークレットの取り扱いは環境変数経由を想定。.env 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能（テスト時の安全策）。

### Notes / Implementation details / 設計上の注意
- ルックアヘッドバイアス対策: 全ての時間窓計算・クエリは target_date を明示的に受け取り、datetime.today()/date.today() を直接参照しない設計を採用。
- DuckDB との相互作用: 一部の操作（executemany 等）で DuckDB のバージョン差異を考慮したガード処理を追加（空 params の扱い等）。
- トランザクションと冪等性: market_regime や ai_scores 等への書き込みは DELETE → INSERT の冪等パターン、および BEGIN/COMMIT/ROLLBACK を用いて整合性を担保。
- OpenAI 呼び出しは JSON mode（response_format={"type":"json_object"}）を利用。レスポンスのパース/検証ロジックを強化し、余計な前後テキストが混入した場合の復元処理も実装。
- テスト容易性: OpenAI 呼び出しポイント（各モジュールの _call_openai_api）を unittest.mock.patch 等で差し替え可能にしているため、API 実際呼び出しを伴わない単体テストが可能。

---

開発・利用に関する既知の制約や将来的な改善点は README やドキュメントに順次追記予定です。ご要望やバグ報告は issue を通じてお知らせください。