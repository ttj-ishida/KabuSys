CHANGELOG
=========

すべての注目すべき変更点を記録します。形式は「Keep a Changelog」に準拠しています。

0.1.0 - 2026-04-23
-----------------

Added
- 起動スクリプトを追加 / 整備
  - run_monitoring.py
    - SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御に data/stop_requested.flag を使用。
    - Monitoring は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する設計。
    - duckdb 接続を併用。
    - プロセス優先度を起動時に "high" に設定。
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを実装。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient（BrokerClientFactory 経由）を使用し、Paper Trading 用 SQLite（デフォルト data/paper_trading.db）で本番 DB と分離。
    - ExecutionEngine の依存コンポーネント（OrderRepository / OrderManager / RiskManager / Reconciler）を組み立ててスレッドで実行。停止フラグ検知で安全に停止。
    - 実行用 PID ファイルの管理（data/execution.pid）。

- 設定管理
  - config.py
    - Settings クラスを導入。環境変数（および .env/.env.local の自動ロード）から各種設定を取得。
    - .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を探索して行う。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パースは export プレフィックス、シングル/ダブルクォート内のエスケープ、行内コメント等に対応する堅牢な実装。
    - 各種プロパティを用意（J-Quants / kabu API / LINE / DuckDB / SQLite / paper_trading / 監視しきい値 / PID / Kill Switch 等）。enum 的な値チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を実施。
  - config_setup.py
    - 対話式ウィザードにより .env の初期作成・更新を支援。シークレットのマスク表示、デフォルト利用、選択肢チェック、最終確認後ファイル出力を行う。

- 設定検証 CLI
  - validate_config.py
    - .env および config/*.yaml の存在と基本整合性をチェックする CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、PyYAML が存在する場合は YAML のパース検証、KABUSYS_ENV=live 時の追加ガード等を実装。
    - --strict オプションで警告を失敗として扱う。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB から統計を集計して検証レポートを出力するスクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを算出し PASS/FAIL 判定を行う。P95 算出ロジックを実装。
    - 日付フィルタ（--from / --to）、DB 指定（--db / 環境変数）に対応。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates, calc_equal_weights, calc_score_weights を実装。スコア順ソート、スコアが全て 0 の場合のフォールバック等。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮し、当日売却対象は除外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を実装。未知の値はフォールバックで 1.0。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の各配分方式に対応した発注株数算出を実装。単元株（lot_size）丸め、1 銘柄上限・aggregate cap、cost_buffer を使った保守的見積りとスケーリングロジックを実装。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに対する一貫した設定ユーティリティを追加。stdout への StreamHandler（標準出力）と、日次ローテーション（TimedRotatingFileHandler、30日保持）のファイルハンドラを設定。ログディレクトリ作成失敗時はファイル出力をスキップして継続。
    - ログレベル・ログディレクトリの解決順を定義（引数 → 環境変数 → デフォルト）。
  - utils/process_priority.py
    - プラットフォーム差を吸収したプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。psutil を利用し、権限不足や未対応 OS は警告でスキップする。

- パッケージ基礎
  - __init__.py にバージョン 0.1.0 を設定し、主要サブパッケージを __all__ に列挙。

Changed
- 監視 DB の取り扱い
  - run_monitoring は KABUSYS_ENV に依らず本番用 sqlite_path を使うという設計決定を明示（監視データは環境に依存せず一元管理）。
- ログ出力
  - ログは stdout をメインに出力するように統一（cron / Task Scheduler 等での取り扱いを容易にするため）。

Fixed
- なし（初期リリース相当の追加が中心）。

Removed
- なし。

Security
- なし（ただし .env は絶対に Git にコミットしない旨を config_setup で明示）。

Known Issues / Notes
- research/factor_research.py はファイル末尾が途中で切れている（実装途中の断片あり）。ファクター計算機能は設計方針と定数が定義されているが、完全実装は今後の作業を要する。
- apply_sector_cap や position_sizing 内に「TODO」コメントがあり、価格データ欠損時のフォールバック（前日終値等）や銘柄別 lot_size 管理の拡張が残っている。
- run_monitoring が本番 DB を直接参照する設計のため、テスト実行時は監視 DB の取り扱いに注意が必要。必要に応じて環境変数やファイルパスを上書きして運用すること。
- process_priority / set_cpu_affinity はプラットフォーム差や権限により効果が出ない場合がある（警告が出るだけで安全にスキップされる）。

Upgrade Notes
- 初回導入時は必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を .env に設定してください。config_setup.py のウィザードが便利です。
- 本番環境での KABUSYS_ENV は "live" を使用してください（validate_config で追加警告が出ます）。Kill Switch や LINE の通知設定についても確認してください。
- ログディレクトリ（デフォルト logs/）に書き込み権限が必要です。権限がない場合は標準出力のみにフォールバックします。

その他
- CLI 実行例:
  - 監視ループ: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

（以上）