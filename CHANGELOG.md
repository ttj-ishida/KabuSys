CHANGELOG
=========

すべての変更はコードベースから推測して記載しています。実際のコミット履歴ではなく、提供されたソースコードの実装内容に基づく要約です。

フォーマット: Keep a Changelog 準拠（セクション: Added / Changed / Fixed / Deprecated / Removed / Security）

Unreleased
----------

（無し）

0.1.0 - 2026-04-18
-----------------

Added
- 基本機能の初期実装（初回リリース想定）。
  - 自動売買エンジン起動スクリプト run_execution.py を追加。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - paper_trading モード時は専用 SQLite（data/paper_trading.db）を使用する設計。
    - 実行中の停止制御: data/stop_requested.flag を監視し、安全に停止できる仕組みを実装。
    - 実行時に pid ファイルを書き込む（data/execution.pid 想定）。
  - 監視ポーリング起動スクリプト run_monitoring.py を追加。
    - SystemMonitor を定期的に呼び出すポーリングループを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。
    - 監視用 DB 初期化（init_monitoring_db）と DuckDB 接続を行う。
  - 設定管理モジュール config.py を追加。
    - .env の自動ロード機構（プロジェクトルート検出: .git / pyproject.toml を基準）。
    - 複数の設定プロパティを提供（DB パス、API トークン、環境種別、各種閾値など）。
    - PAPER_FILL_MODE 等の入力値検証を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - 対話式設定ウィザード config_setup.py を追加。
    - .env の初期作成・更新を対話形式で支援する CLI。
    - 既存 .env 読込、値のマスク表示、保存前の確認を実装。
  - 設定検証ツール validate_config.py を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パス存在確認（親ディレクトリ検査）、config/*.yaml の存在およびパース検証（PyYAML がある場合）。
    - --strict オプションで警告も失敗扱いにできる。
  - ロギングユーティリティ utils/logging_setup.py を追加。
    - stdout 出力用 StreamHandler と 日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - ログディレクトリ自動作成、作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度ユーティリティ utils/process_priority.py を追加。
    - Windows / POSIX を吸収して set_process_priority(level) を提供。
    - CPU affinity 設定用 set_cpu_affinity(cpu_count) を実装。
  - ポートフォリオ構築モジュール（kabusys.portfolio）を追加。
    - portfolio_builder: select_candidates、calc_equal_weights、calc_score_weights。
    - risk_adjustment: apply_sector_cap（セクター集中制限）、calc_regime_multiplier（市場レジーム乗数）。
    - position_sizing: calc_position_sizes（等分配 / スコア加重 / リスクベースの株数計算。単元株丸め、aggregate cap スケールダウン、cost_buffer による保守的見積り）。
  - Paper Trading 検証レポート生成ツール tools/paper_verification_report.py を追加。
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から稼働率・注文成功率・送信率・レイテンシ等を集計してレポート出力。
    - P95 計算、閾値判定（稼働率 99% 等）を実装。
  - research/factor_research.py を追加（ファクター計算の骨組み）。
    - モメンタム／ボラティリティ／バリュー等の設計方針と定数を定義。
    - calc_momentum の実装開始（コード断片あり）。※（下記 WIP 参照）

Changed
- 共通設定の読み込み順を明確化: OS 環境変数 > .env.local > .env。既存 OS 環境変数は保護される（上書きされない）。
- run_monitoring/run_execution の起動処理が共通で set_process_priority("high") を呼び出すようにして、重要プロセスとして優先度を上げる設計を採用。
- ログ設定: StreamHandler は stderr ではなく stdout を使用（cron 等で stdout/stderr を一本化しやすくするため）。

Fixed
- MONITOR_POLL_INTERVAL の読み取りで 0 以下や不正な値が指定された場合にデフォルトへフォールバックする安全策を実装（time.sleep に渡すと ValueError となるため）。
- .env パーサの堅牢化:
  - 行頭の "export " を許容。
  - シングル／ダブルクォート内のバックスラッシュエスケープを正しく処理。
  - クォートなしの場合のインラインコメント判定を改善（'#' の直前がスペース/タブのときのみコメントとみなす）。
- position_sizing の aggregate スケールダウン処理で残余キャッシュから lot_size 単位で再配分するロジックを実装（再現性のため順序安定化）。
- run_execution: 起動時に停止フラグが既に存在する場合はエンジンを起動せず終了するガードを追加。

Deprecated
- なし

Removed
- なし

Security
- なし

Known issues / Work In Progress
- research/factor_research.calc_momentum の実装が途中で切れている（ソースが断片的に提供されている）。ファクター計算の完全実装は未完。
- risk_adjustment.apply_sector_cap の価格欠損（price == 0.0）の扱いに TODO コメントあり。現在は過少見積もりとなる恐れがあり、将来的に前日終値や取得原価などのフォールバック価格を検討する旨が記載されている。
- position_sizing の将来拡張: 銘柄別 lot_size を扱う設計への拡張が想定されている（現状は単一 lot_size を使用）。
- 一部のファイルハンドリング / ディレクトリ作成が失敗した場合はフォールバック動作（警告のみ）となるが、その影響範囲は運用での検証が必要。

補足
- この CHANGELOG は提供されたソースコードから機能追加・設計・既知の問題点を推測して作成しています。コミットメッセージや実際のリリースノートがある場合はそちらを優先してください。