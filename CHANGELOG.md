CHANGELOG
=========

すべての日付は YYYY-MM-DD 形式で記載しています。  
この CHANGELOG は "Keep a Changelog" の形式に準拠しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-25
--------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムのコアユーティリティと CLI ツール群を導入。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
- 設定管理
  - .env 自動読み込み機能（プロジェクトルートの .env/.env.local を読み込み、OS 環境変数を保護）。
  - 高度な .env パーサーを実装（コメント、export プレフィックス、クォート内エスケープ、インラインコメントの取り扱い対応）。
  - Settings クラス（src/kabusys/config.py）で種々の設定をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
    - PAPER_FILL_MODE（instant/partial/never/reject の検証）
    - PID / KILL フラグ関連パス、閾値（CPU / Memory / Disk）、LOG_LEVEL、KABUSYS_ENV 判定ユーティリティ（is_live, is_paper, is_dev）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。

- 設定関連 CLI
  - 環境設定ウィザード: python -m kabusys.config_setup
    - 対話式に .env を作成・更新するウィザード（デフォルト値・シークレットマスク・選択肢対応）。
  - 設定検証ツール: python -m kabusys.validate_config
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML が入っていれば）パース検証。
    - --strict モードで警告を FAIL 扱いにできる。

- 実行 / 監視ランナー
  - run_execution（src/kabusys/run_execution.py）
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と完全分離。
    - BrokerClientFactory によりブローカークライアントを選択（Mock 実装を含む想定）。
    - ExecutionEngine をデーモンスレッドで起動、stop フラグ（data/stop_requested.flag）検知で安全停止。実行中の PID ファイル管理。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境に依らず本番 sqlite_path（Settings.sqlite_path）を参照する設計。停止フラグ検知でループ終了。
    - 起動時にプロセス優先度を "high" に設定。

- モジュール: portfolio（銘柄選定・配分・サイズ決定・リスク調整）
  - portfolio_builder
    - select_candidates: スコア降順（同点は signal_rank）で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（スコア合計 0 の場合は等配分にフォールバック）。
  - risk_adjustment
    - apply_sector_cap: セクター集中を抑制するフィルタ。sell_codes（当日売却予定）を考慮して既存エクスポージャーを計算。unknown セクターは上限除外。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた投下資金乗数を返す（未定義値は警告とともに 1.0 にフォールバック）。
  - position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき発注株数を算出。単元株（lot_size）丸め、1 銘柄上限・aggregate cap、cost_buffer による保守的見積り、available_cash 超過時のスケールダウン（端数処理ロジック含む）。

- 研究/集計ツール
  - factor_research（部分実装）: DuckDB の prices_daily/raw_financials を用いたファクター計算の骨組み（モメンタム等の定数と calc_momentum の開始実装あり）。
  - tools/paper_verification_report
    - Paper Trading 用 SQLite を読み、システム稼働率・注文成功率・送信率・レイテンシ（avg/max/P95）等を算出してレポート出力。
    - 基準値（稼働率 99%、成立率 90% 等）に基づく PASS/FAIL 判定。

- ユーティリティ
  - logging_setup（src/kabusys/utils/logging_setup.py）
    - すべての起動スクリプトで共通利用するログ設定ユーティリティを提供。
    - stdout 出力（StreamHandler）および日次ローテート（TimedRotatingFileHandler、デフォルト logs/、30 日保持）。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続。
  - process_priority（src/kabusys/utils/process_priority.py）
    - Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定。psutil を使用。アクセス権限不足時は警告でスキップ。
    - set_cpu_affinity により最初 N コアへピンニング可能（例外は警告でスキップ）。

- ドキュメント化・設計ノート
  - 多くの関数に設計意図、利用上の注意、将来の TODO（例: price のフォールバックなど）を docstring とコメントで追加。

Changed
- 初版リリースのため変更履歴はなし。

Fixed
- 初版リリースのため修正履歴はなし。

Deprecated
- なし

Removed
- なし

Security
- なし（注意）
  - .env は生成後に必ず Git 管理下にコミットしない旨を README/.env ヘッダに明記（config_setup の出力に含める）。

Known issues / Notes
- factor_research.calc_momentum はファイル末尾で未完（実装途中の可能性あり）。詳細実装は今後のリリースで完成予定。
- risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）だとエクスポージャーが過少見積りされる旨の TODO コメントあり。前日終値や取得原価でのフォールバック機構を今後検討予定。
- 実運用ではファイルパス（logs/, data/）の権限やディレクトリ存在に注意。validate_config による事前検証を推奨。
- プロセス優先度・CPU affinity の設定は権限や OS に依存するため、設定に失敗した場合は警告ログのみで安全に継続する設計。

利用例 / CLI
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 実行: python -m kabusys.run_execution
- 監視: python -m kabusys.run_monitoring

以上。