# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
このファイルは、コードベースの現状（初回リリース相当）をソースコードから推測して作成した要約です。

なお、パッケージバージョンは kabusys/__init__.py の __version__ に基づき 0.1.0 としています。

All notable changes to this project will be documented in this file.

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-31
初回リリース（コードベースの機能セットを反映）

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開モジュール群を追加。
  - バージョン: 0.1.0。

- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を提供（プロジェクトルート判定: .git または pyproject.toml）。
  - export KEY=val、クォート・エスケープ、インラインコメントなど POSIX ライクな .env 形式のパースに対応。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数取得ヘルパー _require と Settings クラスを提供。
  - 設定項目（例）:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（許容値: development, paper_trading, live；デフォルト: development）
    - LOG_LEVEL（許容値: DEBUG, INFO, WARNING, ERROR, CRITICAL；デフォルト: INFO）

- AI ニュース処理（kabusys.ai.news_nlp）
  - ニュース記事を集約し OpenAI (gpt-4o-mini) を利用して銘柄ごとのセンチメント（ai_score）を算出し、ai_scores テーブルへ書き込む処理を実装。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（DB 上は UTC naive datetime として扱う）。
  - バッチ処理: 最大 20 銘柄/リクエスト、記事トリム（記事数上限・文字数上限）によるトークン肥大対策。
  - エラー耐性: 429・ネットワーク切断・タイムアウト・5xx を対象とした指数バックオフ＋リトライ、その他エラー時は該当チャンクをスキップして継続。
  - レスポンスの厳格なバリデーション（JSON 構造、results 配列、code と score フィールド、数値チェック）。
  - DuckDB への冪等書き込み: 取得済みコードのみ DELETE → INSERT（部分失敗時の既存スコア保護）。
  - テスト用フック: _call_openai_api の差し替えを想定（unittest.mock.patch でモック化可能）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュース由来の LLM センチメント（重み 30%）を合成して日次で regime_score/regime_label を market_regime テーブルへ保存。
  - LLM は gpt-4o-mini を使用。記事がない場合は LLM 呼び出しを行わず macro_sentiment=0.0 を使用。
  - API 呼び出しで失敗した場合はフェイルセーフとして macro_sentiment=0.0 にフォールバック。
  - データ取得・計算はルックアヘッドバイアス対策済み（target_date 未満データのみ使用、datetime.today() 参照を避ける）。
  - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を確保。エラー時は ROLLBACK。

- 研究用ファクター・特徴量モジュール（kabusys.research）
  - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離などのモメンタム系指標を計算。
  - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率などを計算。
  - calc_value: raw_financials と株価を組み合わせて PER / ROE を計算。
  - calc_forward_returns: 指定ホライズンの将来リターンを一括で取得（デフォルト [1,5,21]）。
  - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。
  - factor_summary / rank: 統計要約、ランク付けユーティリティ。
  - 設計方針: DuckDB のみ参照、外部 API に依存しない、標準ライブラリのみで実装。

- データプラットフォーム（kabusys.data）
  - calendar_management: market_calendar の管理、営業日判定、next/prev_trading_day、get_trading_days、is_sq_day、夜間更新ジョブ calendar_update_job を実装。
    - DB データがない場合は曜日ベースでフォールバック（土日を非営業日として扱う）。
    - カレンダーデータ取得は jquants_client を利用（fetch_market_calendar / save_market_calendar）。
    - カレンダー更新処理はバックフィル、健全性チェックを行い安全に実行。
  - pipeline / etl: ETL の公開インターフェース（ETLResult）と内部ユーティリティを提供。
    - 差分取得、保存（idempotent）、品質チェック（quality モジュール）を想定。
    - ETLResult: 実行結果の集約、品質問題やエラーの収集と to_dict メソッド。

- DuckDB を中心としたストレージ設計
  - 各モジュールは DuckDB 接続を受け取り、テーブル（例: prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar）を操作するインターフェースで実装。

### Changed
- （初回リリースのため過去変更無し）

### Fixed
- （初回リリースのため過去修正無し）

### Security
- API キー（OpenAI など）は引数で注入可能か環境変数（OPENAI_API_KEY）から取得。必須未設定時は ValueError を送出して誤動作を防止。
- 環境変数自動読み込みはデフォルト有効。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

### Notes / 実装上の重要ポイント
- ルックアヘッドバイアス対策:
  - AI スコアやレジーム判定では target_date の未来データを参照しない設計（SQL 条件と window 計算で排除）。
  - datetime.today() / date.today() を直接参照しない実装を意識（calendar_update_job 等は別）。
- OpenAI 呼び出し:
  - JSON Mode を想定し、レスポンスは厳密な JSON を期待するが、前後余計なテキストが混ざる場合の復元ロジックを実装。
  - テスト容易性のため _call_openai_api を patch してモックできる。
- 冪等性と部分失敗耐性:
  - AI スコア書き込みや market_regime 書き込みは、既存レコードを消しすぎないようコード単位で DELETE → INSERT を行い、部分失敗時に他データを保護する。
- DuckDB の互換性対応:
  - executemany に空リストを渡さない等、DuckDB バージョン差分を考慮した実装。

### Migration / 使用上の注意
- 必要なテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）を事前に作成しておく必要があります。各関数はそれらテーブルを参照します。
- OpenAI を利用する機能（score_news, score_regime）は OPENAI_API_KEY を環境変数に設定するか、関数引数として api_key を渡してください。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から実行されます。パッケージ配布後は自動検索がルートの検出に依存する点に注意してください。
- J-Quants 関連処理は kabusys.data.jquants_client（コード内参照）に依存します。実装と認証情報（JQUANTS_REFRESH_TOKEN）が必要です。
- ログレベルや環境（KABUSYS_ENV）に不正な値が設定されていると ValueError が発生します。許容値を確認してください。

### Internal / Developer notes
- テストのための差し替えポイント（例）:
  - kabusys.ai.news_nlp._call_openai_api
  - kabusys.ai.regime_detector._call_openai_api
- OpenAI SDK の例外ハンドリングは将来の SDK 変更を考慮して getattr で status_code を参照するなど寛容に実装。
- タイムゾーンの扱い:
  - news_nlp は内部で UTC naive datetime を用いた比較を行う。JST/UTC の変換ロジックは calc_news_window に明記あり。

---

参照テーブル・主要関数（抜粋）
- 設定: kabusys.config.Settings（settings 変数）
- ETL: kabusys.data.pipeline.ETLResult
- ニューススコア: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- カレンダー: kabusys.data.calendar_management.*
- 研究関数: kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary

以上。必要であれば、各リリースノートの箇条書きをさらに詳細化（例: SQL スキーマ想定、サンプル env ファイル、使用例コード）できます。どのレベルの詳細を追加するか指示してください。