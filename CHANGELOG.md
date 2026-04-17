# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
日付はこのリリース作成日です。

フォーマットの意味:
- Added: 新規機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated / Removed / Security: 該当なしの場合は記載していません

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ初期リリース: KabuSys — 日本株自動売買システムのコア機能群を追加。
  - パッケージバージョンは `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は環境 (`KABUSYS_ENV`) に関わらず本番用の `sqlite_path` を使用する旨を明示。
    - 停止フラグファイル（data/stop_requested.flag）を検出して安全にループ終了。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを行う。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は独立した Paper Trading 用 SQLite（`data/paper_trading.db`）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 起動前に停止フラグが既に立っている場合は起動せず終了。
    - Engine は別スレッドで実行し、停止フラグを監視して安全停止。PID ファイルパスを受け渡す。

- 設定管理
  - config.py
    - プロジェクトルートを `.git` または `pyproject.toml` で探索し、.env 自動ロード機能を追加（無効化用に `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を用意）。
    - `.env` / `.env.local` の読み込み優先度を実装（OS 環境変数は保護）。
    - .env の行パーサを強化（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメントの扱いなど）。
    - Settings クラスを提供し、環境変数からアプリ設定を安全に取得。必須値未設定時は `ValueError` を発生させる。
    - 各種設定プロパティを用意（DB パス、Paper Trading 関連、監視閾値、PID/KILL フラグパス、環境判定ロジック等）。
    - `PAPER_FILL_MODE` のバリデーション（"instant" | "partial" | "never" | "reject"）を実装。

- モニタリング DB 初期化ユーティリティ
  - monitoring.monitoring_db:init_monitoring_db を呼ぶことで監視用テーブルを冪等に保証。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を追加。
    - デフォルト DB は `data/paper_trading.db`。`--db` オプションや環境変数 `PAPER_TRADING_SQLITE_PATH` で上書き可能。
    - 稼働率・注文成功率・送信率・レイテンシ（P95）などを集計して PASS/FAIL 判定を出力。
    - 判定基準（閾値）は定数化（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）。
    - SQL の欠損 (テーブル未作成 等) に対する保護（OperationalError を捕捉して N/A / 0 を返す）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - select_candidates はスコア降順、同点時は signal_rank（小さい方優先）でのタイブレークを実装。
    - calc_score_weights は全スコアが 0 の場合に等配分へフォールバックして WARNING を出す。
  - portfolio/risk_adjustment.py
    - apply_sector_cap：セクター集中の上限チェック（既存保有を考慮、売却予定銘柄を除外可能）。"unknown" セクターは上限適用しない。
    - calc_regime_multiplier：市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）と未知レジームでのフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes：銘柄別の発注株数を算出（risk_based / equal / score をサポート）。
    - 単元株（lot_size）丸め、1 銘柄上限 / 投下資金上限、cost_buffer を使った保守的見積り、aggregate cap を超える場合のスケールダウンと残差分の lot 単位での再配分ロジックを実装。
    - 価格欠損時のスキップやログ出力等の安全策を追加。

- 研究モジュール（DuckDB を利用したファクター計算・解析）
  - research/factor_research.py
    - calc_momentum：モメンタム（1M/3M/6M リターン、MA200 乖離）を計算。データ不足判定（200 行未満等）を実装。
    - calc_volatility：ATR（20 日平均）・ATR 比率・出来高/売買代金指標を計算。true_range の NULL 伝播を明示的に制御。
    - calc_value：raw_financials からの最近の財務データ取得（ROW_NUMBER を使用）と PER/ROE 計算を実装。
  - research/feature_exploration.py
    - calc_forward_returns：LEAD による将来リターン計算（horizons のバリデーションあり）。
    - calc_ic：Spearman ランク相関による IC 計算（ランクは average tie handling）。
    - factor_summary：各ファクターの count/mean/std/min/max/median を計算する集計ユーティリティ。
    - rank：同順位は平均ランクにする実装（丸めによる ties 検出漏れ対策あり）。

- AI ニュース NLP（下地実装）
  - ai/news_nlp.py
    - raw_news を OpenAI API（gpt-4o-mini）でスコアリングし、ai_scores テーブルへ書き込む処理の設計・実装（バッチ処理、トークン肥大対策、最大記事数・文字数制限、スコアクリップ、リトライ戦略、レスポンス検証、部分成功時の DB 保護方針 等）。
    - calc_news_window：JST に基づくニュース収集ウィンドウ計算を提供（target_date に対して前日 15:00 JST 〜 当日 08:30 JST）。
    - score_news：API キー解決・ウィンドウ算出・記事集約から書き込みまでのフローを実装（途中までの実装が含まれる）。

- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定を追加。Windows は psutil の優先度クラス、POSIX は nice 値で制御。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加（引数チェック・例外時は警告ログでスキップ）。
    - アクセス権限や未対応 OS の場合は失敗をログに記録してスキップするフェイルセーフを実装。

- パッケージ公開用の __all__ 整備
  - portfolio と research のパッケージレベルで主要関数をエクスポート。

### Changed
- 仕様上の注意をコード内ドキュメントに明記
  - run_monitoring が本番 sqlite_path を環境に関係なく使用する点をドキュメントに記載。
  - 各モジュールに設計方針（DuckDB/SQLite 以外にアクセスしない等）を注記し、ルックアヘッドバイアス防止などの注意点を明示。

### Fixed
- .env 読み込みの堅牢化
  - config._parse_env_line がクォートやエスケープ、行内コメントをより正確に扱うよう改良され、.env ファイルの多様な表記に耐性を持たせた。

- モニタリングループでのエラーハンドリング強化
  - monitor.check_once() の例外をキャッチしてログを残し、ポーリングループを継続するように変更（単回の例外でプロセス全体が停止しないようにする）。

### Notes / 使用上の重要事項
- 環境変数
  - KABUSYS_ENV: 有効値は "development" | "paper_trading" | "live"。無効値は ValueError。
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（整数）。1 未満や不正値はデフォルト 60 秒にフォールバック。
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB のパスを上書き可能。
  - PAPER_FILL_MODE: Paper Broker の振る舞い（instant|partial|never|reject）。無効値は ValueError。
  - OPENAI_API_KEY: ai/news_nlp.score_news 実行時に必要（引数で渡すことも可能）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化。
- 停止 / PID / キーファイル
  - data/stop_requested.flag を配置すると run_monitoring / run_execution が安全に停止する。
  - run_execution は data/execution.pid を PID 管理に利用。
  - Settings で PID/KILL フラグパスを調整可能。

---

今後の予定（例）
- ai/news_nlp の完全実装（API 呼び出しのリトライ部分・レスポンス処理・DB 書き込みの続き）。
- テストカバレッジ拡充（特に portfolio / position sizing の数値ロジック）。
- ドキュメント強化（運用手順、.env.example、デプロイ手順）。

以上。