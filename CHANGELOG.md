CHANGELOG
=========

すべての変更点をこのファイルに記録します。フォーマットは Keep a Changelog に準拠しています。

Unreleased
----------

- なし

0.1.0 - 2026-04-19
------------------

Added
- 初期リリース: KabuSys 基本コンポーネントを追加。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、BrokerClientFactory を用いたブローカー抽象化、OrderRepository/OrderManager/RiskManager/Reconciler 等の組み立て、停止フラグによる安全停止を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能、停止フラグでの優雅な終了、監視用 DB（SQLite）と DuckDB の接続を行う。
- 設定管理
  - config.py: .env 自動ロード機構（プロジェクトルート検出 .git / pyproject.toml）、堅牢な .env パース（export、クォート、インラインコメント対応）、Settings クラスによる環境変数アクセスを実装。各種設定プロパティ（DB パス、KABUSYS_ENV、ログレベル、Paper Trading 関連、しきい値等）を提供。
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を追加。
  - validate_config.py: 起動前に .env と config/*.yaml の基本チェックを行う設定検証 CLI を追加（--strict オプション対応）。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）と配分重み計算（等金額 calc_equal_weights、スコア加重 calc_score_weights）を追加。スコア全0 時は等金額にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py: セクター集中上限適用（apply_sector_cap）と市場レジームに基づく投下資金乗数（calc_regime_multiplier）を追加。未知レジームは警告を出して 1.0 にフォールバック。
  - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score 対応）、単元株丸め、単銘柄上限・aggregate cap（available_cash）に基づくスケーリング、cost_buffer（手数料・スリッページ想定）反映、残差分の lot 単位での追加配分ロジックを実装。
  - portfolio パッケージのエクスポート設定を提供。
- 解析 / リサーチ
  - research/factor_research.py: DuckDB 接続を受けてモメンタム等のファクターを計算するモジュールを追加（関数群の実装開始。prices_daily/raw_financials に依存）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。期間フィルタ、稼働率・注文成功率・送信率・レイテンシ（P95 含む）等を計算して PASS/FAIL 判定を行う。閾値はソースに定義 (稼働率99%、成功率90% 等)。
- ユーティリティ
  - utils/logging_setup.py: 共通ログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分を吸収し、権限不足・未対応 OS の場合は警告を出してスキップする。

Changed
- なし（初期リリース）

Fixed
- run_monitoring のポーリング間隔取得で不正値が指定されても ValueError を投げずデフォルトにフォールバックするように実装（MONITOR_POLL_INTERVAL の堅牢化）。
- logging_setup: ログディレクトリ作成に失敗した場合でもアプリケーションが起動を続行できるように設計（ファイルハンドラ作成失敗は警告、コンソール出力は維持）。
- process_priority: 未対応 OS や権限不足を丁寧に扱い、例外ではなく警告でスキップするように改善。
- calc_score_weights: 全銘柄のスコア合計が 0 の場合に等金額配分にフォールバックして WARNING を出力（ゼロ除算回避）。
- apply_sector_cap: セクター未定義（unknown）の扱いは上限適用対象外とし、誤って除外されるのを防止。
- calc_position_sizes: 価格未取得（None または <=0）の銘柄をスキップして安全に動作するように調整。aggregate cap でスケーリングする際の残余配分ロジックを実装してより再現性のある配分を実現。

Security
- なし

Deprecated
- なし

Removed
- なし

Notes / 備考
- Paper Trading と本番（live）の DB を明確に分離（Settings.paper_sqlite_path / Settings.is_paper を活用）。run_execution は paper_trading 環境で専用 DB を使用するよう設計されているため、本番 DB とペーパートレードデータは完全分離される。
- stop flag / kill switch: プロセスを安全に停止するために data/stop_requested.flag（プロジェクト直下の data ディレクトリを想定）による停止検知を各実行スクリプトで採用。
- .env 自動ロード: OS 環境変数を保護（既存 OS 環境変数は上書きされない）し、.env.local を .env の上からオーバーライドできる。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
- validate_config は PyYAML が未インストールの場合に YAML 検証をスキップして警告を出す。config/*.yaml のテンプレート生成方法の案内も含む。

今後の予定（候補）
- research/factor_research の完全実装（欠損ハンドリング、Zスコア正規化統合）。
- Strategy / Execution の単体テスト追加と CI ワークフロー整備。
- 銘柄ごとの lot_size をマスタ化して position_sizing を拡張。
- より詳細な監視メトリクスとアラート送信（LINE 等）連携の強化。