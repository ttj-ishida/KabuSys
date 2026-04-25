Changelog
=========
すべての重要な変更をここに記録します。  
このファイルは "Keep a Changelog" の形式に準拠します。

フォーマット:
- 変更はセクション（Added, Changed, Fixed, Deprecated, Removed, Security）に分類しています。
- 日付はリリース日を示します。

Unreleased
----------
（現在なし）

0.1.0 — 2026-04-25
------------------
初回公開リリース。以下の主要機能・ユーティリティを実装しています。

Added
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて v0.1.0 として定義。

- 環境設定管理
  - .env 自動ロード機能を実装（.env, .env.local の順、OS 環境変数を保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - 独自の .env パーサを実装し、シングル/ダブルクォート、エスケープ、export プレフィックス、インラインコメント等に対応（src/kabusys/config.py）。
  - Settings クラスを実装し、各種設定値（J-Quants, kabuAPI, DBパス, Paper Trading 用設定, 監視閾値, 実行環境識別など）をプロパティ経由で取得・検証可能に。

- 設定補助 CLI
  - 対話式環境設定ウィザード（python -m kabusys.config_setup）を実装。.env の初期作成・更新を支援（secret マスキング、選択肢、デフォルト提示、保存確認など）。
  - 設定検証 CLI（python -m kabusys.validate_config）を実装。必須環境変数の有無、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML が有れば）パース検証、本番環境向けガードをチェック。--strict オプションで警告を FAIL 扱いにする。

- 実行エンジン起動スクリプト
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離して使用（data/paper_trading.db をデフォルト）。
    - BrokerClientFactory によるブローカークライアント生成を組み込み（Mock クライアントによる紙運用サポート）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）検知で安全停止。
    - PID ファイルの扱い、監視テーブル初期化（冪等）を実装。
    - RiskManager のデフォルト構成値（max_position_pct, max_utilization, rate_limit_per_sec, circuit breaker 等）を設定例として導入。

- 監視（Monitoring）起動スクリプト
  - SystemMonitor のポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境に関わらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - stop フラグ検知・KeyboardInterrupt でクリーンに終了。check_once() 内の例外はログ出力してループ継続（耐障害性を向上）。

- ロギングユーティリティ
  - 一貫したログ設定ユーティリティを実装（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と 日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR/LOG_LEVEL 環境変数または引数で挙動を制御。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - 既存ハンドラは上書き（重複防止）される仕様。

- プロセス優先度 / CPU 固定ユーティリティ
  - set_process_priority/set_cpu_affinity を実装（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux/macOS 等）差分を吸収。psutil を用いて優先度（high/normal/low）や CPU affinity を設定。権限不足や未対応 OS では警告してスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - 候補選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で上位 N を抽出。タイブレークは signal_rank で。
    - calc_equal_weights / calc_score_weights: 等配分・スコア正規化配分（スコア合計が 0 の場合は等配分にフォールバック）。
  - セクター制限とレジーム係数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター暴露が閾値を超過している場合、新規候補を除外。
    - calc_regime_multiplier: market レジーム ('bull','neutral','bear') に応じた投下資金乗数を返す（未知レジームは警告して 1.0 フォールバック）。
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method（"risk_based"/"equal"/"score"）に対応し、lot_size（単元株）で丸め、個別上限・総投資上限（aggregate cap）を考慮してスケーリングする。cost_buffer を考慮して保守的に見積もるロジックを実装。
    - aggregate スケーリング時に端数処理（lot 単位）を公平に配分するための残差ソートロジックを実装。

- Paper Trading 検証レポートツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）を追加。
    - Paper Trading 用 SQLite DB（PAPER_TRADING_SQLITE_PATH）を読み、システム稼働率・注文成功率・送信率・P95 レイテンシ・リスク却下数を集計して PASS/FAIL 判定を出力。
    - P95 計算ロジック、日付フィルタ、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 ≤ 200ms）を実装。
    - DB 未存在やテーブル欠損時の耐障害的なハンドリング（OperationalError を捕捉して N/A を返す）。

- 研究用ファクター計算（着手）
  - research/factor_research.py を追加（モメンタム・ボラティリティ等の計算ロジック設計を含む）。DuckDB を利用して prices_daily / raw_financials からファクター算出を行う設計。実装は主な定数・関数枠組みを整備（file は未完の箇所あり）。

Changed
- なし（初回リリース）

Fixed
- 環境/実行時の堅牢性向上
  - .env 読み込み時の IO エラーを警告に変換して起動継続可能に。
  - ログディレクトリ作成やファイルハンドラ作成に失敗した場合、コンソールログのみでフォールバックするよう改善。
  - run_monitoring/run_execution で外部例外をキャッチして監視ループ・エンジン処理が停止しないように（監視: check_once 内例外をログに残して継続、実行: stop flag で安全停止）。

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / Known issues / TODO
- position_sizing.calc_position_sizes:
  - price が 0 や欠損のときに現在はスキップする実装。将来的には前日終値や取得原価などをフォールバックする案あり（TODO コメントあり）。
  - lot_size は現状グローバル固定（100）。将来的に銘柄別 lot_map を導入する想定。
- risk_adjustment.calc_regime_multiplier:
  - 未知のレジームは警告して 1.0 でフォールバック。実運用ではレジーム検出部とのインタフェース整備が必要。
- research/factor_research:
  - ファイル末尾で実装が途切れている箇所が存在（実装継続が必要）。
- validate_config:
  - PyYAML 未インストール環境では YAML の内容検証をスキップ（警告）。CI 等で厳密に検証する場合は PyYAML を追加推奨。

Migration
- なし（初回リリース）

その他
- 本リリースは初期実装のため、設定ミスや権限不足による挙動（ログ書き込み失敗、優先度設定失敗など）を想定して多くの箇所で「警告してフォールバック」する設計になっています。運用環境への導入時は .env の設定、ログディレクトリ、psutil の権限（優先度変更の許可）等を事前に確認してください。