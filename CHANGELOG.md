# Changelog

すべての重要な変更履歴を記載します。本ファイルは Keep a Changelog の形式に準拠しています。  

なお、内容はリポジトリ内のコードを参照して推測した初期リリース向けのまとめです。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-24

### Added
- 初期リリース: KabuSys 0.1.0 を公開。
- コア機能
  - 実行エンジン (execution)
    - 起動スクリプト run_execution.py を提供。KABUSYS_ENV に応じて本番 DB／ペーパートレード用 DB を切り替え、BrokerClientFactory を使用してブローカー接続を作成、ExecutionEngine をスレッドで起動して監視・停止フローを実装。
    - エンジン用の各コンポーネントを組み立てる OrderRepository / OrderManager / RiskManager / Reconciler を実装。
    - paper_trading モードでは MockBrokerClient を使用し、data/paper_trading.db に記録することで本番 DB と完全分離。
  - 監視モジュール (monitoring)
    - 起動スクリプト run_monitoring.py を提供。SystemMonitor をポーリングで定期実行し、stop フラグで安全に終了。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用して接続・初期化。
  - 設定管理
    - Settings クラスを実装。環境変数・.env 自動読み込み（.env / .env.local、OS 環境変数の保護）と各種プロパティ（パス、閾値、env 判定、paper_trading 用パス等）を提供。
    - .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - CLI ツール
    - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援。
    - validate_config.py: .env と config/*.yaml の起動前検証ツール（--strict による警告の FAIL 扱い）。
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツール。稼働率・注文成功率・送信率・レイテンシ（P95）等を出力。閾値による PASS/FAIL 判定を実装。
  - ポートフォリオ構築ライブラリ (portfolio)
    - portfolio_builder: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全ゼロ時のフォールバック警告あり。
    - risk_adjustment: セクター集中上限適用 (apply_sector_cap)、市場レジームに基づく投下資金乗数 (calc_regime_multiplier) を実装（レジーム不明時はフォールバック）。
    - position_sizing: 各銘柄の発注株数算出ロジックを実装。allocation_method（"risk_based", "equal", "score"）に対応し、lot_size（単元）丸め、max_position_pct、max_utilization、aggregate cap（利用可能現金を超える場合のスケールダウン）と残差の扱いを考慮。
  - 研究（research）モジュール
    - factor_research モジュール雛形を追加。DuckDB 接続を受け、Momentum / Value / Volatility / Liquidity などのファクター計算を行う設計（prices_daily / raw_financials を前提）。
  - ユーティリティ
    - logging_setup: 統一的なログ設定ユーティリティを追加。stdout へ出力する StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせ、LOG_DIR / LOG_LEVEL の解決・ディレクトリ作成失敗時のフォールバックなどを実装。
    - process_priority: プロセス優先度（Windows/Linux の差分吸収）と CPU affinity 設定ユーティリティを提供。psutil の権限エラー等を安全にハンドリング。
  - DB 統合
    - sqlite3 と duckdb を用途別に併用（monitoring は sqlite、分析等に duckdb）。
  - 停止制御 / PID 管理
    - data/stop_requested.flag を用いた外部停止フラグに対応。エンジン・監視プロセスがフラグ検知で安全に終了する仕組みを実装。実行時の PID ファイル管理（pid_file path）に対応。

### Changed
- （初回リリースのため該当なし）

### Fixed / Hardened
- .env パーサーで実際の shell 風の記法に近い扱いを実装
  - export プレフィックスに対応
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理を考慮
  - クォート無しの値でインラインコメントを適切に扱う（# の前に空白がある場合のみコメント扱い）
  - 読み込み失敗時に警告を出して継続する安全設計
- run_monitoring の MONITOR_POLL_INTERVAL 読み取りで不正値を検出した場合にデフォルトへフォールバックし警告を出すように改善
- logging_setup でログディレクトリ作成失敗時にファイル出力をスキップして stdout のみで継続するフォールバックを導入
- process_priority / set_cpu_affinity は権限不足や未対応 OS に対して警告を出して安全にスキップする実装

### Known issues / Notes
- research/factor_research.py はファイル末尾が途中のように見受けられ、ファクター計算の一部が未完（WIP）。本リリースでは設計・雛形を含む。
- position_sizing 内の価格欠損時の注記（TODO）があり、価格が取得できない場合のフォールバック処理は将来の改善項目。
- config/*.yaml のパース検証は PyYAML の有無に依存する（未インストール時は検証をスキップして警告）。
- Paper Trading 用 DB は本番 DB と分離されているが、運用時はパス設定を必ず確認すること。

### Security
- （本リリースで特筆すべきセキュリティ修正はなし。環境変数にシークレットを含むため .env を Git 管理しない旨の注意を README 等で周知推奨）

---

リリース内容やファイルごとの実装方針について不明点があれば、特定のファイルや機能に絞ってより詳細な CHANGELOG 項目を追記します。