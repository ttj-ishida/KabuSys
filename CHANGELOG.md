CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」フォーマットに準拠しています。

0.1.0 - 2026-04-22
-----------------

Added
- 初期リリース: KabuSys 日本株自動売買システムの基盤機能を追加。
- パッケージ構成
  - モジュール群を提供: data, strategy, execution, monitoring, portfolio, research, tools, utils など。
  - バージョン情報: __version__ = "0.1.0"。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 専用 SQLite(DB: data/paper_trading.db を想定) に記録。paper_trading と本番 DB を完全分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止制御: data/stop_requested.flag を検出すると安全に停止。
    - 実行 PID を data/execution.pid に記録する仕組み（pid_file を受け渡し）。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト: 60 秒、無効値は警告のうえデフォルトにフォールバック）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視テーブルにアクセス。
    - duckdb を分析用 DB として接続。
    - 停止フラグ (data/stop_requested.flag) の検出でループを終了。

- 設定・環境管理
  - config.py
    - .env 自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml を起点に探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを抑止可能。
    - .env/.env.local の読み込み順と上書きルール（OS 環境変数を保護）を実装。
    - .env パースの強化: export 形式、クォート文字列、インラインコメント、エスケープに対応。
    - Settings クラスを追加し、各種環境変数の取得・検証ロジックを提供:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN/LINE_USER_ID 等のオプション
      - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
      - PAPER_FILL_MODE の検証（有効値: "instant" | "partial" | "never" | "reject"）
      - KABUSYS_ENV の検証（development / paper_trading / live）
      - ログレベル検証、各種閾値プロパティ（CPU/MEM/DISK）など

  - config_setup.py
    - 対話式 .env 作成ウィザードを追加。既存 .env の読み込み、値のマスク表示、デフォルト値・選択肢のサポート、最終確認後に .env を書き込む。
    - 書き込み時のテンプレート（コメント付き）を生成。

  - validate_config.py
    - 起動前チェック CLI を追加。必須環境変数・KABUSYS_ENV の妥当性・ログレベル・DB パスの親ディレクトリ存在確認・config/*.yaml の存在と YAML パース検証（PyYAML が存在する場合）・本番環境向けの追加ガードを実行。
    - --strict モードを指定すると警告も FAIL 扱いで終了コード 1 を返す。

- 監視関連
  - monitoring 側で使用する DB 初期化関数（init_monitoring_db）を利用し、各起動スクリプトで監視テーブルの整合性を保証（冪等）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を返却。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコアに基づく重み（合計が 0 の場合は等配分へフォールバックし警告を出力）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック。既存保有を基にセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外。unknown セクターは上限適用外。
    - calc_regime_multiplier: 市場レジーム ("bull"|"neutral"|"bear") に応じた投下資金乗数を返却（未知の値は警告のうえ 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" | "equal" | "score") に基づいて発注株数を算出。
      - 単元株（lot_size）丸め、1 銘柄上限・aggregate 上限（available_cash）・cost_buffer（手数料/スリッページ見積り）を考慮。
      - aggregate cap 超過時はスケーリングと残差処理により再配分。
      - risk_based ではリスク許容率（risk_pct）、stop_loss_pct を用いてポジションサイズを決定。
      - 設定不足（価格欠損等）はログでデバッグ出力を行いスキップ。

- 研究（research）
  - research/factor_research.py
    - ファクター算出基盤を追加。Momentum, Value, Volatility, Liquidity 等の定量ファクター計算を想定して設計。
    - DuckDB 経由で prices_daily / raw_financials を参照する前提の関数（例: calc_momentum）を実装開始（営業日ベースの窓や MA200 の扱いなどを記載）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード検証レポート生成ツールを追加。
    - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 指標: 稼働率(uptime)、注文成功率(fill_rate)、送信率(send_rate)、レイテンシ(P95) 等を算出。
    - CLI: --from / --to（YYYY-MM-DD）で期間指定、--db で DB パス指定。
    - 閾値（PASS/FAIL 判定）を定義（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200ms）。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定関数 setup_logging を提供。
    - stdout への StreamHandler（stdout を使用）および 日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30 日分保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続（起動時の堅牢性向上）。
  - utils/process_priority.py
    - set_process_priority(level) で Windows / POSIX を吸収してプロセス優先度を設定（Windows の定数は getattr によるフォールバック対応）。
    - set_cpu_affinity(cpu_count) を提供し、最初の N コアにピン留め可能。
    - 権限不足や未対応 OS に対する失敗時は警告を出力してスキップ。

Changed
- n/a（本バージョンは初期追加が中心のため変更履歴はなし）。

Fixed
- n/a

Deprecated
- n/a

Removed
- n/a

Security
- n/a

Notes / 運用上の注意
- .env の自動読み込みは便利だが .env を絶対に Git にコミットしないこと。
- 本番運用時は KABUSYS_ENV=live に設定すると追加チェックが走り、LINE 通知設定などを確認する警告が出る。KILL_FLAG_CLEAR_ON_START は本番では 0 推奨。
- run_monitoring と run_execution はそれぞれ監視 DB と実行 DB の取り扱いに違いがある（monitoring は常に sqlite_path を使用、execution は paper_trading の場合は paper_sqlite_path を使用）。
- DuckDB は分析用途で使用されるため、PyPI パッケージの duckdb が必要。
- 一部機能（例: research.calc_momentum の詳細実装や将来の拡張）は TODO コメントで拡張性を残している。

今後の予定（例）
- research モジュールの各ファクター実装完了と単体テスト追加
- Strategy / Execution の結合テスト・シミュレーション整備
- 銘柄ごとの lot_size 対応（stocks マスタの導入）などポジション計算の細分化

---

注: 上記はコードベースの実装内容から推測して作成した CHANGELOG です。実際のリリースノートや社内運用ドキュメントとして利用する場合は、変更の意図・担当・関連チケット等を補足してください。