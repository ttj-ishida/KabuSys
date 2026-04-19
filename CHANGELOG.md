# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
フォーマット: https://keepachangelog.com/ja/

## [Unreleased]

（現状のリポジトリは初期リリース相当の状態のため、主要変更は下記 0.1.0 に含まれます。今後の変更はこのセクションに記載してください。）

---

## [0.1.0] - 2026-04-19

初回リリース。日本株自動売買システム "KabuSys" のコア機能群を実装しました。主に以下の機能／ユーティリティ、CLI スクリプト、ポートフォリオ構築ロジック、実行・監視ランナー、設定管理等を含みます。

### Added
- 基本情報
  - パッケージのバージョンを追加（__version__ = "0.1.0"）。
  - パッケージ公開用の __all__ を定義（data, strategy, execution, monitoring 等）。

- 設定・環境管理
  - Settings クラス（kabusys.config）を実装し、環境変数から設定を一元取得可能にしました。
  - .env 自動ロード機能を導入（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - .env のパース機能を強化（export 形式、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応）。
  - 環境変数保護（OS 環境変数優先）および自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を追加。
  - Paper Trading 用設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等）を追加。

- 設定ツール / 検証
  - 対話式設定ウィザード CLI（kabusys.config_setup）を追加。.env の新規作成・更新を支援。
  - 設定検証 CLI（kabusys.validate_config）を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在／パース等をチェック。--strict による警告を FAIL 扱いにするオプションあり。
  - validate_config は本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 設定の未設定、KILL_FLAG_CLEAR_ON_START の危険設定など）を実装。

- 実行・監視ランナー
  - 実行エンジン起動スクリプト（kabusys.run_execution）を追加。
    - プロセス優先度を high に設定して起動。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（MockBrokerClient の利用を想定）。
    - ExecutionEngine の起動・停止監視、PID ファイル管理、停止フラグ（data/stop_requested.flag）に対応。
  - 監視ループ起動スクリプト（kabusys.run_monitoring）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視データを記録。
    - stop flag（data/stop_requested.flag）検知でループを終了。

- ロギング・プロセス制御ユーティリティ
  - 統一ログ設定ユーティリティ（kabusys.utils.logging_setup）を追加。
    - コンソール出力は stdout、ファイル出力は日次ローテーション（TimedRotatingFileHandler）で 30 日分保持。ログディレクトリは引数・環境変数・デフォルトの順で解決。
    - 既存ハンドラの重複防止（既存ハンドラをクリアして再構成）。
    - ファイルハンドラ作成失敗時はコンソール出力のみで継続。
  - プロセス優先度・CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）を追加。
    - Windows / POSIX (Linux, Darwin, FreeBSD) を吸収。nice 値や Windows の priority class を利用。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(N) を提供。権限不足等のケースは警告して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder: 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）。
    - select_candidates は score 降順、同点時は signal_rank 昇順でタイブレーク。
    - calc_score_weights は全スコアが 0 の場合に等配分へフォールバック（Warning）。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）。
    - apply_sector_cap は既存保有のセクター時価を計算し、max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは適用除外）。
    - calc_regime_multiplier は "bull"/"neutral"/"bear" に対する乗数を提供。未知のレジームは 1.0 でフォールバック（Warning）。
  - position_sizing: 発注株数決定ロジック（calc_position_sizes）。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - リスクベースでは risk_pct / stop_loss_pct に基づく算出、単元株（lot_size）丸め、1 銘柄上限 (max_position_pct) を考慮。
    - aggregate cap（全銘柄合計が available_cash を超える場合）ではスケーリングを行い、端数処理で残余キャッシュを用いて lot_size 単位で追加配分するアルゴリズムを実装。
    - cost_buffer によりスリッページ・手数料を保守的に見積もる。
    - 価格欠損時はスキップしログに記録。

- 研究用ファクター計算（部分実装）
  - research.factor_research モジュールにモメンタム等のファクター計算基盤を追加（DuckDB 接続を受ける設計）。モジュールは prices_daily / raw_financials テーブルを参照して、モメンタム、MA200 乖離、ATR、流動性指標などを算出する方向で実装が始まっています（一部未完）。

- Paper Trading の検証ツール
  - tools.paper_verification_report を追加。Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から以下の指標を算出してレポート出力:
    - 稼働率 (uptime_pct)、総ポーリング数、エラー発生数
    - 注文成功率（Filled / Created）、送信率（Sent / Created）
    - リスク却下数（risk_logs）
    - レイテンシ: 平均・最大・P95（P95 は全値抽出後に計算）
  - デフォルトの合格基準を設定（稼働率 >= 99%、成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。PASS/FAIL 判定を出力。

- DB 初期化ユーティリティ利用
  - run_execution / run_monitoring 起動時に監視テーブルが存在することを保証するため init_monitoring_db(sqlite_conn) を呼び出す（冪等）。

### Changed
- （初回リリースのため履歴なし）

### Fixed
- （初回リリースのため履歴なし）

### Notes / Known limitations
- .env の自動ロードはプロジェクトルートが未検出の場合はスキップされます（パッケージ配布後の安全策）。
- position_sizing の price が欠損（0.0）だった場合、現在は単純にスキップします。将来的には前日終値や原価等でフォールバックする旨の TODO コメントあり。
- calc_regime_multiplier は未知レジームに対して 1.0 でフォールバックし警告を出します。設計上、Bear レジーム時は generate_signals() 側で BUY シグナルを生成しないことで保護されているため、乗数は中間的なセーフガードとして実装されています。
- logging_setup はログディレクトリ作成に失敗した場合、ファイル出力を諦めてコンソールのみで動作します。
- research.factor_research は一部実装が未完（コード断片が途中で終端しているため、完全なファクター計算関数は今後の追加が必要）。

---

今後のリリース案:
- ExecutionEngine / BrokerClient 実装の詳細ドキュメント化とエンドツーエンドの統合テスト
- factor_research の完成（すべてのファクター計算実装）
- 効率化・パフォーマンス改善（DuckDB クエリ最適化等）
- 単体テスト・CI の整備

（この CHANGELOG はコードベースの内容を元に推測して作成しています。実際の開発履歴と差異があり得ます。）