CHANGELOG
=========

このプロジェクトは "Keep a Changelog" の形式に準拠して変更履歴を管理します。  
各リリースでは「Added / Changed / Fixed / Removed」などのカテゴリで変更点を記載します。

[0.1.0] - 初回リリース
--------------------

### Added
- 基本モジュール群を初期実装
  - kabusys パッケージのエントリポイントとバージョンを追加（__version__ = 0.1.0）。
- 環境設定・管理
  - Settings クラスを追加し、環境変数経由で各種設定（DB パス、API トークン、環境種別、ログレベル、監視閾値など）を取得可能に。
  - .env 自動読み込み機能を追加（プロジェクトルートの .env、.env.local を優先順で読み込み）。OS 環境変数は保護され上書きされない仕組みを導入。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パース機能を実装：コメント・export 形式・シングル/ダブルクォートやエスケープに対応。
  - PAPER_FILL_MODE（ペーパートレードの約定モード）に対するバリデーションを実装（有効値チェック）。
  - KILL_FLAG_CLEAR_ON_START 等の設定取得を実装。
- 起動スクリプト / デーモン機能
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時には paper 用 SQLite を使用（本番 DB と完全分離する設計）。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）の扱いを実装。
    - BrokerClientFactory を用いてブローカークライアントを生成（環境に応じて Mock を利用する想定）。
    - ExecutionEngine を別スレッドで起動し、停止フラグ検知で安全に停止する仕組みを実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境にかかわらず監視は本番用 sqlite_path を使用する（監視データは単一 DB に集約する設計）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバック。
    - 停止フラグ検知でループ終了、KeyboardInterrupt ハンドリング、DB 接続のクリーンアップを実装。
- DB / 分析サポート
  - DuckDB 接続をサポート（設定から duckdb_path を取得して接続）。
  - 監視用 DB 初期化ユーティリティ init_monitoring_db の呼び出しを各起動スクリプトで実行（冪等にテーブル存在を保証）。
- ロギング・プロセス管理ユーティリティ
  - utils.logging_setup.setup_logging を追加：
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app>.log）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみ継続。
    - 環境変数/引数からログレベル・ログディレクトリの解決を行う。
  - utils.process_priority を追加：
    - Windows / POSIX（Linux/Mac/FreeBSD）双方でプロセス優先度（high/normal/low）を設定するユーティリティを提供。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を実装（権限不足等は警告でスキップ）。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates（スコア降順で上位 N を選択）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコアに基づく重み。全てのスコアが 0 の場合は等金額にフォールバック）
  - portfolio.risk_adjustment:
    - apply_sector_cap（既存保有のセクター集中を計算し上限超過セクターの新規候補を除外。unknown セクターは上限適用外）
    - calc_regime_multiplier（market レジームに応じた投下資金乗数。未知のレジームは 1.0 にフォールバックし警告）
  - portfolio.position_sizing:
    - calc_position_sizes（risk_based / equal / score の各配分方式をサポート）
    - 単元株（lot_size）での丸め、1銘柄上限・aggregate cap（利用可能現金超過時のスケーリング）、cost_buffer を考慮した保守的見積り、残差分の優先配分ロジックを実装
- CLI ツール
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を追加（項目定義、既存値の再利用、シークレットマスク表示、保存確認など）。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認と（PyYAML があれば）パース検証、本番向けガード（LINE 通知設定や Kill Flag の自動クリア設定の注意喚起）を実施。
    - --strict オプションで警告を FAIL 扱いにできる。
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成ツールを追加。
    - 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）などを集計して PASS/FAIL 判定を出力。
    - P95 計算、期間フィルタ、DB パス解決（引数/環境変数/デフォルト）をサポート。
- 研究用モジュール（research）
  - research.factor_research: ファクター計算モジュールを追加（モメンタム等のファクター算出関数を実装、DuckDB 接続を利用する設計）。※ファイル末尾で実装が続く構成。

### Changed
- 監視・実行プロセスの設計上の方針を明文化
  - 監視は環境に依存せず本番監視 DB を使用する点を明示。
  - Execution は paper_trading 環境で DB を分離することで本番データと混在しないように設計。
- ロギング動作の統一化
  - 全起動スクリプトから setup_logging を呼び出すことでログの出力先・フォーマットを統一。

### Fixed
- 環境変数パーサの堅牢化
  - クォート内のバックスラッシュエスケープや、クォートなし時のコメント判定ルールを実装し、.env のパース誤動作を低減。

### Removed
- なし（初回リリース）。

注記
- 実装は現時点でのコードベースから推測して作成しています。内部実装の詳細（Engine/Monitor の振る舞いや BrokerClient の具体的実装など）は別ファイルに依存します。
- research.factor_research のファイルはモメンタム計算等を含むが、ファイル末尾で実装が継続しているため完全実装の有無はソース全体を参照してください。

今後の予定（アイデア）
- 各コンポーネントの単体テスト・統合テストの追加
- position_sizing の銘柄別 lot_size 対応（stocks マスタ参照への拡張）
- ログ/メトリクスの外部監視（Prometheus/Pushgateway 等）連携
- paper_trading 向けの自動検証テストパイプラインの構築

---