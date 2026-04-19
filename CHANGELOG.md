# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
慣例: "Added", "Changed", "Fixed", "Removed", "Deprecated", "Security" のセクションを使用しています。

## [Unreleased]

## [0.1.0] - 2026-04-19
初期リリース。

### Added
- 実行エントリスクリプトを追加
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。プロセス優先度を設定し、BrokerClientFactory を用いてブローカークライアントを生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をデーモンスレッドで走らせる。停止フラグ (data/stop_requested.flag) による安全な終了処理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する仕様。

- 設定管理 / 初期化ツール
  - config.py: 環境変数読み込み・ラッパー Settings クラスを追加。自動でプロジェクトルートの .env / .env.local を読み込み（OS 環境変数は保護）。各種設定値（DB パス、KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）をプロパティで取得・検証。
  - config_setup.py: 対話式ウィザードで .env を作成/更新する CLI を追加。既存値の読み込み、シークレットマスク表示、保存確認などを実装。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。必須環境変数存在チェック、KABUSYS_ENV の妥当性、ログレベル、DB パス、YAML パース検証 (PyYAML がなければ警告) や live 環境向けのガードチェックを実装。--strict モードで警告を失敗扱いにできる。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。スコア全てが 0 の場合は等金額にフォールバックする警告を追加。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、および市場レジームに応じた資金乗数 calc_regime_multiplier を追加（未知のレジームはフォールバックで警告）。
  - portfolio/position_sizing.py: position sizing ロジックを追加。risk_based / equal / score の割当方式をサポートし、lot_size（単元株）丸め、max_position_pct / max_utilization の制約、cost_buffer を考慮した aggregate cap スケーリングを実装。端数処理や残余キャッシュの分配ロジックも含む。
  - portfolio パッケージの __init__ で上記関数をエクスポート。

- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。StreamHandler は stdout に出力、TimedRotatingFileHandler で日次ローテーション（30日保持）する。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度設定と CPU affinity 設定機能を追加。Windows / POSIX(Linux/Mac/FreeBSD) に対応し、権限不足や未対応 OS の場合は警告を出してスキップする。

- モニタリング関連
  - monitoring.monitoring_db の初期化呼び出しを run_monitoring/run_execution 両方で行い、監視テーブルの存在を起動時に保証（冪等）。

- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。指定期間の system_status / trade_logs / risk_logs から稼働率、注文成功率・送信率、レイテンシ（平均/最大/P95）等を集計し PASS/FAIL 判定を出力。閾値（稼働率 99%、成立率 90% 等）はスクリプト内定義。--from / --to / --db オプションをサポート。

- 研究用ファクターモジュール
  - research/factor_research.py: DuckDB 接続を受け取り、モメンタム等の定量ファクターを計算するための骨格を追加（モメンタム計算関数 calc_momentum の実装開始、定数や設計方針を定義）。

### Changed
- 環境変数読み込みの挙動:
  - config.py: .env/.env.local の自動ロード順序を OS 環境変数 > .env.local > .env として実装し、OS 環境変数を上書き禁止（protected）にした。
  - .env の行パースで export プレフィックスやクォート、エスケープ、インラインコメントを考慮する堅牢な実装に変更。

- ログ設定のデフォルト:
  - logging_setup.py: デフォルトログディレクトリやローテーション設定、stdout 出力への統一などを明確化。

### Fixed
- run_monitoring.py / run_execution.py の堅牢性向上:
  - run_monitoring.py: check_once() 内での例外をキャッチして次のポーリングへ安全に継続するようにし、停止フラグ検知でクリーンにループを抜ける処理を実装。
  - run_execution.py: ExecutionEngine を別スレッドで実行し、停止フラグ検知時に engine.stop() を呼んで安全に終了する仕組みを追加。起動時に停止フラグが既にある場合は起動せず終了する。

### Security
- 環境変数のシークレット扱い:
  - config_setup のウィザードはシークレット入力をマスク表示し、.env ファイルに書き出す際に注意喚起を追加（.env を Git にコミットしない旨の注記）。

### Notes / Known limitations
- research/factor_research.py はモメンタム等の計算ロジックの実装途中（ファイル末尾が途中で切れている）。完全な実装は今後のリリースで追加予定。
- position_sizing の価格欠損時の挙動（price が 0.0 の場合の過少評価）について TODO コメントあり。将来的にフォールバック価格を導入する可能性がある。
- PAPER_FILL_MODE の妥当性チェックは Settings で行われる（有効値: instant, partial, never, reject）。不正な値は起動時に例外となる。

---

（以降のリリースでは各モジュールの詳細な変更点・バグ修正・性能改善・API 互換性の情報を追記してください。）