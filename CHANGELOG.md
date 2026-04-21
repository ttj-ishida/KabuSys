CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

0.1.0 — 2026-04-21
------------------

Added
- 初回リリース。主要機能を追加。
  - 実行系・監視
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度を高く設定し、スレッドでエンジンを実行。KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite(DB) を使用して本番 DB と完全分離する仕組みを導入。
      - 停止フラグ file（data/stop_requested.flag）検出による安全停止対応。
      - execution.pid を用いた PID 管理。
      - BrokerClientFactory を使用してブローカークライアントを抽象化。
      - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてエンジンを構成。
      - RiskManager のデフォルトパラメータ（max_position_pct, max_utilization 等）を設定。
    - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60秒）。監視用 DB 初期化処理を実行し、停止フラグによる終了処理を実装。
  - 設定・検証
    - config.py: Settings クラスを導入し、環境変数・.env の管理を統一。
      - 自動 .env ロード機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
      - .env の安全なパース（export 句、クォート／エスケープ、インラインコメントの扱いなどをサポート）。
      - 多数のプロパティを提供（J-Quants / kabuAPI / DB パス / Paper Trading 設定 / 監視閾値 / ログ等）。
      - PAPER_FILL_MODE のバリデーション（instant|partial|never|reject）。
    - config_setup.py: 対話式 .env 作成ウィザードを追加（.env の初期作成・更新支援）。秘密値のマスク表示、デフォルト選択、保存確認を実装。
    - validate_config.py: 設定検証 CLI を追加。必須環境変数や DB パス、config/*.yaml の存在/パース確認（PyYAML が無ければ警告）を行う。--strict モードで警告を FAIL 扱いにできる。
  - ポートフォリオ構築（純関数群）
    - portfolio/portfolio_builder.py: 候補選定（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）を実装。スコアが全て 0 の場合は等配分へフォールバック（警告ログ）。
    - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap と市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装。unknown セクターの扱い、レジーム未定義時のフォールバックを用意。
    - portfolio/position_sizing.py: position sizing 実装（risk_based / equal / score の allocation_method 対応）。単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）によるスケールダウン、cost_buffer（手数料・スリッページ見積り）対応、残差の lot 単位での再配分ロジックを実装。
    - portfolio パッケージの __all__ を整備。
  - ユーティリティ
    - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップするフォールバックを実装。
    - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。Windows/Linux(Mac含む) の差分吸収、権限エラー時の警告フォールバック、set_cpu_affinity による最初 N コア固定を提供。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（P95）等を集計し、PASS/FAIL 判定（閾値はソース内定数で定義）を出力。--from/--to/--db 引数をサポート。
  - 研究用モジュール（下地）
    - research/factor_research.py: ファクター計算モジュール（Momentum 等）を追加。DuckDB 接続を受けて prices_daily / raw_financials からファクターを算出する設計（モジュール途中まで実装）。設計方針や計算窓の定数が定義済み。
  - パッケージ
    - __init__.py: パッケージバージョン __version__ を "0.1.0" に設定。

Changed
- ログ出力の標準出力先を stdout に明示（StreamHandler）。cron 等の運用環境で stderr/stdout を統一して扱えるようにした。

Fixed / Improved
- .env パーサーを堅牢化:
  - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - .env の自動ロードはプロジェクトルートが検出できる場合にのみ行う（配布後の CWD 非依存化）。
- ログ設定: 既存ハンドラがある場合は一旦 flush/close してから再設定し、二重設定を防止。
- run_execution/run_monitoring で起動時にプロセス優先度を最初に設定することで、起動フェーズの重要処理に優先度を反映。
- DB 初期化: monitoring 用テーブルの存在を保証するため init_monitoring_db を起動パスで呼び出し（冪等）。

Security / Notes
- .env ファイルについて: config_setup により .env を生成する際に「.env は絶対に Git にコミットしないこと」をコメントで明記。
- validate_config の live 環境チェックで、LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険な設定を警告。

Known limitations / TODO
- research/factor_research.py は途中で実装が途切れており、完全実装は今後の課題。
- position_sizing の lot_size は現状全銘柄共通。将来的に銘柄別 lot_map を受け取る拡張を検討（TODO コメントあり）。
- apply_sector_cap の価格欠損（price=0.0）の扱いで過少見積りの可能性あり。フォールバック価格（前日終値等）を導入する案がコメントで残っている。
- 一部機能（例: PyYAML による config/*.yaml の詳細バリデーション）は依存パッケージの有無により挙動が変わる（インポートできない場合はスキップ/警告）。

参考: 主要な環境変数（デフォルト値）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL: http://localhost:18080/kabusapi
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO
- MONITOR_POLL_INTERVAL: 60（run_monitoring 用）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

---

今後のリリースでは factor_research の完了、ユニットテストの追加、ドキュメント（API/設計文書）の拡充、並びに CI による静的解析・フォーマットチェック導入を予定しています。