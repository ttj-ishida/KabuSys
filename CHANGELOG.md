CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

（現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-23
-------------------

Added
- 初期リリース: KabuSys 自動売買システムの基本コンポーネントを追加。
- 環境設定 / ロード
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env のパースは quote/エスケープ、export プレフィックス、行内コメントを考慮して堅牢化。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 指定で自動ロードを無効化可能。
  - Settings クラスを追加し、環境変数（J-Quants / kabu API / DB パス / 各種閾値 等）をプロパティ経由で取得。
  - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等の入力値検証を実装（不正値は例外）。
- 設定関連 CLI
  - config_setup: 対話式ウィザードで .env を作成・更新する CLI を追加。
  - validate_config: .env と config/*.yaml の検証 CLI を追加（--strict オプションで警告を FAIL 扱いにできる）。
  - validate_config は PyYAML がない場合は YAML 検証をスキップし、適切に警告を出力。
- 実行スクリプト
  - run_execution: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用し本番 DB と分離。
    - BrokerClientFactory 経由で実際/モックのブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）による安全停止をサポート。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告のうえデフォルトにフォールバック。
    - 監視は設定にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグでループを抜ける仕組みを採用。
- ロギング / プロセス制御ユーティリティ
  - utils.logging_setup: stdout への StreamHandler（標準出力）と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）を組み合わせて統一的なログ設定を提供。ログディレクトリ作成に失敗してもコンソール出力で継続。
  - utils.process_priority: psutil を利用したクロスプラットフォームなプロセス優先度設定（high/normal/low）と CPU affinity 固定ユーティリティを実装。未対応 OS や権限不足時は警告してスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群: DB 非依存）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのソート（スコア降順、タイブレークに signal_rank）と上位 N 選出。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア比率に基づく配分（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限を適用し、上限を超えるセクターの新規候補を除外。
    - calc_regime_multiplier: 市場レジームに応じた乗数（bull/neutral/bear）を返す。未知レジームは警告のうえ 1.0 フォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: 等配分/スコア配分/リスクベース配分に対応した株数計算。単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金を超える場合は縮小）を実装。cost_buffer を用いた保守的なコスト見積りと余り配分ロジックを実装。
- ツール
  - tools.paper_verification_report: ペーパートレード用検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs を集計し、稼働率、注文成功率・送信率、P95 レイテンシ等を算出。閾値判定（PASS/FAIL）を実装。DB パスは引数または PAPER_TRADING_SQLITE_PATH で指定可能。
- 研究モジュール（factor_research）
  - DuckDB を使ったファクター計算の枠組みを追加（モメンタム/ボラティリティ/Value/流動性 等を想定）。calc_momentum 等の関数スケルトンと定数を実装（詳細実装はモジュール内に続く実装を想定）。

Changed
- パッケージの __version__ を 0.1.0 に設定。

Fixed / Hardened
- .env ロード時に OS 側の既存環境変数を protected として上書きを防止する仕組みを導入（.env.local は上書き対象だが OS 環境変数は保護）。
- logging_setup: ログディレクトリ作成失敗時にファイルハンドラ作成をスキップし、コンソール出力にフォールバックするよう改善。
- process_priority: 未対応プラットフォームまたは権限不足時に例外で落ちないように警告ログでスキップするように改良。
- run_monitoring/run_execution: 停止フラグ（data/stop_requested.flag）や実行 PID 管理（execution.pid）を組み込み、安全停止/二重起動検知に配慮。

Notes / Known issues
- research.factor_research.calc_momentum 等、一部研究系関数は枠組みは整っているもののファイル末尾で実装が途中（スニペットが途中で終わっている）に見えるため、完全実装は今後の作業を要する。
- SystemMonitor の監視 DB は設計上「監視は常に本番 sqlite_path を使用する」ため、環境に依らず本番監視 DB を参照します（意図的な設計か確認が必要）。
- position_sizing の price フォールバック（価格データ欠損時の扱い）に関する TODO コメントあり。価格欠損時にエクスポージャーが過小評価される可能性があるため将来の改善を検討。
- 一部外部パッケージ（psutil, duckdb, PyYAML など）に依存。環境によってはインストールが必要。

Authors
- コードベース中の実装内容に基づき自動生成された CHANGELOG（推測を含む）。実際のコミット履歴や変更理由はリポジトリの VCS 履歴を参照してください。