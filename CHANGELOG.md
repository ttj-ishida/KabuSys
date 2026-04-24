# Changelog

すべての注目すべき変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-24

### Added
- 基本アーキテクチャと起動スクリプトを実装
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV による paper_trading モードをサポートし、paper_trading 時は専用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。監視は環境にかかわらず本番 sqlite_path を使用。
- 設定管理周り
  - config.py: 環境変数ラッパー Settings クラスを実装。多くのプロパティ（J-Quants, kabu API, DB パス, ログ設定、監視閾値、環境判定等）と入力検証を備える。
  - 自動 .env ロード機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パーサの実装（export 形式・クォート・インラインコメント対応、上書き制御、保護対象キーの扱い）。
- 開発・運用用 CLI ツール
  - config_setup.py: 対話式ウィザードで .env を初期作成 / 更新するツールを追加。
  - validate_config.py: 起動前チェック CLI を追加。必須環境変数、KABUSYS_ENV、DB パス、config/*.yaml の存在と YAML パース（PyYAML がない場合は警告）などを検証。--strict オプションをサポート。
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を出力。日付フィルタ、DB パスの CLI オプションをサポート。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全ゼロ時は等分配にフォールバックして警告。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier を実装。未知レジームはフォールバックして警告を出力。
  - portfolio.position_sizing: position sizing 実装（risk_based / equal / score）。単元株（lot_size）丸め、per-position 上限・aggregate cap、スケーリングと端数配分ロジック、コストバッファ考慮を含む。
  - portfolio パッケージのエクスポートを整備。
- ユーティリティ
  - utils/logging_setup.py: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテート）を設定する共通ユーティリティを実装。LOG_DIR / LOG_LEVEL の解決順を定義。ログ重複設定防止のため既存ハンドラをクリアする。
  - utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度設定と CPU affinity 設定を実装（psutil を利用）。set_process_priority("high"/"normal"/"low") と set_cpu_affinity を提供。権限不足などの場合は警告を出してスキップ。
- Execution 周りの組み立てと安全機構
  - run_execution.py 内で BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てを実装。RiskConfig の既定値（max_position_pct 等）を設定。
  - 停止フラグ（data/stop_requested.flag 等）と pid ファイルを利用した起動/停止制御を実装。起動時に停止フラグがあれば起動を中止。
- DB 接続: sqlite3（監視・注文履歴）と DuckDB（分析用）を併用する設計を反映。monitoring 用テーブル初期化関数（init_monitoring_db）呼び出しを各起動点で行う（冪等）。
- research/factor_research.py: ファクター計算の土台（モメンタム、ATR、流動性等を想定する定数・設計方針）を追加（momentum 計算関数の実装開始あり。実装中の関数あり）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Known issues
- research.calc_momentum（factor_research.py の一部）はファイル末尾で途中実装のまま切れている可能性があります（今回提供されたコード断片内で未完）。追加のファクター計算は継続実装が必要です。
- 一部外部依存は任意（オプション）です:
  - duckdb: DuckDB 関連の機能（分析処理）に必須
  - psutil: process priority / cpu affinity に利用（無い場合は該当機能は警告してスキップ）
  - PyYAML: config/*.yaml のパース検証に利用（無い場合は検証をスキップして警告）
- .env の自動読み込みはプロジェクトルート検出に依存（.git または pyproject.toml）。プロジェクトルートが特定できない場合は自動ロードをスキップ。
- ログ出力は stdout を優先し、ファイル出力は logs/<app_name>.log に日次ローテーションで保存。ログディレクトリ作成失敗時はファイルハンドラを無効化してコンソール出力のみで継続。

### Security
- 本プロジェクトでは .env を絶対にコミットしないよう README / config_setup のヘッダで注意喚起済み。

---

開発者向けメモ:
- 初期リリースでは運用・検証用の CLI（設定ウィザード・検証・検証レポート）と、起動時の安全弁（停止フラグ、kill flag オプション）・プロセス優先度制御が整備されています。次フェーズでは research モジュールの完了、Strategy ↔ Execution の統合テスト、unit テストの充実、エラーハンドリングとリトライ戦略の拡張を推奨します。