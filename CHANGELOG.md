CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]



0.1.0 - 2026-04-22
-----------------

Added
- 初回公開リリース。
- 起動スクリプト / ランタイム
  - run_execution.py:
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は専用の Mock ブローカ（BrokerClientFactory を通じて生成）を使用し、Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）と本番 DB を分離。
    - プロセス優先度を起動時に "high" に設定。PID ファイル（data/execution.pid）と停止フラグ（data/stop_requested.flag）による安全停止に対応。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて Engine をデーモンスレッドで実行。
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視 DB は本番 DB を前提）。
    - 停止フラグ検知でループを終了、例外発生時はログに残して次ポーリングに進む安全挙動。
- 設定管理・CLI
  - config.py:
    - Settings クラスを実装し環境変数を型付きプロパティで提供。
    - .env / .env.local の自動ロード機能（OS 環境変数を保護して上書き制御）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env 行パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
    - PAPER_FILL_MODE の検証や KABUSYS_ENV / LOG_LEVEL 等の検証ロジックを組み込み。
  - config_setup.py:
    - 対話式ウィザードで .env の初期作成・更新を支援。既存値の取込、秘密値マスク表示、書き込みテンプレートを提供。
  - validate_config.py:
    - 起動前に .env と config/*.yaml の不備を検出する検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パス（親ディレクトリ存在チェック）、PyYAML があれば YAML のパース検証、KABUSYS_ENV=live 時の追加ガード警告等を実装。
    - --strict オプションで警告を FAIL 扱い（exit non-zero）にできる。
- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio:
    - portfolio_builder.py:
      - select_candidates: スコア降順＋タイブレークで候補選定。
      - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（全スコア 0 の場合のフォールバックで警告）。
    - risk_adjustment.py:
      - apply_sector_cap: 同一セクターの既存エクスポージャを計算し、上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームはフォールバックで 1.0。
    - position_sizing.py:
      - calc_position_sizes: risk_based / equal / score の各割当方式に対応した発注株数決定ロジックを実装。単元株丸め（lot_size）、1 銘柄上限、aggregate cap、手数料・スリッページ見積り（cost_buffer）を考慮したスケーリング、および残余キャッシュを用いた端数配分アルゴリズムを備える。
- ユーティリティ
  - utils/logging_setup.py:
    - 全起動スクリプトで統一利用できるログ設定ユーティリティを追加。
    - コンソール出力は stdout を使用（cron 等でのリダイレクトを想定）、日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を設定し最大30日保持。
    - LOG_LEVEL / LOG_DIR の解決順を定義し、ログディレクトリ作成失敗時はファイル出力をスキップしてフォールバック。
  - utils/process_priority.py:
    - Windows / POSIX の差を吸収するプロセス優先度設定を追加（high/normal/low）。
    - CPU affinity 固定用の set_cpu_affinity を提供。権限不足や未対応環境では警告を出して安全にスキップ。
- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite DB を読み取り、稼働率（uptime）、注文成功率（fill rate）、送信率、リスク却下数、API レイテンシ（avg/max/P95）を算出して検証レポートを出力する CLI を追加。
    - デフォルトの DB パスは PAPER_TRADING_SQLITE_PATH 環境変数、なければ data/paper_trading.db。
    - 各指標に閾値（稼働率 >= 99%、fill_rate >= 90% など）を設定し PASS/FAIL を判定。
- 研究用モジュール
  - research/factor_research.py:
    - Momentum 等の定量ファクター計算モジュールの骨子を追加（DuckDB 接続を受けて prices_daily / raw_financials を参照して計算する設計）。（ファイルは一部実装途中）

Changed
- 初版につき履歴の変更項目はありません（以降のリリースで記録予定）。

Fixed
- 初版につき履歴の修正項目はありません。

Security
- 初版につきセキュリティ関連の変更はありません。ただし .env は絶対に Git にコミットしない旨を README/生成テンプレートで明示。

Notes / 重要な挙動
- 監視プロセス（run_monitoring）は MONITOR_POLL_INTERVAL 環境変数で秒数を指定可能。1 未満や不正値はデフォルト 60 秒にフォールバックして警告。
- run_execution は KABUSYS_ENV=paper_trading 時に paper_sqlite_path を利用して本番 DB と切り離して動作する設計。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行う。プロジェクトルートが特定できない場合は自動ロードをスキップする。
- ログは stdout とファイルの両方に出力されるが、ログディレクトリ作成に失敗した場合はコンソール出力のみで継続する。

Acknowledgements
- 本リリースは初期実装の集約です。各モジュールは拡張・テスト・ドキュメント強化の余地があります。今後のリリースでは API の追加、テストカバレッジ拡充、factor / strategy の詳細実装などを予定しています。