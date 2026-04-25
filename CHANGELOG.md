# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-04-25

初回リリース。KabuSys のコアユーティリティ、起動スクリプト、設定管理、ポートフォリオ構築、ペーパートレード検証ツールなどを実装しました。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト: 60秒）。無効な値や 0 以下は警告ログを出してデフォルトにフォールバック。
    - 監視プロセス起動時にプロセス優先度を "high" に設定。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番の sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）検知による安全終了をサポート。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を利用し、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - 停止フラグ検知によりエンジン停止・安全終了処理を実装。
    - 実行用 PID ファイル出力対応（data/execution.pid をデフォルト）。
- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml 基準）。`.env.local` は `.env` をオーバーライドする形で適用。
    - export KEY=val 形式やクォート内のエスケープ、インラインコメントの扱いなどに対応した堅牢な .env パーサを実装。
    - Settings クラスを実装し、J-Quants / kabu API / LINE / DB / 監視閾値 / システム設定などをプロパティ経由で取得可能に。
    - `PAPER_FILL_MODE` の妥当性チェックや `KABUSYS_ENV` / `LOG_LEVEL` の検証を追加。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を実装。シークレット値はマスク表示、既存値の再利用、保存前の確認を提供。
    - デフォルトテンプレートの .env 書き出しを実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml の整合性を検査する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在とパース検証（PyYAML が存在する場合）を行う。
    - `--strict` を指定すると警告も失敗扱いで exit(1)。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで利用する統一ログ設定ユーティリティを追加。
    - stdout へ出力する StreamHandler と日次ローテーション（TimedRotatingFileHandler）によるファイル出力（logs/<app_name>.log）を設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）を実装。
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定機能（high/normal/low）を追加。アクセス拒否等は警告でスキップ。
    - CPU affinity を最初の N コアに固定するヘルパー set_cpu_affinity を追加。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - シグナルのソーティング（スコア降順、signal_rank によるタイブレーク）と候補選択関数 select_candidates を実装。
    - 等金額配分 calc_equal_weights とスコア加重配分 calc_score_weights（全スコアが 0 の場合は等分にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（当日売却予定銘柄の除外や "unknown" セクターの扱い）。
    - 市場レジームに応じた乗数 calc_regime_multiplier を実装（bull/neutral/bear とフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数計算 calc_position_sizes を実装。allocation_method に応じて risk_based / equal / score の各方式をサポート。
    - 単元株（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）に基づくスケールダウン処理を実装。cost_buffer を考慮した保守的見積りもサポート。
    - スケールダウン時に残余キャッシュを fractional 残差に基づいて配分するロジックを実装。
- Paper Trading ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）を読んで検証レポートを生成する CLI を追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを計算して PASS/FAIL 判定を出力。デフォルト閾値を定義（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200ms）。
    - 日付フィルタ（--from / --to）や --db オプションをサポート。DB が存在しない場合に分かりやすいエラーメッセージを出力。
- 研究用モジュール（部分実装）
  - research/factor_research.py
    - DuckDB を使ったモメンタム等ファクター計算のための基盤コードを追加（未完の関数あり、設計方針と定数を含む）。
- パッケージメタ
  - パッケージ初期化ファイルでバージョンを 0.1.0 に設定。

### Changed
- 監視・実行の DB 挙動について明確化
  - 監視（run_monitoring）は環境変数 KABUSYS_ENV にかかわらず監視用（本番） sqlite_path を使用して監視テーブルを初期化する設計とした（監視データは本番 DB を参照する意図）。
  - 実行（run_execution）は paper_trading 環境時に専用の paper_sqlite_path を使用して本番 DB と分離。

### Fixed / Defensive improvements
- .env パーサの堅牢化（config._parse_env_line）
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを考慮してパースするよう改善。無効行は無視。
- MONITOR_POLL_INTERVAL の不正値処理
  - run_monitoring のポーリング間隔読み取り時に整数変換や 0 以下の値によるエラーを捕捉し、警告を出してデフォルトにフォールバックするようにした。
- logging_setup のフォールバック処理
  - ログディレクトリの作成に失敗した場合でもコンソール（stdout）ログのみで起動を継続するようにした。ファイルハンドラ作成失敗時は警告ログ出力。
- process_priority のエラー耐性
  - アクセス拒否や未実装 API による例外を捕捉し、警告を出して処理をスキップするようにした。

### Notes / Known limitations
- research/factor_research.py の関数は一部未完（ファイル末尾で途中切れ）。本リリースでは設計・定数・関数シグネチャを導入しており、実装の継続が必要です。
- 一部コンポーネント（SystemMonitor、monitoring_db、ExecutionEngine、Broker 実装など）は本パッケージ内で参照されているが、このリリースにおいては当該実装の存在を前提としており、別ファイルでの実装や将来の拡張が必要です。
- パーミッションや OS ごとの差異により、プロセス優先度・CPU affinity の設定が行えない場合がある（警告出力してスキップ）。

---

今後の予定（例）
- factor_research の完全実装とユニットテスト追加
- SystemMonitor / ExecutionEngine 周りの統合テスト強化
- 個別銘柄ごとの lot_size サポート（stocks マスタの導入）
- CI 上での config 検証と自動化

以上。