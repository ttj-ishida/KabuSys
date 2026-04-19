# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。以下は、提示されたコードベースから推測して作成した変更履歴です。

## [0.1.0] - 2026-04-19

### Added
- 初期リリース。主要コンポーネントと CLI ツールを追加。
  - 実行/監視関連スクリプト
    - src/kabusys/run_execution.py
      - ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite DB を使用する（data/paper_trading.db をデフォルト）。paper_trading 環境では MockBroker を利用して本番 DB と完全分離。
      - プロセス優先度を高（high）に設定する初期化処理を追加。
      - PID ファイル管理（data/execution.pid）と停止フラグ（data/stop_requested.flag）に基づくグレースフルシャットダウン機能を実装。
      - ブローカーファクトリ、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと起動ループを実装。
    - src/kabusys/run_monitoring.py
      - SystemMonitor 用ポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境に関係なく本番 sqlite_path を使用する旨の設計。
      - 停止フラグ検知によるループ終了と KeyboardInterrupt のハンドリングを実装。
  - 設定 / 環境管理
    - src/kabusys/config.py
      - .env 自動読み込み（.env, .env.local）を実装。プロジェクトルート検出は .git または pyproject.toml を基準に行うため、CWD に依存しない。
      - .env ファイル行のパーサ実装（コメント、export 形式、シングル/ダブルクォート内のエスケープ対応など）。
      - 環境変数の必須チェック用 _require と Settings クラスを提供。DB パス、PID パス、閾値、PAPER_FILL_MODE のバリデーションなどのプロパティを追加。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを導入。
    - src/kabusys/config_setup.py
      - 対話式 .env 作成・更新ウィザードを追加（各項目のデフォルト/説明/シークレットマスク対応）。
      - .env の読み取り/書き込みユーティリティを実装（テンプレート付き）。
    - src/kabusys/validate_config.py
      - 起動前設定検証 CLI を追加（--strict オプションで警告を失敗扱いにできる）。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と PyYAML パース検証（PyYAML 未インストール時はスキップ）、本番環境向けガードチェック（LINE 設定、KILL_FLAG_CLEAR_ON_START 等）を実装。
  - ポートフォリオ構築関連（純粋関数群）
    - src/kabusys/portfolio/portfolio_builder.py
      - 候補選定（スコア順ソート）、等金額配分、スコア加重配分（スコア全て 0 の場合に等分へフォールバック）を実装。
    - src/kabusys/portfolio/risk_adjustment.py
      - セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知レジーム時はフォールバック動作を定義。
    - src/kabusys/portfolio/position_sizing.py
      - position sizing ロジックを実装（risk_based / equal / score の各方式、lot_size 単位で丸め、max_position・max_utilization・cost_buffer を考慮したスケーリング処理、aggregate cap と端数配分のアルゴリズム）。
    - src/kabusys/portfolio/__init__.py にて主要 API をエクスポート。
  - ユーティリティ
    - src/kabusys/utils/logging_setup.py
      - 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーへ設定。既存ハンドラの二重登録を防止。
      - LOG_DIR 解決やファイルハンドラ作成失敗時のフォールバックを実装。
    - src/kabusys/utils/process_priority.py
      - プロセス優先度設定（Windows / POSIX の差異吸収）と CPU affinity 設定ユーティリティを追加。psutil の権限・未実装例を安全に扱う。
  - ツール
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading 検証レポート生成ツールを追加。稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均／最大／P95）を算出し PASS/FAIL 判定を出力。日付フィルタと DB パス指定オプションをサポート。
  - 研究用モジュール（下準備）
    - src/kabusys/research/factor_research.py
      - ファクター計算基盤（モメンタム / MA200 / ATR / ボリューム等）の枠組みと定数を追加。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計方針を導入（関数 calc_momentum 等の実装を含む途中実装）。
  - パッケージ情報
    - src/kabusys/__init__.py にてバージョン __version__ = "0.1.0" を設定。

### Changed
- ログに関する設計
  - コンソール出力を stdout に統一（cron/Task Scheduler 等でのリダイレクトを考慮）。
  - 既存ハンドラをクリアしてからハンドラを再設定することで二重ログ出力を防止。
- .env 自動ロードの優先順位と保護
  - OS 環境変数を保護するため .env ロード時に保護セットを導入（.env.local は override 可能だが OS 環境は上書きされない）。
- 実行/監視プロセス挙動
  - 実行エンジン起動前に停止フラグの存在チェックを追加（既に停止フラグが立っている場合は起動しない）。
  - 監視プロセスは設定に関わらず本番用 sqlite_path を使用することを明記（監視データの一元化）。

### Fixed / Improved
- .env パーサの堅牢化
  - export 形式、クォート内のエスケープ、行内コメントの取り扱いなどに対応（不正な行は無視）。
  - 空やコメント行の扱いを厳密化して環境読み込みの信頼性を向上。
- logging_setup のファイルハンドラ作成失敗に対する堅牢性向上（失敗時はコンソール出力にフォールバックし、警告を出す）。
- process_priority のエラー処理を強化（権限不足・未実装 API を安全に扱い、警告ログでフォールバック）。
- Execution/Risk 設定のデフォルト値を明示（RiskConfig の既定値等）し、初期化時に broker.get_available_cash() を使用して initial_portfolio_value を設定。

### Notes / Implementation details
- Paper Trading と Live の DB は完全分離される設計（paper_trading 環境は paper_sqlite_path を使用）。
- run_monitoring の MONITOR_POLL_INTERVAL は不正値（0 以下、非数）を検出してデフォルトにフォールバックし、警告ログを出力する実装となっている。
- position_sizing や risk_adjustment のアルゴリズムは PortfolioConstruction / StrategyModel のドキュメントに基づく設計注記を含む（ファイル内コメント参照）。
- validate_config は PyYAML の有無に応じて YAML の内容検証をスキップ可能にしているため、実環境での依存性が柔軟に扱える。

---

今後のリリースでは、factor_research の完全実装、戦略側（strategy）やデータ取得周り（data）モジュールの統合、テストカバレッジの追加、CI/CD の導入、さらに Paper Trading / Live 切り替え対応の E2E テスト等が想定されます。必要であれば上記 CHANGELOG をベースに微修正・日付変更を行います。