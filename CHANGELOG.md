# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

### Added
- ドキュメント化されたエントリポイント・スクリプト
  - run_execution: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading SQLite DB を使用し、MockBrokerClient（BrokerClientFactory 経由）で発注をシミュレートする。
    - 停止制御: data/stop_requested.flag による停止検知、data/execution.pid に PID を記録。
    - スレッドでエンジンを実行し、停止フラグ検出時に安全に停止する実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用（監視 DB と運用 DB の分離運用を想定）。
    - 停止フラグ（data/stop_requested.flag）でループを終了。
- 設定管理・CLI
  - config_setup: 対話式ウィザードで .env を生成・更新するツールを追加。
    - 各設定項目の説明・デフォルト値・シークレット入力対応。
    - .env の安全な書き出しテンプレートを備える。
  - validate_config: .env と config/*.yaml の事前検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ確認、YAML の存在・パースチェック、live 環境に対する追加ガードを実装。
    - --strict オプションで警告を FAIL 扱いにできる。
- 環境変数読み込み・設定
  - Settings クラスを追加して各種環境変数アクセスをラップ。
  - 自動 .env ロード機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。  
    - 読み込み順: OS 環境変数 > .env.local > .env。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env ファイルパーサの強化:
    - export プレフィックス対応、クォート付き値のバックスラッシュエスケープ処理、インラインコメント処理などをサポート。
- ロギング・プロセス制御ユーティリティ
  - utils.logging_setup: root ロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション）を設定する共通ユーティリティを追加。
    - LOG_DIR / LOG_LEVEL による上書き、既存ハンドラのクリア、ログファイルのローテーション/バックアップ制御を実装。
  - utils.process_priority: Windows / POSIX を吸収するプロセス優先度設定ユーティリティを追加。
    - nice 値 / Windows 優先度定数を扱い、失敗時は警告でスキップする堅牢性を持つ。
    - CPU affinity 設定関数も実装（psutil の利用、権限不足を想定した警告処理）。
- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選別、signal_rank をタイブレークに使用。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（スコア合計 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限（既存保有比率が上限に達したセクターの候補除外）。"unknown" セクターは制限対象外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear マッピング、未知レジームはフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数計算を実装。
      - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash）でのスケーリング、cost_buffer を使った保守的見積り、残差配分ロジックなどを実装。
- 分析・レポートツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、API レイテンシ（平均/最大/P95）を算出して PASS/FAIL 判定を行う。
    - P95 計算、日付フィルタ、DB パスの CLI/環境変数指定対応、テーブル欠損時の安全ハンドリングを実装。
- その他ユーティリティ・構成
  - __init__.py にバージョン情報（0.1.0）を追加。
  - package 内の各モジュールから必要な関数・クラスをエクスポートする __all__ を整備。

### Changed
- 初期設計として、監視（monitoring）処理は KABUSYS_ENV に依存せず本番用 sqlite_path を参照するという運用上の判断を明確化（run_monitoring）。
- ロギングは stdout にも出すことで cron / タスクスケジューラ運用を念頭に置いた実装に。

### Fixed
- .env 読み込みにおける既存 OS 環境変数保護ロジックを追加（.env.local から上書きする際も OS の環境変数を protected として上書き回避）。

### Known / Notes
- research.factor_research モジュールはファクター計算の設計と基礎実装を行っているが、一部関数（例: calc_momentum）の実装が開発途中で切れている箇所があるため、完全実装は継続作業を要する。  
- 実際のブローカー連携（kabuステーション）や ExecutionEngine の内部実装は別モジュール（execution.*）に依存しており、本リリースではインターフェース・組立て部分が中心。実運用時は BrokerClient の実装・設定確認が必要。
- psutil、duckdb、PyYAML 等の外部パッケージに依存する箇所がある。実行環境に依存パッケージをインストールしてください。
- 監視・発注系はファイルベースの停止フラグ（data/stop_requested.flag 等）で制御する設計のため、運用時はファイル配置権限・パス設定に注意してください。

---

## [0.1.0] - 2026-04-18

初回公開リリース。上記「Unreleased」に記載の機能群を含む初期版。