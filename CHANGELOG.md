CHANGELOG
=========

すべての重要な変更はこのファイルに記録します（Keep a Changelog 準拠）。

[Unreleased]
-------------


[0.1.0] - 2026-04-22
--------------------

Added
- 初回リリース: KabuSys v0.1.0 として基本機能を実装・公開。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成を導入（モック/本番切替対応）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を別スレッドで実行。停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）を扱う。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックして警告を出力。
    - 監視は環境にかかわらず本番の sqlite_path を使用（監視 DB を統一）。
    - 停止フラグ検知で安全にループを終了。

- 設定管理
  - config.py
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env パーサはクォート・エスケープ・コメント処理に対応（export KEY=val もサポート）。
    - Settings クラスで各種設定（DB パス、API トークン、監視閾値、環境判定等）をプロパティとして提供。環境値検証とデフォルト処理を実装。
    - PAPER_FILL_MODE のバリデーション、paper_sqlite_path 等の明示的プロパティを追加。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。シークレットはマスク表示、デフォルト値や選択肢をサポート。
    - 既存 .env 読み込み、編集確認、ファイル書き出しを実装。
  - validate_config.py
    - 起動前チェック CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース（PyYAML があれば）を検査。
    - --strict オプションで警告をエラー扱いにできる。
    - live 環境向けの追加警告（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START の危険設定など）。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler（標準出力）と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app>.log）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル解決（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度を設定するユーティリティを追加。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足や未対応 OS の際は警告を出す安全設計。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - 銘柄候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - スコア合計が 0 の場合は等金額配分にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限を行う apply_sector_cap を実装（既存保有のセクター比率が閾値超過の場合に新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear とフォールバック挙動）。
  - portfolio/position_sizing.py
    - allocation_method ("risk_based", "equal", "score") に基づく発注株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate 上限（available_cash）に合わせたスケールダウンロジック、cost_buffer を用いた保守的見積り、残差処理による端数の再配分を実装。
    - 価格欠損や price <= 0 のケースは安全にスキップしログを出力。

- 解析 / レポート
  - tools/paper_verification_report.py
    - ペーパートレード検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計。閾値判定で PASS/FAIL を表示。
    - P95 計算、日付フィルタ、DB パス解決 (--db / 環境変数 / デフォルト) に対応。
  - research/factor_research.py
    - ファクター計算の枠組みを追加（Momentum / Value / Volatility / Liquidity を想定）。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。ただしファイル末尾が一部未完（今後の実装継続を想定）。

- パッケージ基本情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
  - portfolio パッケージのエクスポート整理（__all__）。

Changed
- N/A（初回リリースのため履歴上の変更はありません）

Fixed
- N/A（初回リリース）

Security
- 環境ファイル .env はウィザードで生成されることを明記し、「絶対に Git にコミットしないこと」を .env ヘッダに注記。

Notes / Implementation details
- 監視（run_monitoring）と実行エンジン（run_execution）は停止フラグにより安全にシャットダウンできる設計（プロセス優先度を起動直後に High に設定）。
- ログは stdout を優先し、CI/cron 等での取り回しを想定（stderr ではなく stdout を使用）。
- 設定検証（validate_config）は PyYAML 非依存で存在確認を行い、PyYAML がある場合はパース検証まで行う。
- 一部ファイル（research/factor_research.py）の実装が継続中の箇所あり（今後の機能追加予定）。

変更に関する問い合わせや追加の差分説明が必要であれば、対象ファイルや関心のある機能を指示してください。