CHANGELOG
=========

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

0.1.0 - 2026-04-17
-----------------

Added
- 初回公開: KabuSys 基本モジュール群を追加。
  - パッケージバージョン: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

- 実行 / 監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV により paper_trading モードで専用 SQLite（data/paper_trading.db）を使用する分離機能を実装。
    - execution.pid 管理および data/stop_requested.flag による外部停止フラグ検知をサポート。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行い ExecutionEngine を別スレッドで実行。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec 等）を定義。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視データは常に本番 DB を参照）。
    - data/stop_requested.flag による停止、KeyboardInterrupt のハンドリングを実装。

- 設定・環境 (.env) 管理
  - config.py:
    - プロジェクトルート自動検出（.git または pyproject.toml）。CWD に依存しない実装。
    - .env/.env.local の自動ロード機構（OS 環境変数を protected として扱い上書き制御）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - 厳密なパース実装: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理等をサポート。
    - 必須 env の取得ヘルパー _require() と各種設定プロパティ（DB パス、API キー、監視しきい値、環境種別判定等）を追加。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）を導入。
    - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値一覧）を導入。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py:
    - 銘柄候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア重み配分 (calc_score_weights) を実装。
    - スコア全てが 0 の場合は等金額配分へフォールバック（警告ログ）。
    - 同点のタイブレークロジックを signal_rank で解決。
  - portfolio/risk_adjustment.py:
    - セクター集中制限 (apply_sector_cap) を実装。既存保有のセクター別エクスポージャーを算出して上限超過セクターの新規候補を除外。
    - "unknown" セクターはセクター上限の適用対象外にする挙動を採用。
    - レジーム乗数 calc_regime_multiplier を実装（bull/neutral/bear のマップ、未知値は 1.0 でフォールバックし警告）。
  - portfolio/position_sizing.py:
    - 発注株数計算 calc_position_sizes を実装（allocation_method: risk_based / equal / score 対応）。
    - 単元株（lot_size）丸め、1 銘柄上限・リスクベース計算、aggregate cap（available_cash）によるスケールダウンロジック、残差の lot 単位での再配分アルゴリズムを実装。
    - cost_buffer を考慮した保守的見積り対応。

- 研究・リサーチ
  - research/factor_research.py:
    - Momentum / Volatility / Value ファクター計算関数を追加（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を用いたウィンドウ関数ベースの実装（MA200、ATR 等）。
    - データ不足時は None を返す安定した処理。
  - research/feature_exploration.py:
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応）、ランク相関 IC 計算 calc_ic、ファクター統計サマリ factor_summary、ランク付けユーティリティ rank を追加。
    - 外部ライブラリ非依存、標準ライブラリのみでの実装方針。

- AI / ニュース NLP
  - ai/news_nlp.py:
    - raw_news を OpenAI API（gpt-4o-mini 想定）でセンチメント評価し ai_scores テーブルへ書き込むモジュールを追加。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）計算ユーティリティ calc_news_window、バッチ送信、JSON Mode 出力バリデーション、±1.0 のクリップ、429/5xx/ネットワーク障害時の指数バックオフリトライなどの設計を記載。
    - 実装はフェイルセーフを重視し、API キー未設定時に ValueError を投げる。
    - （ファイル末尾で処理ロジックが途中まで含まれているため、以降の DB 書き込み等は続きの実装を想定）

- ユーティリティ
  - utils/process_priority.py:
    - プロセス優先度設定と CPU affinity 設定ユーティリティを追加（set_process_priority, set_cpu_affinity）。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収する実装。アクセス拒否や未対応 API の場合は警告ログで安全にフォールバック。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 検証レポート生成スクリプトを追加。
    - 稼働率 / 注文成功率 / 送信率 / P95 レイテンシ等を計算し PASS/FAIL を出力する。
    - 日付フィルタ、P95 計算、DB 存在チェック、DB のテーブル存在エラーを捕捉して安全にレポートを生成。

Changed
- DB 関連挙動
  - 監視用テーブルの初期化 init_monitoring_db() を実行して存在を保証（冪等）。run_execution と run_monitoring の両方で起動時に呼び出し。

Fixed
- 環境変数パーサーの堅牢化
  - export 形式のサポートやクォート内のエスケープ処理、インラインコメントの取り扱いを改善し .env の互換性を向上。

- 安全なフォールバック・エラーハンドリング
  - run_monitoring のポーリングループで check_once() の例外をキャッチしてログ出力のうえ次回ポーリングへ継続。
  - process_priority / set_cpu_affinity が権限不足や未実装 API で失敗しても例外を投げず警告でスキップするように変更。

- research と portfolio の境界条件処理の改善
  - ファクター計算や ATR/MA 計算でデータ不足時に None を返すようにし、上位処理での None 扱いを明確化。
  - calc_score_weights で全スコアが 0.0 の場合に等金額配分へフォールバック。

Notes / Migration
- 環境変数名・デフォルトパス
  - デフォルトの DuckDB パス: data/kabusys.duckdb
  - デフォルトの 監視 SQLite パス: data/monitoring.db
  - Paper Trading 用デフォルト SQLite: data/paper_trading.db
  - 環境変数で上書き可能（詳細は kabusys.config.Settings の各プロパティ参照）

- 自動 .env 読み込み
  - デフォルトでプロジェクトルート（.git または pyproject.toml）を検出して .env/.env.local を読み込みます。
  - OS 環境変数を優先し、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化してください。

- Paper Trading の分離
  - KABUSYS_ENV=paper_trading の場合、run_execution は paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。Paper と本番 DB は完全分離を意図しています。

Known issues / TODO
- ai/news_nlp.py はファイル末尾で処理が途中終了している（fetch / send / write の続き実装が残っている箇所がある）。実運用前に残りのロジック（記事集約、API 呼び出しループ、DuckDB への安全な書き込み）を完成させてください。
- position_sizing の price フォールバック:
  - price_map に欠損（0.0）がある場合、エクスポージャーが過小評価される旨の TODO コメントあり。将来的に前日終値等のフォールバック実装を検討。

Security
- 外部 API キー（OpenAI 等）は環境変数で指定する設計。ログや出力に API キーを出力しないよう十分注意してください。

以上。