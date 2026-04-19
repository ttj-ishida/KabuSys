# Changelog

すべての重要な変更点を記録します。これは Keep a Changelog の形式に準拠しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

比較的初期のリリースであるため、本ファイルはコードベースから推測できる主要機能・挙動・注意点をまとめた「初版の機能一覧」的なリリースノートになっています。

## [Unreleased]

## [0.1.0] - 2026-04-19
### Added
- 基本構成とコアモジュールを追加（初期リリース）。
  - パッケージ: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler 組み立て。
    - エンジンはスレッドで実行され、data/stop_requested.flag を監視して安全に停止可能。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority.set_process_priority を利用）。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト: 60 秒）。不正値は警告しデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に関係なく本番の sqlite_path（data/monitoring.db をデフォルト）を使用。
    - data/stop_requested.flag を検知するとループを終了。
    - プロセス優先度を起動直後に "high" に設定。

- 設定管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索して特定）。
    - 読み込み順: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env の各行パーサを独自実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いなどに対応）。
    - Settings クラス: 環境変数をラップして型変換・妥当性チェック（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
    - DB/ログ/監視関連のパスやしきい値等をプロパティで提供。

  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI（python -m kabusys.config_setup）。
    - 主要な設定項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE 設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）。
    - 既存 .env 読み込み、シークレットマスク表示、保存確認などをサポート。

  - validate_config.py
    - 起動前に .env と config/*.yaml のチェックを行う CLI（python -m kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の確認、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および (PyYAML が利用可能なら) パース検証、KABUSYS_ENV=live 時の追加ガード等を実施。
    - --strict オプションで警告を FAIL 扱いにできる。

- Logging / プロセスユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティ（setup_logging）。
    - stdout (StreamHandler) と 日次ローテートのファイルハンドラ (TimedRotatingFileHandler) をルートロガーに設定。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップし stdout のみで継続。
  - utils/process_priority.py
    - set_process_priority(level) で Windows/Linux/macOS に対して適切な優先度設定を実施（権限不足や未対応 OS の場合は警告でスキップ）。
    - set_cpu_affinity(cpu_count) によりプロセスを先頭 N コアにピン留め（権限や OS に依存し失敗する場合は警告）。

- ポートフォリオ構築関連（純粋関数群、DB非依存）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N を返す（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分を算出。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等金額へフォールバック（警告出力）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター割合が上限を超える場合、新規候補を除外するロジック（"unknown" セクターは上限適用しない）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を返す（"bull"=1.0, "neutral"=0.7, "bear"=0.3）。未知レジームは 1.0 にフォールバック（警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数を算出。
      - allocation_method: "risk_based"（リスクベース） / "equal" / "score" をサポート。
      - risk_based: 損切り率・リスク許容率から株数算出。
      - equal/score: ウェイトに基づく配分。max_position_pct, max_utilization, lot_size（単元）等を考慮。
      - aggregate cap のため投資総額が available_cash を超える場合はスケーリングし、端数（lot_size 単位）を残差に基づいて再分配するアルゴリズムを実装。
      - cost_buffer により手数料/スリッページを保守的に見積もり。
      - 一部 TODO（将来的に銘柄ごとの lot_size を導入する旨の記載）。

- 監視・監査データベース
  - monitoring_db の初期化を保障する関数（起動スクリプトで呼び出し）。（監視テーブルが存在しない場合でも冪等に作成する仕様）

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB（PAPER_TRADING_SQLITE_PATH 環境変数で指定可）から統計を集計し、検証レポートを出力する CLI。
    - 取得指標:
      - システム稼働率（system_status）
      - 注文成功率 / 送信率（trade_logs の Created/ Filled/ Sent カウント）
      - リスク却下数（risk_logs）
      - レイテンシ（平均・最大・P95）
    - Pass/Fail 判定基準（デフォルト閾値）を定義:
      - 稼働率 >= 99.0%
      - 注文成立率 (fill) >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - CLI オプション: --from, --to, --db（期間フィルタ・DBパス指定）

- 研究（research）モジュール（初期実装）
  - research/factor_research.py
    - DuckDB 接続を受け取り、prices_daily / raw_financials を基にモメンタム・バリュー・ボラティリティ・流動性等のファクター計算を行う設計（calc_momentum 等を含む）。
    - 設計上の方針と定数（期間設定等）を実装。なおソースの一部が切れている箇所があり、実装継続が必要。

### Changed
- N/A（初版のため "Added" に該当する変更点のみ記載）。

### Fixed
- N/A（初版）。

### Known limitations / Notes
- .env パーサは多くのケースに対応するが、完全な shell レベルのパースではない。特殊ケースは注意。
- process priority / CPU affinity は OS と権限に依存するため、設定に失敗する場合は警告を出してスキップする実装。
- run_monitoring は monitoring DB（SQLITE_PATH）を KABUSYS_ENV にかかわらず使用するため、ローカルテスト時に本番 DB を誤って使用しないよう注意が必要。paper_trading の実行は run_execution 側で PAPER_TRADING_SQLITE_PATH を使用して分離される。
- portfolio.position_sizing の将来的な拡張点:
  - 銘柄別の lot_size をサポートする設計への移行（TODO コメントあり）。
- risk_adjustment.apply_sector_cap は price_map に 0.0 が含まれるとエクスポージャーを過少見積もる可能性があり、前日終値等のフォールバックが必要になり得る（TODO コメント）。
- research/factor_research.py はファイル末端が切れている（実装未完）ため、実行前に完成させる必要あり。

### Documentation / CLI usage (主要コマンド)
- .env 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

### Security
- 機密値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE_CHANNEL_ACCESS_TOKEN 等）は .env に保存する設計になっているが、.env を Git にコミットしない旨を README/ヘッダに明示している（config_setup の出力参照）。

---

本 CHANGELOG はソースコードの内容とコメント（docstring / TODO / CLI ヘルプ等）から推測して作成しています。実際の変更履歴やリリースノート作成時は、コミットログ / リリース担当者による検証を行ってください。