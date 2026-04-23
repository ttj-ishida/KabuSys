# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。主にコードベースから推測できる機能追加・改善点を記載しています。

## Unreleased

- （なし）

## [0.1.0] - 2026-04-23

### Added
- 実行用エントリポイントを追加
  - run_execution.py: ExecutionEngine を起動するスクリプトを実装。KABUSYS_ENV に応じて paper_trading 用の専用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用し、BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてエンジンを起動する。停止は data/stop_requested.flag によるフラグ検出で行う。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。監視は本番 sqlite_path を常に参照し、停止フラグ（data/stop_requested.flag）でループを終了する。

- 設定・環境変数管理
  - config.py: プロジェクトルート検出（.git / pyproject.toml）に基づく .env 自動読み込み機能を追加。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを抑制可能。.env のパースはシングル/ダブルクォートや export 形式、インラインコメントに対応。Settings クラスを実装し、J-Quants / kabu API / データベース / 監視閾値 / システム設定等のプロパティを提供。PAPER_FILL_MODE の妥当性チェックや KABUSYS_ENV / LOG_LEVEL の検証を含む。
  - config_setup.py: .env を対話式に作成・更新するウィザードを実装。既存値の読み込み、シークレット扱い、選択肢提示、保存確認を備える。

- 設定検証 CLI
  - validate_config.py: .env と config/*.yaml の存在・基本的妥当性検証ツールを追加。必須環境変数チェック、KABUSYS_ENV の警告、DB パスの親ディレクトリチェック、YAML のパース確認（PyYAML の有無に応じてスキップ）等を実行。--strict オプションで警告を FAIL 扱いにできる。

- ロギングとプロセス管理ユーティリティ
  - utils/logging_setup.py: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定するユーティリティを追加。ログディレクトリ自動作成や、既存ハンドラのクリーンアップを行う。LOG_LEVEL/LOG_DIR の優先解決に対応。
  - utils/process_priority.py: Windows / POSIX（Linux/Mac/FreeBSD）に対応したプロセス優先度設定機能を追加。CPU affinity 設定関数も提供。アクセス権限エラー等は警告でスキップする堅牢な実装。

- ポートフォリオ構築関連関数（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順（タイブレークに signal_rank）で選出。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。スコア合計が 0 の場合は等配分にフォールバックし警告を出す。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限の適用（既存ポジションのセクター露出に基づき新規候補を除外）。"unknown" セクターは制限対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（既定値とフォールバック動作を明示）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づいた発注株数算出を実装。損切り率・リスク率・単元株（lot_size）丸め・max_position_pct・max_utilization・cost_buffer を考慮した aggregate cap スケーリングと残差処理（fractional remainders による再配分）を含む。

- Paper Trading 向け検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH で指定可）からデータを集計し、稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）、リスク却下数などの指標を算出して標準出力にレポートを出力するスクリプトを追加。閾値（稼働率 99% 等）を満たすか PASS/FAIL 判定を行う。

- 研究用ファクター計算（初期実装）
  - research/factor_research.py: DuckDB の prices_daily / raw_financials を用いたファクター計算モジュールを追加（モメンタム、MA200 乖離、ATR、ボリューム指標等を設計）。calc_momentum 等の関数が実装されており、DuckDB 接続を受け取って (date, code) ベースの結果を返す設計。注：ファイル末尾が途中で切れている箇所があるため、さらに実装継続の余地あり。

### Changed
- 初回リリースのため該当なし（初期実装群）。

### Fixed
- 該当なし（初版リリース）。

### Deprecated
- 該当なし。

### Removed
- 該当なし。

### Notes / 注意事項
- .env の自動読み込みはプロジェクトルート検出に依存する（.git または pyproject.toml が目印）。プロジェクトルートが見つからない場合は自動ロードをスキップする。
- 本番用と paper_trading 用で SQLite DB を完全に分離する設計（settings.is_paper 判定で paper_sqlite_path を使用）。
- run_execution/run_monitoring は stop flag（data/stop_requested.flag）を用いて安全に終了できるようになっている。また実行中は pid ファイル（data/execution.pid など）を使用する設計。
- PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等は Settings で厳密に検証され、不正値は例外を投げる（起動前に validate_config でチェックすることを推奨）。
- research/factor_research.py はモメンタム等の計算を意図した実装が進められていますが、ファイル末尾に未完の部分が見られるため、本格運用前に追加実装・レビューが必要です。

---

初回の正式リリース相当のまとめです。必要であれば各ファイルごとの詳細な変更点（関数一覧・引数仕様・戻り値・例外挙動など）を別途ドキュメントとして展開できます。どのレベルの詳細を出力しますか？