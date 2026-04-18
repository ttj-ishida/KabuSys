# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

なお、本リリースはコードベースから推測して作成した初期リリースノートです（自動生成ではなく手作業による推測記述）。

## [0.1.0] - 2026-04-18

### Added
- 基本アーキテクチャと起動スクリプトを追加
  - run_execution.py: ExecutionEngine の起動用スクリプトを追加。KABUSYS_ENV に応じて paper_trading 用 DB を分離して使用（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。停止フラグ・PID ファイル処理、スレッド実行ループを実装。
  - run_monitoring.py: SystemMonitor を定期ポーリングする起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
- 設定管理・自動環境ロード
  - config.py: .env ファイル（.env, .env.local）自動読み込み機能を追加。プロジェクトルートの検出は .git または pyproject.toml を使用。環境変数の取得用 Settings クラスを提供し、各種設定プロパティ（DB パス、ログレベル、閾値、paper 設定等）を実装。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。必須項目やデフォルト値、シークレット入力に対応し、.env を生成/更新可能。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML 利用時）および live 環境向けのガードチェックを実装。--strict オプションを追加（警告を FAIL 扱いにできる）。
- ポートフォリオ構築ライブラリ
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等分配・スコア加重（calc_equal_weights / calc_score_weights）を実装。スコアが全て 0 の場合は等配分にフォールバック。
  - portfolio.position_sizing: 各銘柄の発注株数算出ロジック（risk_based / equal / score）を実装。単元株（lot_size）丸め、1 銘柄上限、aggregate cap のスケーリング、コストバッファ対応、残差に基づく追加配分ロジック等を実装。
  - portfolio.risk_adjustment: セクター集中の上限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知のセクターやレジーム時のフォールバック動作を定義。
  - portfolio パッケージの __all__ エクスポートを整備。
- ユーティリティ
  - utils.logging_setup: 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と日次ローテートの TimedRotatingFileHandler をルートロガーに設定。ログレベル・ログディレクトリの解決順を定義し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils.process_priority: Windows / POSIX を吸収したプロセス優先度設定と CPU affinity 設定を追加（psutil を利用）。アクセス拒否などは警告でスキップ。
- 分析・検証ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成ツールを追加。システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計し PASS/FAIL 判定を行う。閾値（稼働率 99%、注文成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
- リサーチモジュール（部分実装）
  - research.factor_research: ファクター計算モジュールの骨子を追加。モメンタム、バリュー、ボラティリティ、流動性などの計算方針・定数を定義。DuckDB 接続を前提とした設計。

### Changed
- ログ出力の標準ストリームを stderr ではなく stdout に統一（utils.logging_setup）。cron や Task Scheduler からのリダイレクト時の取り扱いを考慮。
- DB 周りの扱いを明確化
  - run_execution: paper_trading の場合は paper 用 SQLite を使用し本番 DB と完全分離する設計に。init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。
  - run_monitoring: 監視は常に本番 sqlite_path を使用する設計に。

### Fixed
- .env パーサの改善（config._parse_env_line）
  - export プレフィックス対応、シングル/ダブルクォート中のバックスラッシュエスケープ対応、インラインコメントの扱いを改善。クォートなしのコメント判定ロジックを追加。
- Settings クラスの入力検証追加
  - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）。不正な値は ValueError を送出。
  - KABUSYS_ENV と LOG_LEVEL の値検証を厳格化し、不正な値は ValueError（早期検出）。
- process_priority のプラットフォームフォールバックを堅牢化（Windows 定数の getattr フォールバック、サポート外 OS は警告）。

### Documentation / UX
- 各 CLI モジュール（config_setup, validate_config, paper_verification_report）にヘルプ・使用例を追加。config_setup は生成される .env のテンプレートヘッダ・注意書きを出力。
- ログ設定でディレクトリ作成に失敗した場合に標準エラー出力で警告を表示し、ファイルハンドラをスキップする挙動を文書化。

### Notes / Implementation details
- run_monitoring.py はプロセス優先度を先に High に設定し、MONITOR_POLL_INTERVAL（環境変数）でポーリング間隔を上書き可能。0 以下や不正な値はデフォルト 60 秒にフォールバックして警告を出力。
- run_execution.py は RiskManager のデフォルト設定（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を設定し、初期ポートフォリオ値は broker.get_available_cash() を使用。
- position_sizing の aggregate cap スケーリングでは小数端数の再配分を lot_size 単位で行い、再現性のためにコードを二次キーに用いるソート安定化を実施。
- apply_sector_cap は sector_map に存在しない銘柄を "unknown" として扱い、unknown セクターはセクター上限適用対象外（除外しない）。
- validate_config の config YAML 検証は PyYAML 未インストール時にスキップし、その旨を警告する。

### Removed
- なし（初期リリースのため該当なし）。

### Security
- 環境変数読み込みで OS の既存環境変数を保護する仕組み（protected set）を導入。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

---

今後の予定（例）
- research.factor_research の完全実装（価格テーブル参照ロジック、Zスコア正規化等）
- strategy / execution の詳細実装・テストカバレッジ強化
- 単体テスト・統合テストの追加、CI ワークフロー整備
- Windows/Linux 両対応の運用ドキュメント追記

もし CHANGELOG に追加したい点（リリース日や抜けがある機能の強調など）があれば指示してください。