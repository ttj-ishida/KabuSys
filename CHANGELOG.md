# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。

最新リリース
=============

Unreleased
----------

（なし）

既知のリリース
===============

[0.1.0] - 2026-04-23
-------------------

Added
- 初期リリース（バージョン 0.1.0）。
- 起動スクリプトを追加:
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離する。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、スレッドでの ExecutionEngine 実行と停止フラグ（data/stop_requested.flag）監視を実装。
    - プロセス優先度を "high" に設定するユーティリティ呼び出しを導入。
    - 実行中 PID の保存先（data/execution.pid）を使用。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する実装。
    - 停止フラグ（data/stop_requested.flag）によるループ終了、例外安全な loop 実装。
- 環境設定・読み込み:
  - config.py
    - .env 自動ロード（プロジェクトルート検出：.git または pyproject.toml）。
    - .env の構文パーサ実装（export プレフィックス、シングル/ダブルクォート、インラインコメント、エスケープ対応）。
    - Settings クラスで環境変数を型安全に取得するプロパティ群を提供（J-Quants / kabu / LINE / DB / 監視 / システム設定等）。
    - Paper Trading 用設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）をサポート。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
- 設定関連 CLI:
  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する機能。
    - 入力時にシークレットはマスク表示、デフォルト／既存値の再利用、ファイル書き出しテンプレートを実装。
  - validate_config.py
    - 起動前の検証ツール（必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリチェック、config/*.yaml の存在および YAML パースチェック（PyYAML があれば実行））。
    - --strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築ライブラリ:
  - kabusys.portfolio
    - portfolio_builder.py
      - select_candidates: BUY シグナルをスコア降順 / signal_rank によるタイブレークで選定。
      - calc_equal_weights / calc_score_weights: 等配分・スコア加重の重み計算（スコア合計が 0 の場合は等配分にフォールバック）。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中制限の適用（既存保有を考慮し、上限超過セクターの新規候補を除外）。"unknown" セクターは除外対象外。
      - calc_regime_multiplier: レジームに応じた投下資金乗数（bull:1.0 / neutral:0.7 / bear:0.3）、未知レジームはフォールバックと警告。
    - position_sizing.py
      - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算、単元株丸め(lot_size)、1銘柄上限、aggregate cap（available_cash）に対するスケーリング、cost_buffer による保守的見積り、端数調整アルゴリズムを実装。
- ユーティリティ:
  - utils/logging_setup.py
    - 統一的ロギング設定ユーティリティ（setup_logging）。
    - stdout への StreamHandler と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。LOG_DIR/LOG_LEVEL に基づく解決。既存ハンドラをクリアして二重設定を防止。
  - utils/process_priority.py
    - set_process_priority(level) — Windows / POSIX（Linux, Darwin, FreeBSD）に対応した優先度設定。失敗時は警告でスキップ。
    - set_cpu_affinity(cpu_count) — 指定コア数にプロセスを固定する機能（アクセス権限等で失敗する場合は警告でスキップ）。
- Paper Trading 検証ツール:
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）を読み、システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計しレポート出力。
    - パス/期間指定オプション（--db, --from, --to）をサポート。P95 計算、閾値を用いた PASS/FAIL 判定を実装（稼働率 >= 99% 等の基準）。
- research/factor_research.py（ファクター計算の雛形）
  - DuckDB を利用して Momentum / Value / Volatility / Liquidity 系のファクターを計算する設計。calc_momentum 等の関数が実装途中にある（将来的なファクター計算を意図）。

Changed
- パッケージ初期化:
  - kabusys.__init__ に __version__ = "0.1.0" を追加。

Notes / Remarks
- DB とログの取り扱い:
  - run_monitoring は環境に関係なく Settings.sqlite_path（監視 DB）を使用。
  - run_execution は paper_trading 環境では paper_sqlite_path を使用し、本番と DB を分離。
- セキュリティ / 運用上の注意:
  - .env は絶対にリポジトリにコミットしないことを README に明記している（config_setup のヘッダ）。
  - validate_config は本番（KABUSYS_ENV=live）時に LINE 通知設定未設定や Kill Switch 設定が危険な値になっていないか警告を出す。
- 実行時の保護:
  - stop_requested.flag / kill.flag / execution.pid 等のファイルを用いた外部制御（停止・PID 管理）をサポート。
- 未実装 / TODO:
  - portfolio.position_sizing の価格フォールバック（price が欠損時の取り扱い）や銘柄毎の lot_size 拡張は TODO コメントとして残されている。
  - research/factor_research は一部未完（ファイル末尾で calc_momentum の実装が途中で終わっている箇所あり）。

Fixed
- （なし、初回リリース）

Deprecated
- （なし）

Removed
- （なし）

Security
- （なし）

---

注: 本 CHANGELOG はリポジトリ内のコードから推測して作成しています。挙動や公開 API の詳細は各モジュールの docstring / コメントを参照してください。