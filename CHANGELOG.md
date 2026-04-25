CHANGELOG
=========

このファイルは「Keep a Changelog」形式に準拠しています。
詳細: https://keepachangelog.com/ja/1.0.0/

すべての変更はセマンティックバージョニングに従います。

Unreleased
----------

(vacant)

0.1.0 - 2026-04-25
------------------

Added
- 基本パッケージの初期実装を追加（バージョン 0.1.0）。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - プロセス優先度を上げる（set_process_priority("high")）。
    - 監視用 DB は環境にかかわらず本番用 sqlite_path を使用する実装。
    - 停止フラグ file data/stop_requested.flag の検知でループ終了。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db 等）を使用し、本番 DB と分離。
    - BrokerClientFactory を介してブローカークライアントを生成（Mock 実装の切り替えを想定）。
    - ExecutionEngine を別スレッドで起動し、停止フラグ検知で安全停止。PID ファイル管理を実施。
- 設定管理
  - config.py
    - .env/.env.local の自動読み込み（プロジェクトルートが判定できる場合）。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
    - .env パーサ実装（export 形式対応、シングル/ダブルクォート・バックスラッシュエスケープ、インラインコメント処理）。
    - Settings クラスで多数の設定をプロパティとして公開（J-Quants、kabu API、DB パス、監視閾値、環境判定等）。
    - PAPER_FILL_MODE の検証ロジック、paper_sqlite_path のプロパティ等を実装。
- 設定ユーティリティ / CLI
  - config_setup.py
    - 対話式ウィザードで .env を作成/更新する CLI。
    - 標準項目（KABUSYS_ENV や API トークン、DB パス、LOG_LEVEL、Kill Switch 動作など）をサポート。
    - 秘密項目はマスク表示、既存 .env を読み込んで再利用可能。
  - validate_config.py
    - 起動前の設定検証 CLI（--strict オプションで警告を FAIL 扱いにできる）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・（PyYAML インストール時は）パース検証、live 環境向けの追加警告を実装。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの統一設定ユーティリティ。
    - StreamHandler（stdout）と日次ローテートの TimedRotatingFileHandler を設定。
    - LOG_DIR / LOG_LEVEL 環境変数を考慮。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py
    - プラットフォーム抽象化されたプロセス優先度設定（Windows と POSIX を吸収）。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。psutil による実装で権限不足時は警告ログでスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのソート（score 降順、同点は signal_rank 昇順）と上位 N 選択。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を防ぐための候補フィルタ（既存ポジションのセクター比率が上限を超えている場合に新規を除外、"unknown" セクターは除外しない）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数（既定値: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバック（警告ログ）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注株数計算。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）に応じたスケールダウン、cost_buffer を考慮した保守的見積り、スケールダウン後の残余配分ロジックを実装。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプト。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）等を出力。
    - P95 計算、期間フィルタ（--from/--to）、--db/環境変数による DB 指定をサポート。
    - 閾値（uptime 99%、fill_rate 90%、send_rate 95%、P95 latency 200 ms）に基づく PASS/FAIL 判定を行う。
- research/factor_research.py
  - ファクター計算の骨組み（モメンタム、ボラティリティ、流動性、バリュー等）を追加。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
- パッケージ初期化
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / 実装上の注意
- .env 自動ロードはプロジェクトルート（.git か pyproject.toml）を探索して行うため、パッケージ配布後の動作で CWD に依存しない設計になっています。プロジェクトルートが特定できない場合は自動ロードをスキップします。
- validate_config の YAML 検証は PyYAML がインストールされている場合にのみ実行されます（未インストール時は警告を出してスキップ）。
- logging_setup は標準出力に stdout を使用します（cron 等で stdout/stderr を一本化している運用を想定）。
- run_monitoring は監視データ保存用に sqlite3、分析用に DuckDB を使用します。run_execution も同様に DuckDB を利用します。
- run_execution は paper_trading モード時に専用の paper_sqlite_path を使用することで本番 DB と完全に分離します。
- process_priority の操作は権限（root/管理者）が必要な場合があり、失敗時は警告ログで処理を継続します。

今後の予定 (提案)
- research/factor_research の完全実装（関数内部実装の続き）。
- 単体テストの追加（特に position_sizing のスケーリングロジック、.env パーサ、config_wizard）。
- CI 実行用の設定・パッケージ配布手順の整備。