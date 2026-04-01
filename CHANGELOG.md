# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-04-01
初回リリース。日本株自動売買プラットフォームの基礎機能を実装しました。主な追加内容は以下のとおりです。

### Added
- パッケージ基盤
  - kabusys パッケージ初期構成（バージョン 0.1.0）。
  - 公開 API (__all__) に data, strategy, execution, monitoring を定義。

- 設定・環境変数管理
  - kabusys.config: .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）。
    - .env と .env.local の読み込み順序を実装（OS 環境変数を保護する protected 機構）。
    - export 形式やクォート・エスケープ、インラインコメント等に対応するパーサ実装。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB /監視設定 / システム設定をプロパティ経由で取得。
    - 必須値取得時のバリデーション（未設定時は ValueError を送出）。
    - KABUSYS_ENV, LOG_LEVEL の値検証。
    - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）や PID ファイルパスのデフォルトを設定。

- AI（NLP）関連
  - kabusys.ai.news_nlp:
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄別センチメントを評価して ai_scores テーブルへ書き込む score_news を実装。
    - JST ベースのニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で正確に算出。
    - バッチ送信（最大 20 銘柄/チャンク）、記事トリム（最大記事数、最大文字数）によるトークン肥大化対策。
    - JSON Mode を利用した厳格なレスポンス検証と冗長テキストからの JSON 抽出のフォールバック。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）と指数バックオフ、失敗時のフェイルセーフ（該当チャンクをスキップ）。
    - DuckDB executemany の互換性対策（空リスト渡しを回避）。
    - score_news は成功時に書き込んだ銘柄数を返す。API キーは引数か環境変数 OPENAI_API_KEY で供給。

  - kabusys.ai.regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - マクロニュース抽出（キーワードベース）・LLM スコアリング・スコア合成・market_regime テーブルへの冪等書き込みを提供。
    - API 呼び出し失敗時は macro_sentiment=0.0 にフォールバックして処理継続。
    - OpenAI 呼び出しは専用の内部 _call_openai_api を用い、テストで差し替えやすく設計。

- Data 関連
  - kabusys.data.calendar_management:
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が未取得時の曜日ベースフォールバック（週末を非営業日扱い）。
    - calendar_update_job による夜間差分取得（J-Quants クライアント呼び出し）とバックフィル、健全性チェックを実装。
  - kabusys.data.pipeline / etl:
    - ETLResult データクラスを公開（ETL 実行結果、品質チェック情報、エラー集計を保持）。
    - pipeline モジュールで ETL の差分取得・保存・品質チェックの設計に対応するユーティリティを実装（ETLResult を含む）。
    - jquants_client 経由の差分フェッチと冪等保存を前提とした設計。

- Research（リサーチ）関連
  - kabusys.research.factor_research:
    - モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER、ROE）などのファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB のウィンドウ関数を活用し、日次・銘柄別の計算結果を dict リストで返却。
  - kabusys.research.feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を実装。
    - pandas 等に依存せず標準ライブラリのみでの実装。
  - kabusys.research.__init__ で各関数を再エクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- OpenAI 統合まわりの堅牢性改善（設計段階で次を考慮して実装）
  - 429 / ネットワーク断 / タイムアウト / 5xx のリトライ処理と指数バックオフ。
  - API レスポンスの JSON パース失敗や不正なフィールドを検出した場合はログ出力の上でフェイルセーフ値（0.0 やスキップ）を採用し、全体処理を停止させない実装。
- DuckDB 互換性対応
  - executemany に空リストを渡さないガード（DuckDB 0.10 の制約回避）。
  - DATE/文字列から date オブジェクトへ安全に変換するユーティリティを実装。

### Security
- OpenAI API キーや Slack / kabu API の機密情報取得時は明示的に環境変数から取得し、未設定時は ValueError を送出して早期検出できるようにしました。
- .env ローダーは OS 環境変数を保護する protected セットを保持し、既存の OS 環境変数を意図せず上書きしないデフォルト動作。

### Migration notes / ユーザ向け注意事項
- OpenAI の利用
  - score_news / score_regime は api_key 引数を受け取りますが、未指定時は環境変数 OPENAI_API_KEY を参照します。未設定だと ValueError が発生します。
  - API 呼び出し失敗時は該当チャンク/評価をスキップしたり 0.0 を使用して継続するため、部分的な結果欠損が発生する可能性があります。ログを確認してください。
- 環境変数自動読み込み
  - パッケージインポート時にプロジェクトルートが検出できる場合、.env → .env.local の順で自動読み込みします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - .env のパースは export 形式やクォート・エスケープに対応していますが、.env.example を参照して設定してください。
- DuckDB パス・SQLite パス等のデフォルトは Settings プロパティで定義されています。必要に応じて環境変数で上書きしてください（DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等）。
- calendar_update_job は market_calendar の最終取得日を検査し、過度に将来の日付が登録されている場合はスキップします（健全性チェック）。

---

今後のリリースでは、strategy / execution / monitoring の具体的な発注ロジックやランタイム監視、より多様なファクターや backtest ユーティリティの追加を計画しています。