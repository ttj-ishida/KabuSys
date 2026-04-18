# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の慣例に従って記載しています。  
バージョン番号はパッケージの __version__ を基準にしています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-18
初回リリース — KabuSys の基本機能セットを実装しました。主に環境設定、起動スクリプト、監視/実行の起動基盤、ポートフォリオ構築・ポジションサイジング、ユーティリティ、および Paper Trading 向け検証ツールを含みます。

### Added
- 基本パッケージ情報
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として追加。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止はプロジェクトの data/stop_requested.flag により検知。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番用 SQLite パスを使用して初期化。
    - duckdb 接続を併用。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=`paper_trading` の場合はペーパートレード専用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（MockBroker を含む想定）。
    - エンジンの PID ファイル管理と停止フラグ検出（data/execution.pid / data/stop_requested.flag）。
    - デーモンスレッドで Engine.run_session を実行、停止フラグで安全に停止。

- 環境設定関連
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートの探索: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順序と OS 環境変数保護機構を実装。
    - .env の各行パースは export プレフィックス、クォート値、エスケープ、インラインコメントの処理に対応。
    - Settings クラスで主要設定をプロパティとして提供（J-Quants / kabu API / DB パス / ロギング / 監視閾値 / 環境種別 等）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - KABUSYS_ENV / LOG_LEVEL の値検証。
  - config_setup.py
    - 対話式ウィザードで .env 初期作成・更新を支援する CLI を追加。
    - シークレット値のマスク表示、選択肢サポート、既存 .env の読み込み・再利用に対応。

- 設定検証 CLI
  - validate_config.py
    - .env と config/*.yaml の事前検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML が存在する場合）などを実装。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定の確認や Kill Switch 設定の警告）。
    - --strict フラグで警告も失敗扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定: select_candidates（スコア降順、タイブレークに signal_rank）を実装。
    - 重み算出: calc_equal_weights（等分配）、calc_score_weights（スコア正規化、全スコア 0 の場合は等分配へフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中上限適用: apply_sector_cap（既存保有を踏まえて新規候補を除外）。
    - 市場レジームによる乗数: calc_regime_multiplier（bull/neutral/bear をマッピング、未知は警告のうえフォールバック）。
  - portfolio/position_sizing.py
    - 銘柄ごとの発注株数算出: calc_position_sizes を実装。
    - allocation_method により risk_based / equal / score をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限・総投下金額（aggregate cap）スケーリング、cost_buffer（手数料・スリッページ推定）対応。
    - 利用可能現金に基づくスケーリングと残余での追加配分ロジックを実装。

- 監視・モニタリング基盤
  - monitoring_db 初期化利用（起動スクリプトから監視テーブルの冪等な初期化を行う）。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ロギング設定ユーティリティを追加。
    - stdout 出力用 StreamHandler（stdout）と、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app>.log、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py
    - クロスプラットフォームなプロセス優先度設定を追加（Windows の priority class / POSIX の nice 値を吸収）。
    - CPU affinity 設定ユーティリティも実装。アクセス権限や未対応 OS の場合は安全にスキップして警告ログを出す。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（fill rate）、送信率、P95 レイテンシ等を集計し PASS/FAIL を判定するしきい値を定義。
    - 日付フィルタ、DB パス指定（--db または PAPER_TRADING_SQLITE_PATH）に対応。

- 研究/リサーチ
  - research/factor_research.py
    - ファクター計算モジュールを追加（モメンタム、MA、ATR、流動性などを想定）。
    - calc_momentum の基盤実装（詳細な計算ロジックと定数定義を追加）。※ファイル末尾に実装途中の節が存在するため、今後の拡張予定あり。

### Changed
- なし（初回リリースのため追加のみ）

### Fixed
- なし（初回リリースのため追加のみ）

### Removed
- なし

### Notes / Known limitations
- research/factor_research.py はモメンタム関係の実装が含まれる一方、ファイル末尾に未完の箇所（実装継続の余地）が見られます。今後、完全なファクター計算の追加・テストを行う予定です。
- 一部の IO / OS 操作（ログディレクトリ作成、プロセス優先度設定、CPU affinity）は権限やプラットフォームに依存するため、失敗時は安全にフォールバックし警告を出す設計になっています。
- Paper Trading と本番 DB の分離により、誤って実データを書き込まないよう配慮していますが、環境変数の設定ミスに注意してください（validate_config を事前に実行することを推奨します）。

---

（本 CHANGELOG はコードベースからの推測に基づいて作成されています。実際のコミット履歴がある場合は、そちらに基づいて適宜調整してください。）