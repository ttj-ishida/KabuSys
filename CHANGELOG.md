# CHANGELOG

すべての重大な変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

注: 下記はソースコード内容から推測して作成した変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-04-21

### Added
- 全体
  - 初回公開リリース。日本株自動売買フレームワーク「KabuSys」の基本コンポーネントを追加。
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 設定管理
  - Settings クラスによる環境変数ベースの設定取得を実装。
    - J-Quants / kabuステーション / LINE / DB パス / 監視閾値など主要設定をプロパティ経由で取得可能。
    - KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL の検証を実装。
    - PAPER_FILL_MODE と PAPER_TRADING_SQLITE_PATH 等、ペーパートレード向け設定をサポート。
  - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - 読み込み順序: OS 環境 > .env > .env.local（.env.local は上書き、ただし OS 環境は保護）。
  - .env パースロジックで以下に対応:
    - export KEY=val 形式
    - シングル/ダブルクォート内のエスケープ処理
    - 行内コメントの扱い（クォート有無に応じた挙動）
  - config_setup: 対話式ウィザードを実装し、.env の初期作成／更新を支援。
    - シークレットのマスク表示、選択肢、デフォルト値、保存前の確認処理を提供。

- 設定検証 CLI
  - validate_config CLI を実装。起動前に環境変数・パス・config/*.yaml 等を検査する。
    - 必須環境変数のチェック、KABUSYS_ENV の妥当性チェック、LOG_LEVEL 検証。
    - DUCKDB / SQLITE の親ディレクトリ存在チェック。
    - PyYAML が利用可能な場合、config/*.yaml のパース検証を実行。未インストール時は警告を出力。
    - live 環境向けの追加ガード（LINE 通知設定未登録や KILL_FLAG_CLEAR_ON_START の危険設定など）。

- 実行スクリプト
  - run_execution:
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用して本番 DB と完全分離。
    - BrokerClientFactory 経由でブローカークライアントを作成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）検知で安全に停止。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視テーブル（init_monitoring_db）を冪等に初期化。

  - run_monitoring:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時は警告してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する点に言及。
    - 停止フラグ検知でループを終了し、例外発生時はログを出して次ポーリングへ継続。

- ロギング・プロセス制御ユーティリティ
  - utils.logging_setup:
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル解決の優先順位（引数 > LOG_LEVEL 環境変数 > デフォルト）を実装。
  - utils.process_priority:
    - Windows / POSIX を吸収するプロセス優先度設定を実装 (high/normal/low)。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - 権限不足や未対応環境での失敗は警告ログを出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - シグナル選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
    - スコア合計が 0 の場合は等分配へフォールバック。
  - portfolio.risk_adjustment:
    - セクター集中度制限（apply_sector_cap）: 既存保有を基に超過セクターの新規候補を除外。
    - レジーム乗数（calc_regime_multiplier）: bull/neutral/bear に応じた投下資金乗数を返す。未知レジームは警告して 1.0 にフォールバック。
  - portfolio.position_sizing:
    - 株数決定ロジック（risk_based / equal / score）を実装。
    - 単元株（lot_size）での丸め、per-stock 上限・aggregate cap の適用、cost_buffer による保守的見積り、スケールダウンと端数処理を実装。

- ツール
  - tools.paper_verification_report:
    - ペーパートレード検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ等を集計して判定（PASS/FAIL）を出力。
    - 複数の閾値を定義（稼働率 99%, 成功率 90%, 送信率 95%, P95 レイテンシ 200ms）。
    - DB 存在チェック、クエリ実行時の OperationalError を握りつぶしてフォールバックする堅牢性あり。

- リサーチ
  - research.factor_research:
    - ファクター計算モジュールのスケルトンを追加（モメンタム / MA200 / ATR / 流動性などの計算方針を記載）。
    - DuckDB 接続を受け prices_daily / raw_financials を参照して計算する設計。現時点で実装途中（ファイル末尾が切れているため一部未完）。

### Changed
- 仕様の明確化
  - 監視コンポーネントは monitor 用 DB 初期化を起動時に必ず行い、監視ループでは実行環境に関係なく本番 sqlite_path を参照する仕様を文書化。
  - run_execution は paper_trading 時に paper_sqlite_path を使用することで本番 DB と完全に分離する仕様を明示。

### Fixed
- 入力検証・堅牢性向上
  - MONITOR_POLL_INTERVAL の不正な値（0 や負数、非整数）を検出して警告し、デフォルトにフォールバックする処理を追加。
  - .env パースでクォート内のエスケープ・インラインコメントを正しく処理するように改善。
  - ログディレクトリ作成失敗やファイルハンドラ生成失敗時のフォールバックを追加して起動時に致命的にならないようにした。
  - Process priority / CPU affinity 設定で権限不足や未実装の環境に対し警告ログを出して安全にスキップ。

### Notes
- 実行に必要な外部依存:
  - psutil（プロセス優先度 / CPU affinity）、duckdb（分析 DB）、PyYAML（config ファイル検証、未インストール時は警告してスキップ）。
- セキュリティ:
  - .env を絶対にリポジトリにコミットしない旨を config_setup の生成テンプレートに明記。
- 未実装 / TODO:
  - research.factor_research の一部実装が途中（ファイル末尾で切れている）。
  - position_sizing の lot_size を銘柄別で持たせる拡張案（将来の拡張ポイントとしてコメントあり）。
  - price 欠損時のフォールバック（前日終値など）に関する TODO コメントあり。

---

（以降のリリースでは改修・バグ修正・新機能追加をここに記録してください）