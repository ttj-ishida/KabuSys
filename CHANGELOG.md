# Changelog

すべての注目に値する変更はこのファイルに記録します。  
形式は「Keep a Changelog」に準拠します。  

最新リリース: 0.1.0 (初回公開)

---

## [Unreleased]

（なし）

---

## [0.1.0] - 2026-04-24

初回リリース。以下の主要機能・ユーティリティ・CLI を含みます。

### Added
- 全体
  - パッケージ初期バージョンを追加（kabusys v0.1.0）。
  - パッケージ公開用の __version__ を設定（src/kabusys/__init__.py）。

- 実行/監視ランナー
  - run_execution: 実際の ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper trading SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory からブローカークライアントを作成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで起動。
    - 停止制御: data/stop_requested.flag を検知して安全に停止。起動時には data/execution.pid を使用。
    - RiskManager のデフォルト構成（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）をコード内で定義。initial_portfolio_value を broker.get_available_cash() から取得して初期化。

  - run_monitoring: システム監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL（デフォルト 60 秒）で上書き可能（不正値はデフォルトにフォールバックして警告出力）。
    - 停止フラグ data/stop_requested.flag を検知してループ終了。
    - Monitoring は実行環境にかかわらず本番 sqlite_path を使用して監視情報を記録。

- 設定管理
  - Settings クラスを追加（src/kabusys/config.py）。
    - .env 自動読込機能: プロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env` と `.env.local` を読み込む。OS 環境変数を保護する仕組みあり（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - 各種設定プロパティを提供（J-Quants / kabuAPI / LINE / DB パス / 監視しきい値 / 環境種別 / ログレベル 等）。
    - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"）や KABUSYS_ENV の検証（development/paper_trading/live）など。

  - 設定ウィザード CLI（src/kabusys/config_setup.py）
    - 対話式で .env の初期作成・更新を支援。シークレット値は入力時にマスクして表示。
    - .env の読み書き処理を提供し、生成ファイルヘッダにコミット禁止の注意書きを追加。

  - 設定検証 CLI（src/kabusys/validate_config.py）
    - 起動前に必須環境変数・KABUSYS_ENV の妥当性・ログレベル・DB パスの親ディレクトリ・config/*.yaml の存在と YAML パース（PyYAML が利用可能な場合）を検査。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ（src/kabusys/portfolio/*）
  - portfolio_builder: シグナル選別および重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
    - calc_score_weights は全銘柄スコアが 0 の場合に等金額配分へフォールバックして警告出力。
  - risk_adjustment: セクター集中制限とレジーム乗数（apply_sector_cap, calc_regime_multiplier）。
    - apply_sector_cap は "unknown" セクターを上限適用外にする等の保守的な処理を実装。
    - calc_regime_multiplier は "bull"/"neutral"/"bear" を定義、未知レジームは 1.0 でフォールバックし警告を出す。
  - position_sizing: 発注株数計算（calc_position_sizes）。
    - allocation_method に "risk_based", "equal", "score" をサポート。
    - 単元株（lot_size）で丸め、銘柄ごとの上限(max_position_pct)、aggregate cap（available_cash）を考慮したスケーリングと端数処理を実装。
    - cost_buffer を導入してスリッページ・手数料を保守的に見積もる。

- ユーティリティ
  - ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - ルートロガーを初期化し、StreamHandler (stdout) と TimedRotatingFileHandler（日次、30世代保持）を設定。
    - 既存ハンドラをクリアして二重設定を防止。ログディレクトリの作成失敗時はファイル出力をスキップして警告出力。
    - stdout を使用することでログリダイレクト運用に対応。

  - プロセス優先度 / CPU affinity（src/kabusys/utils/process_priority.py）
    - set_process_priority(level): Windows / POSIX（Linux, Darwin, FreeBSD）間の差分を吸収して優先度を設定。アクセス拒否等は警告でスキップ。
    - set_cpu_affinity(cpu_count): 最初の N コアにプロセスをピン固定するユーティリティを提供（安全チェックあり）。

- 監視 DB 初期化（参照）
  - init_monitoring_db を呼び出して監視テーブルが存在することを保証（冪等性）。

- Paper Trading 関連ユーティリティ
  - paper_verification_report CLI（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading の検証レポートを生成。システム安定性（稼働率）、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）を算出。
    - デフォルト DB パスは data/paper_trading.db。--from / --to / --db オプションをサポート。
    - PASS/FAIL 判定閾値を静的に定義（稼働率 99% など）。

- リサーチ（途上）
  - research/factor_research モジュールを追加（DuckDB を使ったファクター計算の骨組み）。モメンタム / Value / Volatility / Liquidity 等の計算方針を実装予定（calc_momentum の実装が開始されているが一部まで実装）。

### Changed
- ログ出力
  - すべての起動スクリプトから統一的に setup_logging を呼び出すようにしてログ設定を共通化。
  - StreamHandler を stdout に統一（cron 等からの起動時に stdout/stderr を統合して扱えるよう配慮）。

- .env の読み込み優先度
  - OS 環境変数 > .env.local > .env の順で読み込み。既存 OS 環境変数は保護される（上書きされない、ただし .env.local は override=True で上書き可能だが protected セットは除外）。

### Fixed
- 環境変数パースの堅牢化（src/kabusys/config.py）
  - export プレフィックスや引用符付き値のエスケープ、行内コメントの扱いなどを正しく処理するように改良。
  - _parse_env_line により無効行や不正フォーマットを安全にスキップ。

### Security
- .env 管理に関する注意
  - config_setup が生成する .env ヘッダに「.env は絶対に Git にコミットしない」旨を明記。シークレットは対話時にマスク表示。

---

## 注意事項 / マイグレーションノート
- モニタリング DB と実行エンジンの DB 分離
  - paper_trading モードでは paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番データと完全に分離されます。運用時は KABUSYS_ENV を適切に設定してください。

- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能。0 以下や整数以外の値は無効としてデフォルト 60 秒にフォールバックします。

- Kill Switch / Stop Flag
  - 停止フラグは data/stop_requested.flag を参照しており、このフラグを立てることで監視・実行プロセスを安全に停止できます。
  - config_setup にて KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に Kill Flag を自動クリアしますが、本番環境（KABUSYS_ENV=live）では危険な設定なので注意喚起があります。

- ログファイル出力の失敗
  - ログディレクトリの作成やファイルハンドラ作成に失敗した場合は警告を出してコンソール出力のみで継続します。ログディレクトリの権限やパスを確認してください。

- 未実装 / 既知の制限
  - research/factor_research の一部機能は実装途中（ファイル末尾が切れている/補完が必要）。DuckDB に依存する分析系コードの完全なテスト・検証が必要です。
  - position_sizing の lot_size は現状グローバル一律の扱い（将来的に銘柄別単元対応の拡張を予定）。
  - apply_sector_cap の price 欠損（0.0）時のエクスポージャー過少見積りに関する TODO が残っています。

---

以上。リリースに関する詳細や追加の変更履歴（パッチ・バグ修正等）は、今後のコミットに応じて Unreleased セクションに追記してください。