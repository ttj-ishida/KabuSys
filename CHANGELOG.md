CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。

Unreleased
----------

- なし

0.1.0 - 2026-04-23
------------------

Added
- プロジェクト初回リリース（バージョン 0.1.0）。
- コア起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度を設定し、SQLite / DuckDB に接続してエンジンをバックグラウンドスレッドで実行。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）を監視し、フラグ検出で安全に停止。
    - 実行時 PID を data/execution.pid に保存する（Engine 側の pid_file パスを使用）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視情報を記録。
    - 停止フラグ検出でループ終了、KeyboardInterrupt をハンドリングしてクリーンアップ。

- 設定・環境変数管理
  - config.py
    - .env 自動読み込み（プロジェクトルートを .git / pyproject.toml から探索）。
    - .env 読み込み時の優先度: OS 環境変数 > .env.local > .env。
    - .env の行パーサを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
    - Settings クラスを追加し、アプリケーション設定（J-Quants / kabu API / DB パス /監視閾値 / 環境種別 等）をプロパティとして提供。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - 環境種別（KABUSYS_ENV）のバリデーション（development / paper_trading / live）。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。デフォルト値やシークレットマスク表示に対応。
  - validate_config.py
    - 起動前検証 CLI を追加。必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在チェック（PyYAML があれば YAML のパース検証も実施）。
    - --strict フラグで警告を FAIL 扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
    - ログレベル・ログディレクトリの解決順を実装（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - プロセス優先度および CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分吸収。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。アクセス権や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群、DB 参照なし）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア順にソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分を実装（全スコア 0 の場合はフォールバックで等配分し警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限を適用して新規候補を除外するロジックを実装（売却予定銘柄はエクスポージャー計算から除外）。"unknown" セクターは上限除外の対象外とする挙動を明記。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームでは 1.0 にフォールバックし警告出力。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき銘柄ごとの発注株数を計算。
    - リスクベース計算（risk_pct, stop_loss_pct に基づく）、単元株丸め（lot_size）、1銘柄上限・全体利用率上限、コストバッファ考慮の aggregate cap スケーリング、残差分の分配ロジックを実装。

- 解析・ツール
  - tools/paper_verification_report.py
    - Paper Trading 向けの検証レポート生成 CLI を追加。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、P95 レイテンシなどを算出して PASS/FAIL 判定（閾値はソース内定義）。
    - データフィルタリング（--from / --to）対応と DB パス解決ロジック（引数 > 環境変数 > デフォルト）。
  - research/factor_research.py
    - ファクター計算モジュール（モメンタム / MA200 / ATR / ボリューム等）を追加（DuckDB 接続を受け prices_daily / raw_financials を参照する設計）。※ファイル先頭にて設計方針と定数を実装。calc_momentum の実装が開始されている（注: 一部実装が未完の可能性あり）。

- パッケージ情報
  - __init__.py にて __version__="0.1.0" を設定。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / 注意事項
- .env ファイルは絶対にリポジトリにコミットしないこと（config_setup のヘッダに注意書きあり）。
- run_monitoring は監視用 DB（settings.sqlite_path）を環境にかかわらず本番パスとして接続する設計であるため、テスト環境での実行時は sqlite_path を適切に設定すること。
- Paper Trading と Live は SQLite を分離しているが、DuckDB（分析用）は共通 path を使用する設計となっている（必要に応じて環境変数 DUCKDB_PATH を調整してください）。
- research/factor_research.py は計算方針をまとめた状態で一部実装が途中のため、利用する際は実装状況を確認してください。

もし CHANGELOG に追記すべき点（例: 実装の詳細、リリース日付の修正、未完の関数の明示など）があれば指示してください。