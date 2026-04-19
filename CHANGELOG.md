CHANGELOG
=========

フォーマット: Keep a Changelog 準拠（日本語訳）
- 各項目は重要な追加・変更・修正点をコードから推測して記載しています。
- 日付はリポジトリ内のコード状態に基づく推定日です。

Unreleased
----------
- なし

0.1.0 - 2026-04-19
------------------

Added
- 実行用スクリプトを追加/整備
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じてペーパートレード用の DB を分離（data/paper_trading.db を使用）し、BrokerClientFactory により実運用／モックを切り替え可能。エンジンは別スレッドで実行し、data/stop_requested.flag と data/execution.pid を利用して停止制御・PID 管理を行う。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。

- 設定・環境変数管理
  - config.py: Settings クラスを導入。.env 自動読み込み機能（プロジェクトルート検出基準: .git または pyproject.toml）、.env/.env.local の読み込み順序、OS 環境変数保護（上書き保護）を実装。各種設定（DB パス、PID/kill フラグ、しきい値、paper_trading 関連、ログレベル等）をプロパティ経由で提供し、値検証（有効値チェック）を行う。
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。シークレット項目はマスク表示、保存前に確認表示を行う。

- 起動前検証ツール
  - validate_config.py: .env と config/*.yaml（存在する場合）を検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV／LOG_LEVEL の妥当性チェック、DB パスや YAML パース検証、KABUSYS_ENV=live 時の追加ガードを実装。--strict オプションにより警告を FAIL 扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定（コンソール stdout と TimedRotatingFileHandler（日次・30日保持））を提供。LOG_DIR 作成失敗時はファイル出力をスキップしてコンソールのみで継続するフォールバックを実装。
  - utils/process_priority.py: クロスプラットフォーム（Windows/Linux/macOS 等）でプロセス優先度（high/normal/low）を設定するユーティリティ。CPU affinity 設定関数も提供。権限不足や未対応 OS 時は警告を出して安全にスキップする。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定 select_candidates、等分配 calc_equal_weights、スコア重み calc_score_weights を実装（同点タイブレークなどの仕様あり）。
  - portfolio/risk_adjustment.py: apply_sector_cap（セクター集中制限）と calc_regime_multiplier（市場レジームに応じた資金乗数）を実装。未知レジームに対するフォールバックとログ出力を備える。
  - portfolio/position_sizing.py: calc_position_sizes を実装。allocation_method（risk_based / equal / score）に基づく株数算出、単元株丸め、aggregate cap（可用現金に対するスケーリング）、cost_buffer（手数料・スリッページ見積り）考慮等のロジックを装備。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から指標（稼働率、注文成功率、送信率、レイテンシ等）を集計し、しきい値（稼働率 99% 等）で PASS/FAIL 判定するレポート生成スクリプトを追加。P95 計算、期間フィルタ、DB 存在チェックを実装。

- 監視 DB 初期化
  - monitoring.monitoring_db モジュール（呼び出しあり）を使い、起動時に監視テーブルが存在することを保証（冪等）。

- 研究モジュール（骨格）
  - research/factor_research.py: Momentum / Value / Volatility / Liquidity 等のファクター計算方針と定数を整備。DuckDB を用いた prices_daily/raw_financials ベースでの計算を想定。calc_momentum のインターフェースと設計を追加（実装の続きを予定）。

Changed
- デフォルト挙動・安全策の強化
  - .env 自動読み込みはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能とし、プロジェクトルート未検出時は自動ロードをスキップする動作を明示。
  - run_execution / run_monitoring の起動時にプロセス優先度を最初に設定するようにした（高優先度設定をデフォルトで実行）。

Fixed / Improved
- .env パーサの強化（config._parse_env_line）
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント扱いの厳密化などを実装。より多様な .env フォーマットの扱いを改善。
- logging_setup の堅牢化
  - 既存ハンドラを flush/close のうえクリアして再設定することで二重登録を防止。ログディレクトリ作成失敗時の挙動を明確化。
- validate_config の診断強化
  - PyYAML の有無を検出して YAML 検証をスキップするなど、環境に依存した判定を改良。live 環境での危険設定（LINE 未設定や KILL_FLAG_CLEAR_ON_START）に関する警告追加。

Security
- 機密情報（J-Quants / kabu API パスワード等）は .env 内でシークレット扱いを前提とするウィザードと README コメントを追加（.env を絶対に Git に含めないよう注意喚起）。

Known issues / TODO
- research/factor_research.calc_momentum の実装がファイル内で途中（ソース切れ）となっており、完全な実装が未着手。今後 DuckDB クエリと集計ロジックの実装が必要。
- position_sizing と risk_adjustment にて価格欠損（price が 0.0 または None）のフォールバックロジックは TODO コメントとして残存。前日終値や取得原価によるフォールバック実装が望まれる。
- set_process_priority / set_cpu_affinity は権限不足やプラットフォーム違いで失敗する可能性があるため、実行環境での権限確認が必要（既に警告での安全スキップを行う実装）。
- run_execution/run_monitoring の停止制御は file-flag ベース（data/stop_requested.flag / data/kill.flag 等）で行うため、外部プロセスや運用手順による管理を想定。クラスタ／コンテナ環境への適用時は追加のオーケストレーション対応が必要となる場合がある。

Notes / Migration
- .env の自動読み込みはプロジェクトルートの検出に依存するため、配布後やインストール後はルート検出が失敗する場面があり得る（その場合は手動で環境変数を設定するか KABUSYS_DISABLE_AUTO_ENV_LOAD を切り替えてください）。
- ペーパートレード用 DB は production DB と完全に分離される（Settings.paper_sqlite_path）。ペーパートレード検証を行う場合は PAPER_TRADING_SQLITE_PATH を指定するかデフォルトの data/paper_trading.db を利用してください。
- ログは既定で logs/<app_name>.log に日次ローテーションで出力されます。LOG_DIR 環境変数で変更可能。ログディレクトリ作成に失敗した場合はコンソール出力のみとなります。

Acknowledgements
- 初期リリース（0.1.0）として、実行/監視/設定管理/ポートフォリオ構築/検証ツールなど運用に必要な主要コンポーネントの雛形を揃えています。今後、研究モジュールの完成、テストの追加、エラー経路の詳細なハンドリングや性能検証を進めてください。