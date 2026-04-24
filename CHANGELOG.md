# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-24

### Added
- 初回リリース。KabuSys のコア機能群を追加。
  - 起動スクリプト
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。スレッドでエンジンを起動し、data/execution.pid に PID を記録。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを実装。
      - 停止フラグ (data/stop_requested.flag) の検知により安全にエンジンを停止。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。デフォルトポーリング間隔は 60 秒。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（不正値は警告のうえデフォルトにフォールバック）。
      - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
      - 停止フラグ (data/stop_requested.flag) の検知でループを終了。
  - 設定/環境管理
    - config.py
      - .env の自動読み込み機能を追加（プロジェクトルート自動検出: .git または pyproject.toml を基準）。
      - 高機能な .env パーサ（export 形式、クォート内のエスケープ、インラインコメントの扱いを考慮）。
      - Settings クラスでアプリケーション設定値をラップ（デフォルト値・バリデーションを含む）。
      - Paper Trading / Live / Development を区別する KABUSYS_ENV、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等の設定を提供。
    - config_setup.py
      - 対話式ウィザードで .env を初期作成・更新する CLI を追加。シークレット入力のマスク、選択肢サポート、既存値の再利用を実装。
    - validate_config.py
      - 起動前に .env と config/*.yaml の設定不備を検出する検証 CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML のパースチェック、Live 環境向けのガードを実施。
      - --strict オプションで警告を失敗扱いにできる。
  - ユーティリティ
    - utils/logging_setup.py
      - 統一的なログ設定ユーティリティを追加。StreamHandler を stdout に設定し、TimedRotatingFileHandler（日次ローテーション、30日保管）でファイル出力を行う。
      - LOG_LEVEL / LOG_DIR の解決順序やハンドラの二重設定防止ロジックを実装。
    - utils/process_priority.py
      - Windows / POSIX の差分を吸収するプロセス優先度設定ユーティリティを追加（high/normal/low）。
      - CPU affinity 設定ユーティリティも実装（psutil を使用）。権限不足や未対応環境では警告を出してスキップ。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全て 0 の場合は等金額にフォールバック。
    - portfolio/risk_adjustment.py
      - セクター集中上限の適用 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier) を実装。未知レジームはフォールバックで警告。
    - portfolio/position_sizing.py
      - 発注株数計算ロジックを実装（allocation_method: risk_based / equal / score）。
      - 単元株（lot_size）丸め、1銘柄上限・aggregate cap のスケーリング、cost_buffer（手数料・スリッページ考慮）、利用可能現金に対するスケール調整を採用。
  - リサーチツール
    - research/factor_research.py（ファクター計算基盤を追加。モメンタム / MA / ATR / ボラティリティ等の計算方針を実装（実装途中を含む））
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading の検証レポート生成スクリプトを追加。期間フィルタ、稼働率・注文成功率・送信率・レイテンシ（P95）等の算出と PASS/FAIL 判定（閾値はソース内で定義）を実装。
      - DB パスはコマンドライン (--db) または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

### Changed
- ロギング設計
  - すべての起動スクリプトから utils.setup_logging を呼び出す想定とし、コンソール出力は stdout に統一（cron / scheduler での取り扱いを考慮）。
- .env 自動読み込みの挙動
  - OS 環境変数を保護するために .env 読み込み時の上書き（.env.local は上書き許可だが OS 環境変数は保護）を実装。

### Fixed / Robustness
- 設定値の妥当性チェック・フォールバックを随所に追加
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検知して警告し、デフォルト（60 秒）にフォールバックするようにした。
  - calc_score_weights で全スコアが 0 の場合に等金額にフォールバックして警告を出すようにした。
  - process_priority / set_cpu_affinity はプラットフォーム差分や権限不足を捕捉して警告を出し、プロセスを停止させないようにした。
  - ログディレクトリ作成失敗時はファイルハンドラを無効化してコンソール出力のみで継続するようにした。
  - validate_config の YAML 検証は PyYAML 未導入時にスキップして警告を出す。

### Security
- .env に関する注意
  - config_setup が生成する .env ヘッダに「.env は絶対に Git にコミットしないこと」を明示。
  - Settings._require により必須環境変数未設定時は ValueError を送出して起動を失敗させることで、秘密情報の未設定を発見しやすくした。

### Notes / Known limitations
- research/factor_research.py は設計方針と一部実装を含むが、（スナップショット中で）実装が途中で切れている箇所があるため、完全なファクター計算のユニットテストと追加実装が必要。
- position_sizing の価格欠損時の挙動に関する TODO コメントを残している（価格が欠損した場合は見積りが過少になる懸念があるため、将来的に前日終値や取得原価でのフォールバックを検討）。
- run_monitoring は監視用 DB として settings.sqlite_path（本番）を使う設計のため、開発環境で実行する場合は意図的に環境変数を調整する必要がある。

-----

今後のリリースで予定している改善・追加（例）
- factor_research の完了・テスト追加
- ExecutionEngine / SystemMonitor のユニットテストと統合テスト
- 銘柄ごとの単元株情報を持つマスタ導入と position_sizing の拡張
- paper_trading の更なる検証ツールと自動化レポート出力（ファイル/JSON/HTML）

---
この CHANGELOG はコードベースの状態から推測して作成しています。実際のコミット履歴や過去バージョンとの差分と照合して必要に応じて調整してください。