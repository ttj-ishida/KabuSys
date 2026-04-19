# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

※ 本 CHANGELOG はリポジトリの現状コードから機能・変更点を推測して作成しています。

## [Unreleased]

- 現状なし（次回リリースに向けた追加・修正をここに記載します）。

## [0.1.0] - 2026-04-19

初回リリース。以下の主要機能・ユーティリティを追加します。

### Added
- アプリケーション基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - Settings クラスを実装し、環境変数から各種設定値を取得する仕組みを提供。
    - J-Quants / kabuステーション / LINE / DB パス /ログレベル /監視閾値 等をプロパティで公開。
    - KABUSYS_ENV の検証（development / paper_trading / live）と is_live / is_paper / is_dev ヘルパーを追加。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等の paper_trading 関連設定を提供。
    - 自動 .env ロード機能を実装（.env, .env.local）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - 環境変数読み込みの堅牢なパーサ（クォート・エスケープ・コメント対応）を実装。

- 起動スクリプト / 実行系
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
    - 停止フラグファイル（data/stop_requested.flag）を検知して安全終了。
    - 例外はログに出力して次ループへ復帰する耐障害性を備える。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアントの抽象化を使用（Mock の切替を想定）。
    - エンジンは別スレッドで実行。停止フラグ検知でエンジン停止をトリガー。
    - 起動時に PID ファイルを書き、終了時に DB 接続をクローズ。

- 設定・検証 CLI
  - config_setup: 対話式ウィザードで .env を生成/更新する CLI を追加。
    - J-Quants / kabuステーション / DB パス / LINE / ログレベル / Kill Switch の設定項目を対話形式で入力可能。
    - 既存 .env 読み込み、シークレットはマスク表示、保存確認を実装。
  - validate_config: .env と config/*.yaml の検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル確認、DB パスの親ディレクトリ存在チェックなどを実施。
    - PyYAML があれば config/*.yaml のパース検証も実行。
    - --strict モードで警告を FAIL 扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils.logging_setup: 統一ログ設定ユーティリティを追加。
    - stdout に出す StreamHandler と 日次ローテーション（TimedRotatingFileHandler）を併用。
    - LOG_DIR 作成失敗時はファイル出力をスキップして stdout のみで継続。
    - ログレベル解決順（引数 > 環境変数 > デフォルト）を実装。
  - utils.process_priority: プラットフォーム差分を吸収したプロセス優先度設定を追加。
    - Windows / POSIX (Linux, macOS, FreeBSD) をサポート。psutil を使用して nice / priority を設定。
    - set_cpu_affinity を実装し、プロセスを最初の N コアにピン止めする機能を追加（利用不可時は警告でスキップ）。

- ポートフォリオ構築モジュール
  - portfolio.portfolio_builder: 候補選定・重み計算を実装。
    - select_candidates: スコア降順＋タイブレークで上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分（全スコアが 0 の場合は等分配へフォールバック）。
  - portfolio.risk_adjustment: セクターキャップ・レジーム乗数を実装。
    - apply_sector_cap: 既存保有のセクター暴露に基づき新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: regime に応じた投下資金乗数（bull/neutral/bear）を返す。未知は 1.0 でフォールバック。
  - portfolio.position_sizing: 株数決定ロジックを実装。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - risk_based: 損切り幅・許容リスクからベース株数を算出。
    - equal/score: weight に基づく割当てと per-position / aggregate 上限処理。
    - 単元株（lot_size）丸め、cost_buffer を考慮した保守的なコスト見積り、aggregate cap 超過時のスケールダウンと端数配分ロジックを実装。

- Paper Trading 検証ツール
  - tools.paper_verification_report: ペーパートレード DB のレポート生成ツールを追加。
    - 稼働率、注文成立率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出。
    - P95 計算、時間フィルタ（--from / --to）対応、閾値に基づく PASS/FAIL 判定を実装。
    - PAPER_TRADING_SQLITE_PATH 環境変数または --db で DB ファイルを指定可能。

- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を呼ぶことで監視テーブルの存在を保証（冪等に初期化）。

- 研究用ファクターモジュール（着手）
  - research.factor_research: DuckDB からデータを読み取ってモメンタム等のファクターを計算するモジュールを追加（モジュールは実装中で一部未完）。

### Changed
- 監視・実行プロセスの起動順序と、安全停止ハンドリングを統一。
  - 起動直後にプロセス優先度を "high" に設定する処理を全起動スクリプトで共通化。

### Fixed
- 環境変数パースの堅牢化
  - .env パーサでクォート・エスケープ・インラインコメントを適切に扱うよう改善。export プレフィックスにも対応。
- MONITOR_POLL_INTERVAL の不正値に対するフォールバックを実装（0 以下や非整数値は警告を出してデフォルト 60 秒に戻す）。

### Documentation
- 各モジュールに docstring / 使用例を追加し、CLI の使い方や設計意図（PortfolioConstruction.md 等）への参照を明記。

### Notes / Migration
- PAPER_TRADING 環境では paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）が使われ、本番 DB（data/monitoring.db）とは完全に分離されます。運用時は環境変数 KABUSYS_ENV を適切に設定してください。
- .env 自動ロード機能はプロジェクトルートを .git または pyproject.toml で検出します。配布後や特殊な構成では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- ログは既定で logs/ 配下へ出力されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

---

今後の計画（想定）
- research.factor_research の完成（ファクター計算の SQL 実装完了）。
- テストカバレッジの追加と CI 設定。
- ExecutionEngine / BrokerClient のさらなるエラーハンドリング強化と監視メトリクス拡充。