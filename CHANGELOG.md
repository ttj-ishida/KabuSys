# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/）に準拠します。  
このプロジェクトはセマンティックバージョニングを使用します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装しました。主な追加点は以下のとおりです。

### Added
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを提供。起動時にプロセス優先度を "high" に設定し、SQLite / DuckDB に接続してエンジンをデーモンスレッドで実行する。
    - KABUSYS_ENV に応じて paper_trading 用 DB（data/paper_trading.db）を使用し、本番 DB と分離する。
    - 停止フラグ（data/stop_requested.flag）検出による安全停止機構を実装。PID ファイル（data/execution.pid）を管理。
    - BrokerClientFactory を使って本番・ペーパートレードで適切なブローカークライアントを生成。
    - RiskManager, OrderManager, Reconciler, OrderRepository 等の組み立てと実行エントリポイントを用意。
- 監視スクリプト
  - run_monitoring.py
    - SystemMonitor をポーリングで起動するスクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境に関係なく本番 sqlite_path を使用して接続・初期化。
    - 停止フラグによるループ終了、KeyboardInterrupt 対応、エラー発生時のログと次ポーリング継続処理を実装。
- 設定管理
  - config.py
    - Settings クラスを導入し、環境変数から設定値を集中管理。
    - .env / .env.local の自動ロード機能（プロジェクトルート検出 .git / pyproject.toml）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 実行環境フラグ等）。
    - PAPER_FILL_MODE のバリデーション、KABUSYS_ENV と LOG_LEVEL の妥当性チェックを実装。
  - config_setup.py
    - 対話式ウィザードで .env を新規作成・更新する CLI を追加。シークレットマスク表示、選択肢・デフォルトのサポート、保存確認を実装。
- 設定検証 CLI
  - validate_config.py
    - .env と config/*.yaml の設定不備を起動前に検出する CLI を提供。
    - 必須/任意環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML パース（PyYAML 未インストール時は警告）などを実装。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング・ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を一括設定するユーティリティを実装。
    - LOG_DIR/LOG_LEVEL の解決順、ディレクトリ作成失敗時のフォールバック動作を明確化。
- プロセス優先度 / CPU affinity
  - utils/process_priority.py
    - Windows / POSIX（Linux, macOS, FreeBSD）を吸収するプロセス優先度設定ユーティリティを実装（high/normal/low）。
    - CPU affinity 固定機能（最初の N コアに固定）を提供。権限不足や未対応 OS では警告を出してスキップ。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコア全 0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を実装。未知のレジーム時のフォールバックとログ出力あり。
  - portfolio/position_sizing.py
    - 各種配分方式（risk_based / equal / score）に基づく株数決定ロジックを実装。単元株（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金でスケーリング）、コストバッファを考慮したスケーリング分配ロジックを実装。
- リサーチ
  - research/factor_research.py（モジュール骨格とモメンタム計算インターフェース）
    - DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。モメンタム・MA200・ATR・流動性等を計算するための定数と calc_momentum の骨格を追加（詳細実装途中の痕跡あり）。
- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）を読み取り、稼働率・注文成功率・送信率・P95 レイテンシ等を集計してレポート出力するスクリプトを追加。
    - デフォルトの合格基準（稼働率 >=99%、成立率 >=90%、送信率 >=95%、P95 <=200ms）を定義し、PASS/FAIL を判定。
- パッケージ情報
  - __init__.py にバージョン 0.1.0 を設定。

### Changed
- 主要コンポーネントは「実行」「監視」「設定」「ポートフォリオ」「リサーチ」「ツール」へ分割して整理。
- ログ出力先は stdout を標準にし、ファイル出力は logs/<app_name>.log（日次ローテーション）で統一。

### Fixed
- .env パーサ (_parse_env_line) が以下を正しく扱うよう改善:
  - export KEY=val 形式
  - シングル/ダブルクォート内でのバックスラッシュエスケープ
  - クォートなし時のインラインコメント判定（直前がスペース/タブの場合のみ）
- run_monitoring.py のポーリング間隔取得で不正値が与えられた場合にデフォルトへフォールバックするロジックを追加（負数や非整数の回避）。
- DuckDB / SQLite 接続の初期化とクローズ処理を安定化（起動/終了時のリソース解放を保証）。

### Security
- .env に関する注意書きを config_setup.py に明記（.env を絶対に Git にコミットしないこと）。

### Notes / Implementation details
- ExecutionEngine の構成（RiskManager のデフォルトパラメータ、initial_portfolio_value を broker.get_available_cash() で初期化する等）は実運用を想定した合理的なデフォルトを採用していますが、パラメータは config ファイル / 環境変数等で上書きすることを想定しています。
- monitoring 用の DB 初期化（init_monitoring_db）や SystemMonitor / ExecutionEngine の内部実装は別モジュールに分離されており、このリリースではそれらを組み合わせる起動およびユーティリティ周りの基盤整備を行いました。

---

今後の予定（例）
- research/factor_research の完全実装（Momentum / Value / Volatility / Liquidity の算出と正規化）
- ExecutionEngine と Monitoring のさらなるテスト・堅牢化
- 個別銘柄単位の lot_size サポートや外部マスタ連携
- YAML ベースの設定の読み取り・マージ機能の強化

<!--
参考: Keep a Changelog のセクション順序（Added, Changed, Deprecated, Removed, Fixed, Security）に従っています。
-->
