# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。

## [0.1.0] - 2026-04-19

Added
- 初回公開リリース。
- 起動スクリプトを追加:
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - プロセス優先度を "high" に設定してから実行。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite (既定: data/paper_trading.db) を使用し、本番 DB と完全分離して動作。
    - BrokerClientFactory を通じてブローカークライアントを生成（MockBrokerClient の切替をサポート）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、スレッドで ExecutionEngine.run_session を実行。data/execution.pid と停止フラグ (data/stop_requested.flag) を監視して安全に停止。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境に関わらず本番用 sqlite_path（data/monitoring.db 等）を使用。
    - 停止フラグ検出によりループを終了、例外発生時はログ出力後に次ポーリングへ継続。

- 設定関連:
  - config.py
    - .env の自動ロード機能（プロジェクトルート検出: .git or pyproject.toml）。
    - .env 読み込みの上書き制御（OS 環境変数保護）。
    - 強力な .env ラインパーサ:
      - export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いを実装。
    - Settings クラス:
      - J-Quants / kabuAPI / LINE / DB パス（duckdb/sqlite/paper）等のプロパティを提供。
      - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
      - KABUSYS_ENV / LOG_LEVEL の検証と is_live/is_paper/is_dev ヘルパー。
      - PID / kill flag /閾値など監視設定の取得。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI。
    - デフォルト提示、シークレットマスク、選択肢検証、保存確認を実装。

  - validate_config.py
    - 起動前に .env と config/*.yaml の不備を検出する CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリチェック、YAML の存在・パース検証（PyYAML 未インストール時は警告でスキップ）、本番時の追加ガードを実装。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ:
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30 日保持）を設定する共通ユーティリティ。
    - LOG_LEVEL/LOG_DIR の解決順とディレクトリ作成失敗時のフォールバックを実装。
  - utils/process_priority.py
    - set_process_priority(level) で Windows / POSIX を吸収した優先度設定を提供（psutil ベース）。
    - set_cpu_affinity(cpu_count) で CPU affinity を固定するヘルパー（権限不足等は警告でスキップ）。
    - サポートレベルの検証と例外ハンドリングを実装。

- Portfolio コンポーネント:
  - portfolio/portfolio_builder.py
    - 選定・重み計算関数を提供: select_candidates, calc_equal_weights, calc_score_weights。
    - score がすべて 0 の場合は等重配分にフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有を元にセクター集中を検出し、上限超過セクターの新規候補を除外するロジックを実装。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull/neutral/bear）。
  - portfolio/position_sizing.py
    - calc_position_sizes:
      - allocation_method ("risk_based"/"equal"/"score") に基づく発注株数算出。
      - 単元株（lot_size）で丸め、1 銘柄上限・合計キャッシュ上限（aggregate cap）に基づくスケーリング、cost_buffer を考慮した保守的見積り、残余配分アルゴリズムを実装。
      - 価格欠損や不正値時のログとスキップ。

- 分析 / リサーチ:
  - research/factor_research.py（初期実装）
    - Momentum / Value / Volatility / Liquidity 系ファクター計算の設計と calc_momentum などの骨子（DuckDB 接続を前提）を追加（実装は継続中）。

- ツール:
  - tools/paper_verification_report.py
    - ペーパートレード結果検証レポート生成スクリプト。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（P95）等を集計。
    - 合格基準（稼働率 99%、成立率 90% 等）に基づく PASS / FAIL 判定を出力。
    - --from/--to/--db オプションで期間・DB を指定可能。

- パッケージメタ:
  - __init__.py にて __version__ = "0.1.0" を設定。
  - portfolio 等の public API を __all__ でエクスポート。

Changed
- N/A（初回リリースのため履歴なし）

Fixed
- N/A（初回リリースのため履歴なし）

Removed
- N/A（初回リリースのため履歴なし）

Notes / 注意事項
- .env の自動読み込みはデフォルトで有効。テスト等で自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番稼働時は KABUSYS_ENV=live の設定と LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を必ず確認してください。validate_config の本番ガードを活用してください。
- process_priority や CPU affinity の設定は権限に依存します。権限不足時は警告でスキップされます。
- Paper Trading と Live は DB を分離して管理します（デフォルト設定を変更する場合は PAPER_TRADING_SQLITE_PATH / SQLITE_PATH / DUCKDB_PATH 等を調整してください）。

-- end of changelog --