CHANGELOG
=========

すべての注目すべき変更点を記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

（現在のコードベースから推測される未リリースの変更はありません）

[0.1.0] - 2026-04-19
-------------------

Added
- 基本パッケージ初回リリース（バージョン 0.1.0）。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御はプロジェクト内 data/stop_requested.flag ファイルで行う。
    - 監視は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する実装。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）へ記録して本番 DB と完全分離。
    - 停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）による制御を実装。
    - スレッドでエンジンを起動し、停止フラグ検知で安全に停止するループを提供。

- 設定関連
  - config.py
    - Settings クラスを提供（環境変数経由の設定管理）。
    - .env / .env.local の自動読み込み機能（プロジェクトルートの検出: .git / pyproject.toml）。
    - クォート付き / エスケープ / コメント対応の .env パーシング（強化されたパーサ実装）。
    - 多数の設定プロパティを提供（J-Quants, kabuステーション, DB パス, PID/KILL フラグ, モニタ閾値, 環境判定 等）。
    - PAPER_FILL_MODE の検証や KABUSYS_ENV / LOG_LEVEL の検証ロジックを組み込み。

  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - 非表示入力（シークレット）、選択肢サポート、既存 .env の読み込みとデフォルト提示。
    - 保存前の確認プロンプト、.env のテンプレート書き出しを実装。

  - validate_config.py
    - 起動前に .env および config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の値チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在/パースチェック（PyYAML がある場合）を実行。
    - --strict モードで警告を失敗として扱う機能。

- ロギング・ユーティリティ
  - utils/logging_setup.py
    - アプリ全体で統一して使える logging 初期化ユーティリティを追加。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app>.log、30日保持）をセット。
    - ログディレクトリ作成失敗時にはファイル出力をスキップしてコンソール出力のみで継続。
    - LOG_LEVEL / LOG_DIR 環境変数または引数からの解決順を定義。

- プロセス制御ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level: "high"|"normal"|"low") を提供（Windows / POSIX に対応）。
    - set_cpu_affinity(cpu_count) でプロセスの CPU affinity を設定（未対応 OS や権限不足時は警告を出してスキップ）。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順選別。
    - calc_equal_weights, calc_score_weights: 等配分 / スコア加重の重み計算（スコア合計が 0 の場合はフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限を適用して候補をフィルタ。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を計算（未知レジームはフォールバックで 1.0）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき発注株数を計算するアルゴリズムを実装。
    - 単元株丸め（lot_size）、max_position_pct、max_utilization、cost_buffer による aggregate cap のスケーリングを実装。

- 監視 / DB 初期化
  - monitoring_db への初期化呼び出し（init_monitoring_db）を起動スクリプトから呼ぶことで監視テーブルの存在を保証（冪等）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を集計し PASS/FAIL 判定を行う。
    - 判定閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。
    - --from / --to / --db オプション対応。デフォルト DB は environment または data/paper_trading.db。

- 研究用モジュール（着手）
  - research/factor_research.py
    - DuckDB を使ったファクター計算の基盤を追加（モメンタム等を計算する関数を実装予定）。calc_momentum 等の実装が開始されている（ファイル末尾は未完）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。機密情報の扱いに関する注意喚起をドキュメント・ウィザードに記載。

Notes / Known issues / TODO
- research/factor_research.py は途中で切れており、いくつかの関数は未完（リリース時点で追加実装が必要）。
- portfolio.position_sizing の注記:
  - price が欠損（0.0）だとエクスポージャーの過少見積りやスキップが発生するため、将来的にはフォールバック価格（前日終値や取得原価）を使う拡張を検討。
  - lot_size を銘柄別に設定できるよう将来拡張予定。
- run_monitoring は監視 DB に常に本番 sqlite_path を使用する設計になっているため、テスト実行時は注意が必要。
- utils/logging_setup はログディレクトリ作成に失敗した際にファイル出力を無効化するが、ファイルハンドラ作成の失敗はワーニングで通知する仕様。
- process_priority の設定は権限不足や一部 OS で失敗する可能性があり、その場合は警告を出してスキップする設計。

開発者向け注記
- .env の書式パースは比較的柔軟（export プレフィックス、引用符、バックスラッシュエスケープ、インラインコメントの扱い）に対応しています。自動読み込みの挙動や優先順位は config.py に実装済みです。
- validate_config CLI は --strict モードにより警告をエラー扱いにできます。CI での事前チェックに利用可能です。

-----  
（以上）