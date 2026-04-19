# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

- 既存履歴は SemVer を想定しています（このリポジトリでは初期バージョンとして 0.1.0 を付与しています）。

## [Unreleased]

（現状なし）

## [0.1.0] - 2026-04-19

Initial release — 日本株自動売買システム "KabuSys" の最初の公開版。主な機能と実装を以下にまとめます。

### Added
- 実行エントリ / デーモン系
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用（PAPER_TRADING_SQLITE_PATH で上書き可能）。
    - BrokerClientFactory により本番/モックのブローカークライアントを切り替え可能。
    - 停止用フラグファイル（data/stop_requested.flag）を監視し安全に終了する仕組みを備えたスレッド実行ループ。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority.set_process_priority を使用）。
    - ExecutionEngine に渡す RiskManager のデフォルト設定（max_position_pct 等）を定義。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、無効値時はデフォルトにフォールバック）。
    - 監視（monitoring）用 DB は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用する設計。
    - 停止フラグ検知でループを終了、例外はログ出力して次ポーリングへ継続。

- 設定・環境管理
  - config.py
    - Settings クラスを追加し、環境変数からアプリ設定を取得する統一インターフェースを提供。
    - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml から特定して読み込む）。
    - .env の自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env 値のパースはクォートやエスケープ、行末コメント等に柔軟に対応。
    - 各種設定プロパティ（DB パス、PID ファイル、閾値、ENV 解析など）を実装。
    - PAPER_FILL_MODE の有効値検証、KABUSYS_ENV / LOG_LEVEL の検証を行う。

  - config_setup.py
    - 対話式ウィザードで .env を生成／更新する CLI ツールを追加。
    - 対話形式のプロンプト、既存 .env 読み込み、秘密項目のマスク表示、最終確認の保存機能を実装。

  - validate_config.py
    - 起動前に .env および config/*.yaml の不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在確認、YAML パースチェック（PyYAML がある場合）等を実施。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション）を設定する共通ユーティリティを追加。
    - ログ保存先は引数 / 環境変数 LOG_DIR / デフォルト logs/ の順で決定。ディレクトリ作成に失敗した場合はファイル出力をスキップして標準出力のみで継続。
    - 既存ハンドラをクリアして再設定するため、二重設定を防止。

  - utils/process_priority.py
    - psutil を用いて Windows / POSIX を吸収するプロセス優先度設定ユーティリティを追加。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応 OS の場合は警告ログでスキップする安全設計。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - BUY シグナルの候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア比率配分 (calc_score_weights) を実装。
    - スコア全てが 0 の場合は等配分にフォールバックし警告。

  - portfolio/risk_adjustment.py
    - セクター集中の上限適用 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。
    - unknown セクターの扱い、レジーム未定義時のフォールバック挙動を明記。

  - portfolio/position_sizing.py
    - allocation_method（"risk_based","equal","score"）に応じた株数決定ロジックを実装。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap によるスケーリング、コストバッファ適用、残差配分アルゴリズムを含む。
    - price 欠損時の挙動、将来的な銘柄ごとの lot_size 扱いを注釈として記載。

- 取引・監視データベース関連
  - monitoring/monitoring_db.py（参照され初期化を行う呼び出しを含む）
    - run_*.py の起動時に監視用テーブルの存在を保証する初期化を呼ぶ箇所を実装（冪等な init_monitoring_db を利用）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード履歴 DB（デフォルト: data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、API レイテンシ等）を集計しレポートを出力する CLI を追加。
    - 日付フィルタ (--from / --to)、DB パス (--db または環境変数) をサポート。
    - P95 計算、閾値判定（稼働率 99%、成功率 90% 等）を実装し PASS/FAIL を判定。

- 研究用モジュール（DuckDB ベース）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity といったファクター計算の設計と部分実装を追加。DuckDB 接続を受けて prices_daily / raw_financials テーブルを参照する方針を採用。
    - モメンタム計算（calc_momentum）の雛形と定数群を実装（注: ソースの途中まで実装）。

### Changed
- 初期公開のため、既存のコード設計を整理してモジュール単位で公開。  
  - ログやプロセス制御は全スクリプトから共通ユーティリティを利用する設計へ統一。
  - DB パスや各種閾値は Settings 経由で一元管理。

### Fixed
- .env のパースと自動読み込みについて、引用符・エスケープ・コメント処理を改善して現実的な .env 形式に対応。

### Deprecated
- なし

### Removed
- なし

### Security
- なし（ただし .env は絶対にリポジトリにコミットしないことを強く注記）。

---

## 注意事項 / 既知の改善点・ TODO
- research/factor_research.calc_momentum はファイル末尾で実装が途中で切れている（このリリースでは設計と一部実装まで）。本格運用前に完全実装と単体テストが必要です。
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に price が欠損（0.0）の場合にエクスポージャーが過小評価されうる旨の TODO コメントあり。前日終値や取得原価でのフォールバック実装が将来必要。
- run_monitoring は「監視は環境にかかわらず本番 sqlite_path を使用する」設計になっているため、paper_trading 環境で監視 DB を完全に分離したい場合は設定変更が必要。
- process_priority の一部挙動はプラットフォーム依存（権限不足や未対応 OS ではスキップされる）。運用環境で期待する優先度が得られるか確認してください。
- ログディレクトリ作成やファイルハンドラ作成に失敗した場合、明示的な標準エラー出力は行うが、運用側でログ公開先のパーミッションやパス設定を確認すること。

---

メンテナンスや次期バージョンに向けた提案
- factor_research を完成させ、DuckDB ベースの統合テストを追加する。
- ExecutionEngine / SystemMonitor の単体テスト、エンドツーエンドの統合テストを整備する（特に paper_trading の分離動作）。
- ポートフォリオ構築・ポジションサイズ関連に対するモンテカルロやヒストリカルなバックテストでの検証コードを追加する。
- .env 周りのセキュリティ（権限管理）、およびログローテーション設定の監視強化。

[0.1.0]: https://example.com/release/0.1.0 (初期リリース)