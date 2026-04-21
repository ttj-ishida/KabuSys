CHANGELOG
=========

すべての注目すべき変更点を記録します。形式は "Keep a Changelog" に準拠しています。

## [0.1.0] - 2026-04-21

Added
-----
- 初期リリース: KabuSys 基本コンポーネントを実装。
- 環境設定/管理
  - Settings クラスを実装（src/kabusys/config.py）。.env ファイルと環境変数から設定値を読み込み、各種プロパティ（J-Quants / kabuステーション / DB パス / 監視閾値 / 実行環境 等）を提供。
  - .env 自動読み込み機能を実装。プロジェクトルートを .git または pyproject.toml で検出し、.env / .env.local を適切な優先度で読み込む。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パーサーの強化: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応（src/kabusys/config.py）。
- 設定関連 CLI
  - 対話式環境設定ウィザードを追加（src/kabusys/config_setup.py）。.env の初期作成・更新を支援。シークレット項目は表示時にマスク。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。必須環境変数、KABUSYS_ENV/LOG_LEVEL、DB パス、config/*.yaml の存在と YAML パースチェック（PyYAML がある場合）などを検証。--strict オプションで警告も失敗扱いにできる。
- 実行ユーティリティ
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。プロセス優先度設定、paper_trading 環境では専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離、BrokerClientFactory によるブローカークライアント生成、OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てとデーモン実行、停止フラグ（data/stop_requested.flag）による安全停止、PID ファイル管理をサポート。
  - SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（不正値はデフォルト 60 秒にフォールバック）。監視用 DB は環境に依存せず本番 sqlite_path を使用。停止フラグでループを終了し、check_once() 内の例外はログに落として次ポーリングに進む。
- ロギング / プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。コンソール(stdout) と 日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。LOG_DIR / LOG_LEVEL の解決・フォールバックを実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度 / CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。Windows/Linux/macOS の差分を吸収して優先度設定を試行。未対応 OS や権限不足時は警告を出して安全にスキップ。
- ポートフォリオ構築モジュール（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順、タイブレークに signal_rank。
    - calc_equal_weights, calc_score_weights（スコア全て 0 の場合はフォールバックで等金額配分）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存ポジションのセクター露出を計算し上限を超えるセクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear、未知レジームは 1.0 で警告）。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: risk_based / equal / score の配分方式をサポート。単元（lot_size）丸め、1銘柄上限・aggregate cap のスケーリング、コストバッファ考慮（手数料・スリッページ見積り）。
  - 上記関数群をまとめたパッケージエクスポート（src/kabusys/portfolio/__init__.py）。
- Paper Trading 検証レポート
  - paper_verification_report スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。paper_trading の SQLite（PAPER_TRADING_SQLITE_PATH）から指標を集計し、稼働率（uptime）、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL 判定。P95 計算、日付フィルタ、DB 存在チェック、欠損テーブルに対するフォールバックを実装。
- 研究用ファクター計算（着手）
  - factor_research モジュールの骨組み（src/kabusys/research/factor_research.py）。DuckDB を使って momentum / volatility / value / liquidity 等を計算する設計方針と定数を実装（関数 calc_momentum の途中まで実装）。

Changed
-------
- パッケージ初期バージョンとして API と CLI の責務を明確化。実行・監視・設定・検証・分析（DuckDB）を分離した設計を採用。

Fixed
-----
- .env のパースに関する細かいケース（クォート内のバックスラッシュエスケープ、コメント解釈）を扱うように改善（src/kabusys/config.py）。
- ログの二重登録防止: setup_logging は既存ハンドラを閉じてから再設定するようにして、複数回呼び出し時の重複を防止。

Security
--------
- .env の生成スクリプトで「.env を絶対に Git にコミットしないこと」を明記（src/kabusys/config_setup.py）。

Notes / Usage highlights
-----------------------
- 実行環境は KABUSYS_ENV によって切り替え（development / paper_trading / live）。paper_trading 時は発注はモック化され、専用 SQLite を使用して本番 DB と分離する設計。
- MONITOR_POLL_INTERVAL に不正な値を与えた場合は警告を出してデフォルト 60 秒を使用。
- process_priority は権限やプラットフォームにより失敗する可能性があるため、失敗時は警告ログを出して継続します。
- validate_config は PyYAML 未導入時に YAML 検証をスキップして警告を出します。
- Paper Trading 検証レポートは DB のテーブル不足等に対して耐性を持ち、存在しないテーブルがある場合は該当指標を N/A や 0 で扱います。

Acknowledgements
----------------
- 初期実装のため、今後以下の点で拡張・調整予定:
  - factor_research の完全実装（各ファクター計算の SQL 実装）
  - レートリミット・API エラーに対するより詳細な監視メトリクス
  - 単体テストと CI ワークフローの整備
  - 銘柄ごとの lot_size/micro lot 対応や取引コストモデルの精緻化

-----