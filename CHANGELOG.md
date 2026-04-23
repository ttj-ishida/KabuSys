Keep a Changelog
=================

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

注: 以下の CHANGELOG は与えられたコードベースの内容から推測して作成しています（実装・ドキュメント文字列・コメント等に基づく）。実際のコミット履歴ではなく「機能・挙動のまとめ」としてご利用ください。

[Unreleased]: https://example.org/compare/v0.1.0...HEAD

0.1.0 - 2026-04-23
------------------

Added
- プロジェクト初期リリース。パッケージバージョンは `kabusys.__version__ = "0.1.0"`。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント作成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応し、安全に停止可能。
- 監視用スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に依らず本番の sqlite_path を使用する設計。
    - stop フラグ検知で監視ループを終了、例外発生時はログ記録して次のポーリングへ継続。
- 設定・環境管理
  - config.py:
    - .env 自動ロード機能を提供（.env / .env.local をプロジェクトルートから読み込み、OS 環境変数を保護）。
    - export KEY=val 形式、クォート文字列、インラインコメント等に対応する堅牢な .env パーサ実装。
    - Settings クラスを導入し、各種設定値（DB パス、API トークン、閾値、環境フラグ等）をプロパティ経由で取得・検証。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑止をサポート。
- 設定ユーティリティ
  - config_setup.py: 対話式ウィザードで .env の初期作成 / 更新を支援。
    - シークレット項目は入力時にマスク、保存前に確認ダイアログを提示。
    - デフォルト・選択肢・説明付きの項目定義を備える。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証、DB パス親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML 有りの場合は）パース検証。
    - --strict オプションで警告も失敗扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler(stdout) と TimedRotatingFileHandler（日次・30日保持）を設定する汎用セットアップ関数を追加。
    - 重複ハンドラを避けるため既存ハンドラをクリアしてから再設定。
    - LOG_LEVEL / LOG_DIR の環境変数対応と、ログディレクトリ作成失敗時のフォールバック（コンソールのみ）を実装。
  - utils/process_priority.py:
    - Windows/Linux/macOS を吸収するプロセス優先度設定、CPU affinity 設定を提供（psutil 利用）。
    - アクセス権限不足や未対応 OS の場合は警告を出し安全にスキップ。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py:
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
    - スコア全てが 0 の場合は等金額にフォールバック（警告）。
  - portfolio/risk_adjustment.py:
    - セクター集中制限の apply_sector_cap、レジームに応じた投下資金乗数 calc_regime_multiplier を実装。
    - 不明セクターは「unknown」として扱い、セクター上限の適用除外にする旨を実装。
  - portfolio/position_sizing.py:
    - risk_based / equal / score の各 allocation_method に対応した株数計算を実装。
    - 単元株（lot_size）丸め、per-stock 上限・aggregate cap（available_cash）スケーリング、cost_buffer を用いた保守的なコスト見積り、残差処理による追加配分ロジック等を実装。
- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成スクリプトを追加（期間指定可能）。
    - システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計し PASS/FAIL 判定を行う。
    - P95 計算、閾値定義（稼働率 99%、成功率 90% 等）を備える。
- 研究モジュール（初期実装）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールのスケルトンを追加（モメンタム等の計算ロジックを実装予定）。設計方針を明示したドキュメント文字列を含む。

Changed
- なし（初回リリースのため既存からの変更なし）。

Fixed
- 実行時に想定される環境・OS差異を考慮したフォールバック実装を多数追加:
  - ログディレクトリ作成失敗時はファイルハンドラ作成をスキップしてコンソール出力のみ継続。
  - process priority / cpu affinity 設定で権限不足や未実装 API の例外を捕捉して警告にとどめる。
  - DB 初期化（init_monitoring_db）は冪等性を確保して、実行時に存在確認・作成を安全に行うことを想定。
  - .env パーサはクォート・エスケープ・コメント処理を改善し、予期しない値の読み込みを軽減。

Security
- 環境変数ファイル（.env）に関する注意喚起を config_setup.py のヘッダに追加（.env を Git にコミットしないよう明記）。
- シークレット入力項目はウィザードでマスクして表示。

Deprecated
- なし。

Removed
- なし。

Notes / Known issues
- research/factor_research.py は途中で実装が終わっている箇所があり（ファイル末尾が途中で切れている等）、完全版の実装・テストが必要。
- 一部のコメントに TODO（例: price のフォールバック価格、lot_size を銘柄別にする等）が残っており、将来的な機能拡張ポイントを示している。
- config/*.yaml のテンプレート生成スクリプト（scripts/generate_config.py）について言及はあるが、このリポジトリに含まれていない場合は validate_config が警告を出す。

Contributing
- リポジトリに新機能を追加する際は:
  - 設定値は Settings クラスに追加し、必要であれば validate_config に検証ルールを追加してください。
  - ロギングは utils.logging_setup.setup_logging を使って統一してください。
  - .env を変更する場合は config_setup.py の ITEMS 配列を更新してウィザード対応を行ってください。

以上。必要であれば変更点をバージョン別により細かく分割したり、実際のコミットログに基づいた CHANGELOG 化を行います。どの形式（Unreleased を残す／日付表記を修正する等）にするか指示ください。