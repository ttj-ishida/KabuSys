KEEP A CHANGELOG
=================

すべての重要な変更点をこのファイルに記録します。  
このプロジェクトは Keep a Changelog のフォーマットに準拠しています。

Unreleased
---------

- （現時点で未リリースの変更はありません）

0.1.0 - 2026-04-16
-----------------

初回リリース。KabuSys の基本的な自動売買/研究/監視ツール群を追加しました。主な追加・修正点は以下の通りです。

Added
- パッケージ初期化
  - パッケージバージョンを __version__ = "0.1.0" として追加。

- 起動スクリプト・運用ツール
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル (data/stop_requested.flag) を監視して安全停止。
    - 監視処理は環境 (KABUSYS_ENV) にかかわらず本番 sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_sqlite_path を使用し、MockBroker を想定した分離動作を実装。
    - pid ファイル (data/execution.pid) と停止フラグに対応し、別スレッドで Engine を実行して安全に停止できる。
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を計算して標準出力へ出力（期間フィルタ対応）。
    - P95 算出、日付フィルタ、DB 存在チェック等を実装。

- 設定/環境管理
  - config.py
    - Settings クラスを追加し、環境変数経由で設定値を集約。
    - .env/.env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml 基準）、OS 環境変数を保護する override ロジックを実装。
    - env 値（KABUSYS_ENV）、LOG_LEVEL、PAPER_FILL_MODE 等のバリデーションを実装。
    - DB パス、PID/kill フラグパス、監視閾値などをプロパティで提供。

- ポートフォリオ構成（純粋関数群）
  - portfolio.portfolio_builder
    - 候補選定 select_candidates、等配分 calc_equal_weights、スコア加重 calc_score_weights を実装。
  - portfolio.position_sizing
    - position sizing ロジックを実装（risk_based / equal / score の割当方式、lot_size 丸め、aggregate スケールダウン、cost_buffer 加味）。
    - 投資上限（max_position_pct, max_utilization）やスケールダウン時の端数処理（lot 単位での再配分）に対応。
  - portfolio.risk_adjustment
    - apply_sector_cap によるセクター集中制限（既存ポジションを参照して候補除外）。
    - calc_regime_multiplier によるレジーム乗数（bull/neutral/bear のマッピング、未知レジームではフォールバック）。

- リサーチ / ファクター計算
  - research.factor_research
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）を実装。
    - calc_volatility（ATR20、相対 ATR、20日平均売買代金、出来高比）を実装。
    - calc_value（PER、ROE）を実装（raw_financials と prices_daily を結合）。
    - DuckDB 接続を受け取り SQL → Python の組み合わせで高性能に算出。
  - research.feature_exploration
    - 将来リターン calc_forward_returns（任意ホライズン）、IC 計算 calc_ic（スピアマンランク相関）、rank、factor_summary（count/mean/std/min/max/median）を実装。
    - 外部依存を使わずに純粋 Python 実装で解析用ユーティリティを提供。

- AI / ニューススコアリング
  - ai.news_nlp
    - raw_news を OpenAI API（gpt-4o-mini）でセンチメント解析し、銘柄ごとの ai_scores に書き込む処理を追加。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大対策（記事・文字数制限）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンスバリデーションを実装。
    - ニュースウィンドウ計算（JST → UTC の変換）や出力のクリップ処理（±1.0）を実装。
    - API キー未設定時は明確なエラーを返す。

- ユーティリティ
  - utils.process_priority
    - set_process_priority（Windows / POSIX を吸収）と set_cpu_affinity を追加。
    - psutil を用いて cross-platform に優先度や CPU affinity を設定、権限不足や未対応 OS の場合は警告ログでスキップ。

- DB / IO
  - duckdb を計算基盤として利用（research / ai 等）。
  - sqlite3 を監視・実行系のログ・トレード記録に利用。paper_trading 用に専用 SQLite を分離。

Changed
- 監視と実行の DB 運用方針を明確化
  - 監視(run_monitoring)は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計として実装（監視データの一元化）。
  - 実行(run_execution)は paper_trading 環境時に PAPER_TRADING_SQLITE_PATH を使用して本番 DB から分離。

- .env 自動読み込みの動作
  - プロジェクトルートが検出できない場合は自動読み込みをスキップ。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを抑止可能。

Fixed
- 環境変数パーサの堅牢化
  - export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理（スペース直前の '#' のみコメント扱い）を正しく処理するよう改善。
  - .env ファイル読み込み失敗時は警告を出し続行。

- ポジションサイズ関連
  - calc_score_weights が全スコア 0.0 の場合に等分配へフォールバックし、警告ログを出すように修正。
  - calc_position_sizes の aggregate スケールダウンで lot_size 単位の再配分と上限チェックを強化（再現性のため二次ソートを安定化）。

- 監視ループの堅牢化
  - MONITOR_POLL_INTERVAL が不正な値（非整数・0 以下）だった場合にデフォルトへフォールバックし、警告ログを出力。
  - monitor.check_once() 内での例外を捕捉してループを継続するフェイルセーフを追加。

- ファクター & レポート
  - calc_volatility / calc_momentum 等でウィンドウ内データ不足時に None を返す等、NULL/欠損値の伝播を適切にハンドル。
  - paper_verification_report の P95 計算や日付フィルタでデータ不足時に安全に N/A を出力するよう修正。

Notes / Implementation details
- 多くの処理は外部リソース（DuckDB, OpenAI, ブローカー API）に依存します。実際の運用では各種環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY など）を正しく設定してください。
- 本リリースは初版のため、将来的に lot_size の銘柄別対応や price フォールバック（当日価格欠損時）などの拡張を予定しています（ソース内 TODO に記載あり）。
- AI モジュールは API の呼び出し制限・コストに注意して運用してください（バッチ/リトライ実装あり）。

作者注
- 本 CHANGELOG はコードから推測して作成したものです。実装の詳細や意図と異なる箇所がある可能性があります。必要に応じて差分・補足を追記してください。