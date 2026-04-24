Keep a Changelog
=================

すべての重要な変更点をこのファイルで管理します。これは Keep a Changelog の慣習に沿ったフォーマットです。

フォーマット:
- 変更はカテゴリ別に整理（Added, Changed, Fixed, Removed, Security）
- バージョンは semver 準拠（現状は初期リリース v0.1.0）

Unreleased
----------
（未リリースの変更はここに記載してください）

[0.1.0] - 2026-04-24
-------------------

Added
- 初期リリース: KabuSys — 日本株自動売買システムの基本コンポーネントを追加。
- 環境/設定管理
  - Settings クラスを追加（src/kabusys/config.py）。環境変数から各種設定値を取得するプロパティを提供（KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH など）。
  - .env ファイルの自動読み込み機能を実装（プロジェクトルート検出に .git / pyproject.toml を使用）。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - .env パーサを強化（export プレフィックス対応、クォート内のエスケープ、インラインコメント処理など）。
  - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）を追加。
  - kill/ pid 関連パスや閾値などの設定プロパティを追加。
- 設定関連 CLI
  - 対話式ウィザード（src/kabusys/config_setup.py）を追加。.env の初期作成・更新を支援。生成時に .env をコミットしない旨の注意書きを出力。
  - 設定検証ツール（src/kabusys/validate_config.py）を追加。必須環境変数やパス、config/*.yaml の存在・パース確認、KABUSYS_ENV=live 時の追加警告、--strict モードをサポート。
- 起動スクリプト
  - 監視用起動スクリプト（src/kabusys/run_monitoring.py）を追加。MONITOR_POLL_INTERVAL でポーリング間隔上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。停止フラグ（data/stop_requested.flag）を検知してループを終了。
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（PAPER_TRADING_SQLITE_PATH）を使用することで本番 DB と分離。BrokerClientFactory 経由でブローカークライアントを生成し、ExecutionEngine を別スレッドで実行。停止フラグにより安全停止を実現。
  - 両スクリプトとも起動時にプロセス優先度を "high" に設定する処理を実行。
- ロギング・プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）を追加。stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/、30日保持）をルートロガーに設定。LOG_DIR / LOG_LEVEL の解決ロジックを実装し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度/CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）を追加。psutil を利用し Windows / POSIX (Linux, Darwin, FreeBSD) を吸収。失敗時（権限不足等）は警告を出してスキップ。
- Portfolio（銘柄選定・配分・枚数決定）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）を追加: select_candidates, calc_equal_weights, calc_score_weights を提供。スコアが全て 0 の場合は等配分にフォールバック。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）を追加: セクター集中制限を行う apply_sector_cap と市場レジームに応じた資金乗数を計算する calc_regime_multiplier（未知レジームはフォールバックと警告）。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）を追加: risk_based / equal / score の配分方法を実装。lot_size（単元）丸め、max_position_pct による per-stock 上限、aggregate cap（利用可能現金を超える場合のスケールダウン）と残差処理を実装。手数料・スリッページのための cost_buffer を考慮。
- 分析・検証ツール
  - Paper Trading 検証レポート生成ツール（src/kabusys/tools/paper_verification_report.py）を追加。system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（平均／最大／P95）を集計し PASS/FAIL 判定を行う。閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。
- DuckDB / SQLite 統合
  - DuckDB（分析用）と SQLite（監視・注文履歴用）を双方で利用する設計を全体で採用（起動スクリプト等で接続）。monitoring 用 DB 初期化のための init_monitoring_db 呼び出しを各起動点で行う（冪等）。

Changed
- ログ出力の標準出力先に stdout を採用（cron 等で stdout/stderr を一本化する運用を想定）。
- .env 読み込み順序: OS環境 > .env.local > .env（既存の OS 環境変数は保護）。この挙動を明確化。

Fixed
- MONITOR_POLL_INTERVAL のパースを堅牢化。無効な値や 0 以下の値はデフォルト（60 秒）にフォールバックして警告を出力。
- .env 読み込みでファイルアクセス失敗時に警告を投げるようにし、読み込み失敗を安全にスキップするように修正。

Security
- config_setup に .env を絶対に Git にコミットしない旨を明記（.env に API トークン等のシークレットが含まれるため）。

Notes / Known limitations
- research/factor_research モジュールはファクター計算の基盤実装を含むが、一部未完（ファイル末尾が途中で終わっている）。DuckDB のスキーマ（prices_daily, raw_financials 等）への依存があるため、実運用前にデータ準備が必要。
- paper_trading 用 DB と本番 DB は分離されるよう設計しているが、運用ルール（どの環境でどの DB を使うか）は .env の設定に依存するため注意。
- process priority / CPU affinity の設定は権限やプラットフォーム依存で失敗する可能性がある（その場合は警告を出してスキップする設計）。

作者・貢献
- 初期実装（v0.1.0）

-----