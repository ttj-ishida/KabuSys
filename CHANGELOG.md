# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
このファイルはコードベースから推測して作成した変更履歴です（実装コメントやファイル構成に基づく要約）。バージョン管理履歴が存在しない場合の初期リリース向けの記述を含みます。

注意: 環境変数・ファイルパスなどのデフォルト値はソース中のコメント／実装から推測しています。

## [Unreleased]

### Added
- 開発用の Python パッケージ「KabuSys」のコアモジュールを追加。
  - バージョン: 0.1.0 相当（src/kabusys/__init__.py に定義）。
- 起動スクリプトを追加:
  - run_monitoring.py: SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 専用 DB（data/paper_trading.db）に記録して本番 DB と分離。
- 設定管理・補助ツール:
  - config.py: .env 自動ロード機能（プロジェクトルート検出）と Settings クラスを提供。多くの環境変数を扱う（J-Quants トークン、kabu API、DB パス、監視閾値、環境区分 等）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - config_setup.py: 対話式 .env 作成／更新ウィザードを追加（.env の雛形生成・更新支援）。
  - validate_config.py: 起動前の設定検証 CLI を追加（必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在と YAML パースの検証など）。--strict モードあり（警告を FAIL 扱い）。
- 実用ユーティリティ:
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティ（console stdout と日次ローテートファイルハンドラ）。ログディレクトリ作成失敗時はファイル出力をスキップするフォールバックあり。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティ（Windows / POSIX を吸収）。優先度レベル("high"/"normal"/"low") をサポート。
- ポートフォリオ構築関連モジュール（純粋関数群）:
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。
  - portfolio/risk_adjustment.py: セクター集中制限 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier)。未知レジームはフォールバック動作あり。
  - portfolio/position_sizing.py: 発注株数計算ロジック（risk_based / equal / score）、単元株丸め、aggregate cap によるスケールダウン、手数料スリッページのバッファ考慮。
- Execution 周りの骨組み（起動スクリプトから組み立てられるコンポーネント）を追加（ファクトリ／マネージャ／エンジン呼び出し箇所を含む）:
  - execution.* で BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等を組み合わせて起動。
  - RiskConfig のデフォルト値（max_position_pct=0.20 等）を定義し、初期 available_cash を broker.get_available_cash() から取得して使用。
- 監視 DB 初期化機能（init_monitoring_db の呼び出し）を run_monitoring/run_execution 両方で行い、監視テーブルの存在を保証（冪等）。
- 分析用 DuckDB の利用を全体で導入（Settings.duckdb_path）。起動スクリプトは duckdb 接続を確立。
- ツール:
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツール。稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を計算し PASS/FAIL を判定。PAPER_TRADING_SQLITE_PATH で DB を指定可能。
- research/factor_research.py の骨組みを追加（ファクター計算の設計・定数・calc_momentum 等の実装開始。DuckDB を参照する設計）。

### Changed
- n/a（初期導入のため履歴なし）

### Fixed
- n/a（初期導入のため履歴なし）

### Removed
- n/a

### Security
- n/a

## [0.1.0] - 2026-04-19

初回公開リリース（ソースコードの現在状態を反映）。

### Added
- 上記「Unreleased」に記載した全機能を最初のリリースとして追加。
  - 起動スクリプト、設定管理、検証ツール、ウィザード、ロギング・プロセスユーティリティ、ポートフォリオ構成ロジック、Execution の組み立て箇所、Paper Trading レポートツール、研究モジュール骨子など。

### Known issues / Notes
- research/factor_research.calc_momentum の実装が途中で切れている（ファイル末尾が不完全）。ファクター計算機能は現状で完全ではない可能性あり。
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損して price=0.0 の場合、エクスポージャーが過小評価される旨の TODO コメントあり。将来的に前日終値や取得原価でフォールバックする必要あり。
- logging_setup:
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップし、コンソール出力のみで継続する。運用環境ではログディレクトリのパーミッション・存在を事前に確認すること。
- process_priority / set_cpu_affinity:
  - 権限（root / 管理者）がない場合やプラットフォーム差異で設定に失敗する可能性があり、その場合は警告を出してスキップする。
- 停止制御:
  - run_monitoring / run_execution はプロジェクト内の data/stop_requested.flag（あるいは環境での指定パス）を使って停止検知を行う。運用時は stop/kill フラグの取り扱いに注意してください。
- validate_config:
  - PyYAML が無い場合は config/*.yaml のパース検証をスキップする（警告）。CI／本番環境では PyYAML をインストールすることを推奨。
- 環境自動ロード:
  - .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行うが、見つからない場合はスキップする。テスト環境などで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

### Upgrade / Migration
- 既存環境から本パッケージを導入する際は以下を実行して設定を確実に整備してください:
  1. python -m kabusys.config_setup で .env を作成／更新
  2. python -m kabusys.validate_config で設定を検証（本番では --strict 推奨）
  3. 必要に応じて DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH のパスを確認
- Paper Trading を実行する場合、KABUSYS_ENV=paper_trading を設定すると broker は MockBrokerClient を使用し、データは paper_trading 用 DB に分離される（本番 DB とは完全分離）。

---

過去のリリース履歴がないため、この CHANGELOG は初期リリースに相当する内容をまとめたものです。将来的な差分は本ファイルの上部に Unreleased セクションを追加し、変更ごとに記録してください。