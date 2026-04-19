CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。重要な新機能、変更点、バグ修正などを日本語でまとめています。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-19
-------------------

Added
- 基本機能の初期実装（初回リリース）。
  - 実行スクリプト
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。プロセス優先度を "high" に設定して実行。
      - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用に分離した SQLite（data/paper_trading.db, 環境変数: PAPER_TRADING_SQLITE_PATH）に記録する仕組みを導入。
      - 停止フラグ (data/stop_requested.flag) の検出および PID ファイル管理（data/execution.pid）に対応。バックグラウンドスレッドで engine.run_session を実行して安全に停止処理を行う。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - Monitoring は実行環境にかかわらず本番用 sqlite_path を使用して監視テーブルを記録する設計。
  - 設定・環境管理
    - config.py / Settings クラスを追加。
      - .env 自動読み込み（.env → .env.local の順、既存 OS 環境変数は保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
      - .env 行パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（クォート外で空白直前の # をコメントと解釈）に対応。
      - 各種プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE のバリデーション、paper_sqlite_path、PID/KILL フラグ/しきい値など）。
      - 環境種別判定（is_live/is_paper/is_dev）や LOG_LEVEL の妥当性チェックを備える。
    - config_setup.py
      - 対話式ウィザードによる .env の初期作成・更新ツールを追加。シークレット項目はマスク表示、保存前に内容確認が可能。
  - 構成検証
    - validate_config.py
      - 起動前の設定検証 CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードチェックなどを実行。
      - --strict オプションで警告をエラー扱いにできる。
  - ログ・プロセスユーティリティ
    - utils/logging_setup.py
      - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定する共通ユーティリティを追加。
      - LOG_DIR/LOG_LEVEL による設定、既存ハンドラのクリア、ログディレクトリ作成失敗時はコンソール出力にフォールバックする堅牢な実装。
    - utils/process_priority.py
      - psutil を用いたクロスプラットフォーム（Windows / POSIX）プロセス優先度設定と CPU affinity 設定関数を追加。権限不足や未実装環境を想定して警告にフォールバック。
  - ポートフォリオ構築
    - portfolio パッケージ（純粋関数群）を追加。
      - portfolio_builder.py
        - select_candidates（スコア順で候補抽出）、calc_equal_weights、calc_score_weights（全スコア 0 の場合は等分配にフォールバック）を実装。
      - risk_adjustment.py
        - apply_sector_cap（セクター集中による候補除外）、calc_regime_multiplier（market regime に応じた投下資金乗数）を実装。unknown セクター扱い、ログ出力等に対応。
      - position_sizing.py
        - calc_position_sizes を実装。allocation_method に応じた株数算出（risk_based / equal / score）、単元株（lot_size）丸め、per-position と aggregate の上限処理、cost_buffer を用いた保守的見積り、スケールダウンと端数再配分ロジックを備える。
      - package export を __init__ にて整理。
  - 分析・検証ツール
    - tools/paper_verification_report.py
      - Paper Trading の検証レポート生成ツールを追加。稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均、最大、P95）を集計し PASS/FAIL 判定を出力。閾値は定数で定義（例: 稼働率 >= 99% 等）。
    - research/factor_research.py（モジュール骨格）
      - DuckDB を用いたファクター計算モジュールの骨組みを追加（モメンタム / MA200 / ATR / ボラティリティ等の設計と定数）。
  - その他
    - パッケージ基礎: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

Changed
- なし（初期リリースのため）。

Fixed
- なし（初期リリースのため）。ただし実運用を想定した多くのフォールバック（.env 読み込み失敗、ログディレクトリ作成失敗、psutil による権限不足、DB テーブル未存在時のレポート生成例外捕捉など）を実装し堅牢性を向上。

Deprecated
- なし。

Removed
- なし。

Security
- なし（ただし機密情報は .env にて管理する旨を config_setup のヘッダ等で明記）。

Notes / 補足
- run_monitoring/run_execution などの起動スクリプトは stop flag（data/stop_requested.flag）で外部から安全に終了できる設計になっています。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行うため、カレントワーキングディレクトリに依存しません。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading は本番 DB と完全分離する設計（paper_sqlite_path を使用）で、PAPER_FILL_MODE により約定挙動を切り替え可能です（valid values: instant|partial|never|reject）。
- ロギングは標準出力（stdout）へ出力するため、cron や Task Scheduler 等でのリダイレクト運用に適しています。ログファイル出力が失敗した場合でもコンソール出力は維持されます。

README やリリースノートへの反映、また実運用前の環境検証（python -m kabusys.validate_config）を推奨します。