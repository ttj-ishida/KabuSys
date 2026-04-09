# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-09
初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージメタ情報（src/kabusys/__init__.py, __version__ = "0.1.0"）を追加。
  - パッケージの公開モジュール名として data, strategy, execution, monitoring を宣言（strategy/execution/monitoring はエクスポート宣言のみ）。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルートの検出は .git または pyproject.toml を起点に行い、CWD に依存しない実装。
  - .env のパース機能を実装（コメント、export 形式、シングル/ダブルクォート、エスケープに対応）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を導入。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB / Paper Trading / 監視 / システム等の設定プロパティを定義。
  - 設定値のバリデーション（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL など）とデフォルト値を用意。
  - ファイルパスは expanduser を行いユーザフレンドリな挙動に。

- AI（ニュース NLP / レジーム判定）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini）の JSON Mode を用いてバッチ評価。
    - バッチサイズや記事／文字数上限（_BATCH_SIZE=20, _MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）を実装しトークン肥大化対策。
    - 再試行（429・ネットワーク断・タイムアウト・5xx）に対する指数バックオフを実装。リトライ上限は _MAX_RETRIES=3。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results リスト・code/score 検証、既知コードのみ採用、数値チェック）。
    - スコアを ±1.0 にクリップし、取得成功分のみ ai_scores テーブルへ置換（DELETE → INSERT）して部分失敗で既存データを保護。
    - calc_news_window(target_date) を提供し、JST基準のニュース収集ウィンドウ（前日 15:00 ～ 当日 08:30）を UTC naive datetime で返す。
    - API キー注入対応（api_key 引数または環境変数 OPENAI_API_KEY）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とニュースマクロセンチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - DuckDB から prices_daily / raw_news を参照し ma200_ratio を算出、calc_news_window を用いてニュース窓を決定。
    - OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を取得、API失敗時はフェイルセーフで 0.0 を採用。
    - レジーム合成後、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実施。
    - API 呼び出しは独立実装でモジュール結合を避け、テスト用に差し替え可能。

- Data / ETL / カレンダー（src/kabusys/data/*）
  - ETL 基盤（src/kabusys/data/pipeline.py）
    - 差分更新、バックフィル、品質チェック（quality モジュール想定）に基づく ETL パイプラインの骨格を実装。
    - ETLResult dataclass を実装（target_date, fetched/saved counts, quality_issues, errors 等）し to_dict によるシリアライズ対応。
    - ETLResult は data/etl.py から再エクスポート（外部参照用）。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを参照して営業日判定ロジックを提供（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）。
    - DB 登録値が無い場合は曜日ベースでフォールバック（週末を非営業日扱い）。
    - calendar_update_job を実装し J-Quants からの差分取得・バックフィル・保存処理を行う（lookahead・backfill・健全性チェックあり）。
    - DB 書き込み失敗や API エラー時は安全に失敗（0 を返す）しログ出力。

- Research（ファクター計算・特徴量探索）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム: mom_1m / mom_3m / mom_6m, ma200_dev（200日 MA 乖離）。
    - ボラティリティ/流動性: atr_20, atr_pct, avg_turnover, volume_ratio（20日ベース）。
    - バリュー: per, roe（raw_financials からの最新財務データと prices_daily を結合）。
    - DuckDB 上で SQL とウィンドウ関数を用いて高速に計算。データ不足時に None を返す設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算: calc_forward_returns（任意ホライズン、デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算: calc_ic（Spearman の順位相関）。
    - ランク変換ユーティリティ: rank（同順位は平均ランク）。
    - ファクター統計サマリ: factor_summary（count/mean/std/min/max/median）。
    - pandas 等の外部依存を持たない純粋 Python 実装。

### Changed
- （初回リリースのためなし）

### Fixed
- （初回リリースのためなし）

### Notes / 設計上の重要ポイント
- ルックアヘッドバイアス対策: 各処理は datetime.today()/date.today() を直接参照せず、target_date 引数に基づく決定を行う設計。
- データベース操作は冪等性を重視（DELETE → INSERT、ON CONFLICT を想定）し、トランザクションと ROLLBACK を適切に扱う。
- OpenAI API 呼び出しは JSON Mode（response_format）を使い厳密な JSON レスポンスを期待するが、前後余計テキスト混入時の復元処理も実装。
- API 失敗時はフェイルセーフ（スコアは 0.0 を採用、処理は継続）で安全性を優先。
- DuckDB を主要データレイヤに使用。外部重い依存（例: pandas）を避ける設計。
- ログ出力を充実させて異常時のトラブルシュートを容易化。

### 環境変数（主要）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
- OPENAI_API_KEY（AI 機能の利用に必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live), LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD（自動 .env ロードを無効化）

---

開発・運用に際して不明点や追記してほしい変更点があれば指示ください。必要に応じて「変更履歴の粒度を上げる」「個別ファイルごとの詳細な変更点を追加する」など対応します。