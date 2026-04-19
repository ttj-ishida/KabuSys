CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。

リリース日付はソースコードから推測した導入時点（ファイル作成・実装時期）を基に記載しています。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-04-19
-------------------

Added
- 基本アプリケーションと起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite(DB) を使用し、本番 DB と完全に分離して MockBrokerClient を利用する設計。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) による起動/停止制御をサポート。
    - duckdb を分析用 DB として接続、監視用テーブルの存在を保証する init_monitoring_db を呼び出し。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はフォールバック）。
    - 監視モジュールは KABUSYS_ENV に関わらず本番 sqlite_path を使用する（監視は環境分離しない方針）。
    - プロセス優先度の設定、停止フラグ検出、例外ハンドリングを実装。
- 設定管理とツール
  - config.py
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env, .env.local の読み込み順序（OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - 複雑な .env パースを実装（export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメントの扱い）。
    - Settings クラスを導入し、各種環境変数をプロパティ経由で取得（J-Quants、kabu API、DB パス、PID/Kill flag、しきい値等）。
    - PAPER_FILL_MODE の入力検証（有効値: "instant", "partial", "never", "reject"）。
    - 環境 (KABUSYS_ENV) のバリデーション（development/paper_trading/live）およびログレベルの検証。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI。
    - 秘匿項目はマスク表示、デフォルト値や選択肢の提示、保存確認を実装。
    - 書き込み時に .env フォーマットで整形して保存。
  - validate_config.py
    - 起動前に .env と config/*.yaml の基本的な検証を行う CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と PyYAML を利用したパースチェック、live 環境向けの追加警告を実装。
    - --strict オプションで警告も失敗扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定 select_candidates（スコア降順、タイブレークに signal_rank）。
    - 重み計算 calc_equal_weights（等分配）、calc_score_weights（スコア比率、全スコアが 0 の場合は等分配にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存ポジションをセクター別に集計し上限超過セクターの新規候補を除外。unknown セクターは除外対象外）。
    - レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear に対する固定マッピング、未知レジームは警告と 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算 calc_position_sizes（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元株（lot_size）での丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積り、端数の再配分ロジックを実装。
    - 価格欠損時の安全なスキップとログ出力。
- ユーティリティ
  - utils/logging_setup.py
    - 全アプリケーション共通のロギング初期化ユーティリティ setup_logging を提供。
    - stdout への StreamHandler（stdout を使用）と日次ローテートされるファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR 解決（引数 > 環境変数 > デフォルト logs/）・自動作成、作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラのクリーンアップ（重複設定防止）。
  - utils/process_priority.py
    - set_process_priority(level) でクロスプラットフォーム（Windows / POSIX 系）に優先度（nice / Windows priority class）を設定。権限不足や未対応 OS は警告を出して安全にスキップ。
    - set_cpu_affinity(cpu_count) でプロセスの CPU affinity を最初の N コアに固定（未対応・権限不足時は警告）。
- 監視・分析まわり
  - monitoring DB 初期化呼び出し（init_monitoring_db）が起動スクリプトから呼ばれるようになり、監視テーブルの存在を保証（冪等）。
  - duckdb の接続を起動時に確立し分析用 DB を利用可能に。
- CLI / ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - 稼働率、注文成功率（Fill Rate）、送信率（Send Rate）、API レイテンシ（平均/最大/P95）を算出し、しきい値に基づき PASS/FAIL 判定を出力。
    - 日付範囲フィルタ (--from / --to)、DB パス指定 (--db) をサポート。P95 計算、データ不足時の N/A 表示や安全な例外吸収を実装。

Changed
- 初期リリースにつき該当なし（新規追加が中心）

Fixed
- 初期リリースにつき該当なし

Security
- 初期リリースにつき該当なし

Notes / 実装上の注意
- .env パーサはクォート内のエスケープやインラインコメントの取り扱いを独自実装しているため、非常に柔軟だが一部の特殊ケースで微妙な差異が出る可能性あり。
- run_monitoring は監視データに対して常に本番 sqlite_path を使用する設計（環境分離しない）。テスト用途に使う場合は注意。
- process priority / CPU affinity の設定は OS 権限に依存するため、実行環境によっては設定が無視される（警告ログが出力される）。
- portfolio モジュールは純粋関数で設計されており、ユニットテストが容易。ただし価格欠損時のフォールバック（前日終値等）は未実装で TODO コメントあり。
- research/factor_research.py はファクター計算の骨格を備えているが、実装途中の箇所（ソース末尾が未完）あり。今後のリリースで完成予定。

著者
- KabuSys プロジェクト (実装コードから推測して自動生成)

---- 
（この CHANGELOG は与えられたソースコードの内容から推測して作成しています。実際のコミット履歴や変更理由がある場合は適宜差し替えてください。）