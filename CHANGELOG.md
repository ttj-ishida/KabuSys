# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
日付/バージョンはコードの内容から推測して記載しています。実際のリリース履歴とは異なる可能性があります。

## [Unreleased]

### Added
- 環境変数読み込みの堅牢化
  - `.env` / `.env.local` の自動ロード機能を実装（プロジェクトルート自動検出、OS環境変数保護、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
  - クォート付き／エスケープおよびインラインコメントに対応した .env パーサーを導入（export 形式にも対応）。
- 設定ウィザード CLI を追加（kabusys.config_setup）
  - 対話式で .env を作成・更新するウィザードを実装。
  - シークレット項目のマスク表示、選択肢／デフォルト値対応、保存前の確認をサポート。
- 設定検証 CLI を追加（kabusys.validate_config）
  - 必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在と YAML パース検証、live 環境向けのガードチェックを実施。
  - --strict オプションで警告も失敗扱いに可能。
- ログ設定ユーティリティを追加（kabusys.utils.logging_setup）
  - stdout への StreamHandler + 日次ローテートするファイルハンドラをルートロガーに統一的に設定。
  - ログディレクトリ自動作成（失敗時はファイル出力をスキップして stdout のみで継続）。
- プロセス優先度・CPU affinity ユーティリティを追加（kabusys.utils.process_priority）
  - Windows / POSIX を吸収する set_process_priority, set_cpu_affinity を実装。権限不足時に警告を出して安全にフォールバック。
- 実行系起動スクリプトを追加（run_execution）
  - ExecutionEngine を起動するエントリポイント。プロセス優先度設定、PID 管理、停止フラグ検知による安全な停止。
  - paper_trading 環境では MockBrokerClient を使用し、paper 専用 SQLite（data/paper_trading.db をデフォルト）で本番 DB と完全分離。
  - リスク管理（RiskManager）初期化、および Reconciler / OrderManager の組み立てを行う。
- 監視系起動スクリプトを追加（run_monitoring）
  - SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止フラグファイルによる終了、例外発生時のログ捕捉と待機ループ継続を実装。
  - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
- Paper Trading 検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）
  - paper_trading DB から稼働率、注文成功率、送信率、レイテンシ指標を集計し PASS/FAIL レポートを出力。
  - P95 計算、期間フィルタ、閾値判定ロジックを備える。
- ポートフォリオ構築・ポジション計算モジュールを追加（kabusys.portfolio）
  - 候補選定（select_candidates）、等重/スコア重み（calc_equal_weights / calc_score_weights）。
  - セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）。
  - 株数決定ロジック（calc_position_sizes）: risk_based / equal / score の配分方式、lot 単位丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した安全な配分。
- リサーチ（factor 計算）モジュールの骨組みを追加（kabusys.research.factor_research）
  - DuckDB 接続を受ける設計、モメンタム / MA200 / ATR / 流動性等の計算方針・定数を実装（実装途中の関数あり）。
- パッケージメタ情報を追加（kabusys.__init__ に __version__）

### Changed
- .env の読み込み順序と保護
  - OS 環境変数を保護しつつ .env/.env.local を読み込む仕様により、ローカル設定と CI/本番環境の分離を強化。
- ロギング動作
  - stdout を StreamHandler に使用する（stderr ではなく）。cron 等で stdout/stderr を一本化する運用に配慮。
- DB パスの扱い
  - Execution 起動時に paper_trading 環境は paper 専用 SQLite を使用するよう明示的に分離。

### Fixed
- .env パーサーのコメント／クォートの不具合を改善（エスケープ処理の明確化、export プレフィックス対応）。
- 起動スクリプトのリソースクローズ漏れを防止（finally ブロックで SQLite/DuckDB 接続を確実に close）。

---

## [0.1.0] - 2026-04-19 (Initial release; コードベースから推測した最初の機能セット)

### Added
- 初期実装として以下の主要コンポーネントを実装・公開:
  - 環境設定と読み込み
    - Settings クラスによる環境変数取得・検証（KABUSYS_ENV, LOG_LEVEL, 各種パス, PAPER_FILL_MODE など）。
    - 自動的な .env / .env.local 読み込み（プロジェクトルート自動検出）。
  - 起動スクリプト
    - run_execution: ExecutionEngine の起動と停止管理、paper_trading の DB 分離。
    - run_monitoring: SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL 対応）。
  - ユーティリティ
    - logging_setup: 統一的なログ設定（コンソール + 日次ローテートファイル）。
    - process_priority: プロセス優先度と CPU affinity 設定ユーティリティ。
  - 設定支援ツール
    - config_setup: 対話式 .env ウィザード。
    - validate_config: 起動前の設定検証 CLI（YAML パース確認含む）。
  - ポートフォリオ・ポジション管理
    - portfolio_builder, risk_adjustment, position_sizing モジュール（候補選定、重み付け、セクターキャップ、レジーム乗数、株数決定）。
  - Paper Trading 検証ツール
    - tools.paper_verification_report: 検証レポート生成（稼働率、成功率、レイテンシ等）。
  - リサーチモジュールの基盤（factor_research）を追加（DuckDB を用いたファクター計算設計）。
  - パッケージの __version__ を "0.1.0" に設定。

### Changed
- なし（初回リリースのため差分なし）。

### Fixed
- なし（初回リリースのため差分なし）。

---

その他の注記
- 設計上の注意点や TODO がコード内コメントとして残されています（例: price が欠損した場合のフォールバック、銘柄ごとの lot_size 拡張など）。実運用前にこれらの点を確認・補完することを推奨します。
- factor_research モジュールは設計方針・定数が整備されていますが、関数実装が途中で切れている箇所が見られます。ファクター計算を利用する場合は実装完了を要確認してください。

もし実際のコミット履歴・リリース日・担当者情報などを反映した正確な CHANGELOG を作成したい場合は、git の履歴やリリースノートの情報を提供してください。