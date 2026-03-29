# changelog

すべての変更は「Keep a Changelog」規約に従って記載しています。  
このファイルはコードベースから推測して自動生成しています。実装状況の詳細や追加の注意はソースコードを参照してください。

<!-- Unreleased セクション -->
## [Unreleased]

- 今後の変更・予定はここに記載します。

---

## [0.1.0] - 2026-03-29

最初の公開リリース。以下の主要機能・モジュールを追加しました。

### Added
- パッケージ骨格
  - kabusys パッケージ初期化（src/kabusys/__init__.py）を追加。公開モジュール: data, strategy, execution, monitoring。
  - パッケージバージョン __version__ = "0.1.0" を定義。

- 設定・環境変数読み込み
  - src/kabusys/config.py:
    - .env/.env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
    - .env の行パース機能を強化（export 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントルール）。
    - 上書き制御（override）と protected キーセットによる OS 環境変数保護。
    - Settings クラスを追加し、アプリケーションで必要な環境変数をプロパティ経由で取得:
      - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - 任意/デフォルト: KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)、DUCKDB_PATH (data/kabusys.duckdb)、SQLITE_PATH (data/monitoring.db)
      - KABUSYS_ENV 値検証（development / paper_trading / live）、LOG_LEVEL 値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
      - is_live/is_paper/is_dev の補助プロパティ。

- AI 関連（OpenAI を用いたニュース解析・レジーム判定）
  - src/kabusys/ai/news_nlp.py:
    - raw_news と news_symbols を集約して銘柄毎にニュースを生成し、OpenAI (gpt-4o-mini) を用いて銘柄別センチメント（-1.0〜1.0）を取得。
    - タイムウィンドウと UTC 変換ロジック（前日 15:00 JST ～ 当日 08:30 JST）を実装。
    - バッチ処理（_BATCH_SIZE=20）、1銘柄あたりの最大記事数/文字数トリム、JSON レスポンスバリデーション、スコアクリップを実装。
    - リトライ戦略（429/ネットワーク断/タイムアウト/5xx、指数バックオフ）を実装。API 失敗時は部分スキップしフェイルセーフを維持。
    - DuckDB への冪等的な書き込み（DELETE → INSERT、トランザクション、ROLLBACK 保障）。
    - テスト容易性のため _call_openai_api の差し替えを想定（unittest.mock.patch でモック可能）。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。

  - src/kabusys/ai/regime_detector.py:
    - ETF 1321（日経225連動型）の200日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成して日次市場レジーム（bull/neutral/bear）を判定する機能を実装。
    - prices_daily と raw_news を参照して ma200_ratio を計算、マクロ記事をフィルタして OpenAI に投げるロジックを実装。
    - レジームスコア合成と market_regime テーブルへの冪等書き込みを実装（BEGIN/DELETE/INSERT/COMMIT）。
    - API キー解決、リトライ、フォールバック（API 失敗時は macro_sentiment=0.0）を実装。
    - テスト用に _call_openai_api の差し替えを想定。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- データプラットフォーム（DuckDB ベース）
  - src/kabusys/data/pipeline.py:
    - ETLResult データクラスを追加（ETL 実行結果の集約: fetched/saved カウント、品質問題、エラー等）。
    - 差分取得 / バックフィル / 品質チェックの設計に沿ったユーティリティ関数群（テーブル存在チェック、最大日付取得、取引日調整用ヘルパー等）を実装。
    - ETL 実行のエラーハンドリング方針（品質問題は収集して続行、致命的エラーは errors に記録）を用意。

  - src/kabusys/data/etl.py:
    - ETLResult を再エクスポート（public interface）。

  - src/kabusys/data/calendar_management.py:
    - market_calendar テーブルを用いた営業日管理ロジックを実装:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
      - カレンダーデータが無い場合の曜日ベースのフォールバック
      - DB 登録値優先、未登録日の一貫したフォールバック処理
      - 最大探索日数制限 (_MAX_SEARCH_DAYS) と健全性チェック
    - calendar_update_job を実装（J-Quants からの差分取得 → save_market_calendar 呼び出し → 保存件数を返す）。バックフィルや lookahead のデフォルト値を設定。
    - jquants_client（外部モジュール）との連携を想定。

- Research（因子計算・特徴量探索）
  - src/kabusys/research/factor_research.py:
    - Momentum / Volatility / Value といった定量ファクター計算を実装:
      - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（データ不足時は None）
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（窓や NULL 処理に注意）
      - calc_value: per（EPS 0/欠損時は None）、roe（raw_financials 参照）
    - DuckDB の Window 関数を活用した実装。
    - 返り値は {date, code, ...} の dict リスト。

  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns: 複数ホライズンの将来リターンを一括取得する汎用実装（ホライズンの妥当性チェックあり）。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を実装（3 件未満で None）。
    - rank: 同順位は平均ランクとするランク化ユーティリティ（round による ties 安定化）。
    - factor_summary: 各カラムの基本統計量（count/mean/std/min/max/median）を計算。
    - いずれも pandas 等の外部依存なしで標準ライブラリと DuckDB による実装。

- モジュール公開の整備
  - src/kabusys/ai/__init__.py で score_news を公開。
  - src/kabusys/research/__init__.py で主要な関数群（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）を再エクスポート。
  - src/kabusys/data/__init__.py を追加（空のパッケージ初期化）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出して明示的に失敗させる実装（誤操作でのキー漏洩を緩和するための設計方針がみられます）。

### Notes / 設計上の注意点（重要）
- ルックアヘッドバイアス対策:
  - AI/NLP/レジーム/ETL/リサーチの各モジュールは datetime.today() / date.today() を処理内部で参照せず、呼び出し側が target_date を渡す設計になっています。
  - SQL クエリやウィンドウ計算にも target_date 未満/以前のフィルタを明示しており、未来データ参照を防止しています。

- フェイルセーフ設計:
  - OpenAI 呼び出し失敗時はスコアを 0.0（中立）や該当銘柄のスキップで継続する設計。ログに WARN/INFO を出して上位での対応を容易にしています。
  - DuckDB への書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護され、部分失敗時の既存データ保護（コード絞り込み）を行っています。

- テスト性:
  - AI 呼び出し部分（_call_openai_api 等）はモック差し替えを想定して実装されています（unittest.mock.patch での差し替えが可能）。

- 外部依存:
  - jquants_client や quality モジュールなど、外部（別モジュール）との連携を前提とした設計があります。実行にはそれらの実装が必要です。

### Breaking Changes
- 初版リリースのため該当なし。

---

参照:
- 各モジュールの実装詳細・ログメッセージ・エラー処理はソースコード内の docstring とコメントを参照してください。