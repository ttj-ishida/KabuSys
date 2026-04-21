# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベース（src/kabusys/*）の内容から推測して作成した変更履歴です。

## [Unreleased]

### Added
- 起動スクリプトを追加
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV に応じて paper_trading 用 DB を分離し、MockBrokerClient の利用をサポート。スレッドでエンジンを実行し、 data/stop_requested.flag による安全停止をサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書きをサポート。監視用 DB は環境に依らず本番 sqlite_path を使用。
- 設定関連・ユーティリティを追加
  - config.py: .env 自動読み込み機構（.env / .env.local）、環境値検証（KABUSYS_ENV, LOG_LEVEL 等）、各種設定プロパティ（DB パス、paper_trading 用パス、閾値など）を実装。
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を実装。
  - validate_config.py: .env と config/*.yaml の起動前検証 CLI を実装。--strict オプションをサポート。
- ロギング・プロセス管理
  - utils/logging_setup.py: StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。ログ出力ディレクトリ作成失敗時はファイルハンドラをスキップして警告を出力するフォールバック実装を追加。
  - utils/process_priority.py: Windows / POSIX の差分を吸収してプロセス優先度設定（high/normal/low）を実装。CPU affinity 設定関数 set_cpu_affinity を追加。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、タイブレーク）、等金額配分、スコア加重配分（スコアが全て0の場合はフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター別集中制限適用ロジック（セクター露出計算、除外）、市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（unknown レジームはフォールバック）。
  - portfolio/position_sizing.py: position サイズ計算（risk_based / equal / score）、単元株（lot_size）丸め、aggregate cap によるスケールダウン、残余キャッシュに対する端数配分ロジックを実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite DB を解析して稼働率、注文成功率、送信率、レイテンシ指標（P95 など）を計算・レポート出力する CLI。閾値による PASS/FAIL 判定を実装。
- 研究用ファクター計算（骨格）
  - research/factor_research.py: ファクター計算モジュールの設計と定数定義（Momentum/Value/Volatility/Liquidity 等）を追加。DuckDB 接続を受けて prices_daily / raw_financials を参照する方針を記載。モメンタム計算関数の実装（途中）あり。

### Changed
- ログ出力の挙動調整
  - stdout を標準出力に使うことで cron / Task Scheduler 等で stdout/stderr を一本化してリダイレクトしやすくした。
- DB パスの取り扱い
  - ExecutionEngine は paper_trading モード時に paper_sqlite_path を用いて本番 DB と分離するように明示。

### Fixed
- .env パースの堅牢化
  - config._parse_env_line にてシングル/ダブルクォート内のバックスラッシュエスケープ対応およびインラインコメント処理（クォートありは以降無視、クォートなしは '#' の直前が空白/タブであればコメントとして扱う）を実装し、より現実的な .env フォーマットに対応。

### Deprecated
- なし

### Security
- なし

---

## [0.1.0] - 2026-04-21

初回公開リリース（推定）。上記 Unreleased の機能群を包含するベースラインリリースとして記載。

### Added
- パッケージメタ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
- すべての機能（上記 Unreleased の各項目を含む）が初期実装として追加。

### Known issues / Notes
- research/factor_research.py の calc_momentum 関数実装は途中で終端しており、完全実装が必要（今後の作業）。
- position_sizing.calc_position_sizes 内の price 欠損時の挙動に TODO コメントあり（フォールバック価格の検討）。
- logging_setup でログディレクトリ作成に失敗した場合はファイル出力を無効化しているため、ディスク権限等でログファイルが作れない環境ではファイルログが得られない点に注意。
- process_priority.set_cpu_affinity / nice の呼び出しは権限に依存するため、一般ユーザー権限では実行できない場合がある（警告を出してスキップ）。

---

（注）この CHANGELOG は与えられたソースコードの内容から推測して作成したものであり、実際のコミット履歴やリリースノートとは異なる場合があります。必要であれば実際の変更履歴や Git のコミットログに基づいて調整できます。