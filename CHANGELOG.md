# CHANGELOG

すべての注目すべき変更点はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています（[Unreleased] やバージョン見出し、カテゴリ別記載）。

## [0.1.0] - 2026-04-17

初回公開リリース。以下の主要機能と改善を含みます（コードベースから推測して記載）。

### Added
- 全体
  - パッケージ初期版を導入（kabusys v0.1.0）。
  - Python モジュール構成を追加: data / strategy / execution / monitoring 等を想定したモジュール群をエクスポート。

- 設定管理
  - 環境変数・.env ファイル読み込み機能（kabusys.config.Settings）。
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）により .env/.env.local を自動読み込み。OS 環境変数を保護するための上書き制御と、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DUCKDB/SQLite パス / PID・フラグパス / モニタ閾値 / 環境種別検証など）。
  - PAPER_FILL_MODE の値検証（"instant" | "partial" | "never" | "reject"）や KABUSYS_ENV / LOG_LEVEL の検証を実装。

- 実行制御スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - BrokerClientFactory によるブローカークライアント生成。
    - paper_trading 環境では paper 用専用 SQLite（data/paper_trading.db 等）を使用し、本番 DB と分離（MockBrokerClient を想定）。
    - RiskManager / OrderManager / Reconciler の組立てと ExecutionEngine の起動（スレッドで実行）。PID ファイル・停止フラグによる制御／安全停止をサポート。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視データは共通 DB に記録）。
    - stop_requested.flag による停止検知、例外発生時のログ記録とポーリング継続。

- 監視 DB 初期化
  - init_monitoring_db 呼び出しを起動手順に追加し、監視用テーブルの存在を保証（冪等）。

- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収。
    - set_process_priority(level: "high"|"normal"|"low") と set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応環境時は警告ログでスキップするフェイルセーフ実装。

- ポートフォリオ構築
  - 複数の純粋関数を実装（DB参照なし、メモリ内計算）。
    - portfolio_builder: select_candidates（スコア降順）、calc_equal_weights、calc_score_weights（スコア合計が0の場合は等配分にフォールバック）。
    - risk_adjustment: apply_sector_cap（セクター集中制限、売却予定銘柄除外対応）、calc_regime_multiplier（"bull"/"neutral"/"bear" の乗数、未知レジームは警告して 1.0 にフォールバック）。
    - position_sizing: calc_position_sizes（allocation_method="risk_based"|"equal"|"score" をサポート）、単元株丸め、per-stock 上限・aggregate cap（available_cash）でスケールダウン、cost_buffer を考慮した保守的見積り、残差分の lot 単位での再配分ロジックを実装。

- リサーチ／特徴量
  - research モジュール（DuckDB 接続を利用、prices_daily/raw_financials 参照）を実装。
    - factor_research: calc_momentum（1/3/6M リターン・MA200乖離）、calc_volatility（ATR20、相対ATR、20日平均売買代金・出来高比）、calc_value（PER/ROE）。
    - feature_exploration: calc_forward_returns（複数ホライズン対応、入力検証あり）、calc_ic（Spearman ランク相関による IC 計算）、factor_summary（count/mean/std/min/max/median）、rank（同順位は平均ランク）。
    - エクスポート：zscore_normalize（data.stats から）を含めた利便性エクスポート。

- AI ニュース NLP
  - ai/news_nlp.py を追加。
    - raw_news + news_symbols から銘柄ごとに記事を集約し、OpenAI API（gpt-4o-mini）を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書込む処理を実装。
    - 処理はバッチ（最大 _BATCH_SIZE=20 銘柄）で送信、最大記事数/文字数でトリム、レスポンスは厳密な JSON モードで検証。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ再試行を実装（上限あり）。
    - スコアは ±1.0 にクリップ。API キーの解決は引数優先、なければ環境変数 OPENAI_API_KEY を参照。

- コマンドラインツール
  - tools/paper_verification_report.py を追加。
    - Paper Trading の検証レポートを生成（SQLite の paper_trading DB を使用）。
    - 稼働率・注文成功率・送信率・レイテンシ（P95）などを集計して PASS/FAIL を判定する閾値を定義（稼働率99% など）。
    - --from / --to / --db オプションをサポートし、出力は人間向けテキスト（標準出力）。

### Changed
- 自動環境読み込みの挙動整理
  - .env と .env.local の読み込み順と上書きルールを明確化（OS 環境変数優先、.env.local は override=True で上書き可能）。
  - .env 行パーサーの拡張: export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの扱いを厳格化。

### Fixed / Robustness
- .env パーサーで無効行やキー無し行を正しく無視するよう改良。
- 各種集計・算出関数でデータ欠損時に None を返すなど安全に動作するよう防御的実装（ゼロ割回避、NULL伝播の扱い等）。
  - factor_research や paper_verification_report のクエリは、行数不足や NULL を検出した場合に None を返す/例外を捕捉して N/A 表示にフォールバック。
- run_monitoring のポーリングループ内で check_once() の例外を捕捉してログ出力し、次回ポーリングに継続する耐障害性を実装。
- process_priority / cpu_affinity は権限不足や未対応プラットフォーム時に警告を出して安全にスキップするよう改良。

### Known limitations / Notes
- DuckDB に対する executemany の制約に留意（ai/news_nlp の実装コメント等で注意喚起あり）。
- position_sizing の lot_size は現在グローバル固定（将来的には銘柄別 lot_size マップへの拡張を想定）。
- apply_sector_cap のエクスポージャー計算は price が 0.0 の場合に過少評価となる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討。
- news_nlp.score_news は API キー必須（引数または OPENAI_API_KEY 環境変数）。API 呼び出し失敗時は部分的なスコア書込で済ますフェイルセーフ設計。

---

今後の改善候補（コード中の TODO/コメントに基づく）
- 銘柄別の lot_size など取引ルールの柔軟化。
- price 欠損時のフォールバックロジック追加（前日終値や取得原価）。
- news_nlp のより厳密な部分失敗ハンドリング（トランザクション的な保護やリトライ粒度の向上）。
- テスト用の設定（自動ロード無効化の周知）と CI での DB モック整備。

(以上)