CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠しています。  
リリース日はリポジトリ上の現状を基に推定しています。

フォーマット:
- Unreleased: 今後の変更予定
- 各リリース: 追加 (Added), 変更 (Changed), 修正 (Fixed), 非推奨 (Deprecated), 削除 (Removed), セキュリティ (Security)

Unreleased
----------
- research/factor_research.py が途中まで実装されています（計算ロジックの続き・最適化が必要）。
- 一部に TODO コメントが残っており、将来的な機能拡張（銘柄別 lot_size、価格フォールバック等）を予定しています。

0.1.0 - 2026-04-21
-----------------

Added
- 基本パッケージとバージョン
  - パッケージ初期バージョンを追加: __version__ = "0.1.0"

- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル (data/stop_requested.flag) 検知による終了処理を実装。
    - 監視 DB は実行環境に関わらず本番 sqlite_path を使用する仕様を導入。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite を使用し、本番 DB と完全分離（デフォルト: data/paper_trading.db）。
    - 停止フラグ・PID ファイルの取り扱いを実装し、スレッドでエンジンを実行・安全停止するループを提供。

- 設定管理
  - config.py
    - Settings クラスを導入し、環境変数から各種設定を取得する機能を提供（J-Quants, kabu API, DB パス, 各種閾値など）。
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を読み込む）。
    - 複数の検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を行い、不正値は例外で通知。
    - paper_fill_mode（"instant"|"partial"|"never"|"reject"）等、paper trading 固有設定をサポート。
    - kill_flag 関連の設定：KILL_FLAG_CLEAR_ON_START フラグをサポート。

- 設定支援・検証ツール
  - config_setup.py
    - インタラクティブな .env 作成/更新ウィザードを追加。初期値・シークレット入力・選択肢サポートあり。
    - .env の読み書きロジックを提供し、出力テンプレートと注意事項（.env を Git に入れない等）を明記。
  - validate_config.py
    - 起動前に .env と config/*.yaml の整合性を検証する CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、PyYAML が存在する場合は YAML のパース検査を実施。
    - --strict モードで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順）で選択する関数を追加。
    - calc_equal_weights: 等金額配分を計算する関数を追加。
    - calc_score_weights: スコア加重配分を計算。全スコアが 0 の場合は等金額にフォールバックして WARNING を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター別の既存保有比率が閾値を超えると新規候補を除外するロジックを追加（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を返す関数を追加。未知レジームはフォールバックで 1.0 を返す。
    - Bear レジームに関する注記を含む（実装上、generate_signals が Bear の場合 BUY を出さない旨）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 各種配分方式（risk_based / equal / score）に対応した発注株数算出ロジックを実装。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、投下資金上限（max_utilization）、コストバッファを考慮した aggregate cap スケーリング、残差に基づく追加配分ロジックを実装。
    - 将来的な拡張ポイントとして銘柄別 lot_size のサポートを TODO コメントで明記。

- 監視・発注ログと検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、P95 レイテンシ等を集計して判定（PASS/FAIL）を出力。
    - デフォルト閾値: 稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms。

- ログ・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - setup_logging() を提供。root ロガーを初期化し、StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定する。
    - LOG_DIR / LOG_LEVEL の解決順を用意し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - utils/process_priority.py
    - set_process_priority(level) を実装し、Windows / POSIX の差分を吸収してプロセス優先度を設定。
    - set_cpu_affinity(cpu_count) を実装し、最初の N コアにプロセスを固定する機能を提供。
    - 権限不足や未対応 OS の場合は警告出力してスキップする安全挙動を実装。

- DB 初期化補助
  - monitoring/monitoring_db.init_monitoring_db を run_monitoring/run_execution で呼び出して、監視用テーブルの存在を保証（冪等処理）。

- 依存関係と DB
  - sqlite3 と DuckDB を併用するアーキテクチャを採用（履歴や分析用途で使い分け）。
  - paper_trading 環境では専用 SQLite（data/paper_trading.db）を使用して本番 DB とデータ分離。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Deprecated
- なし

Removed
- なし

Security
- なし（初期リリース）

Notes / Known limitations
- research/factor_research.py はファイル末尾が途中で切れており、モメンタム計算ロジックの続きが未完です（今後の実装課題）。
- position_sizing および risk_adjustment 内に複数の TODO があり、価格フォールバックや銘柄別 lot_size の対応を検討中。
- .env 自動ロードはデフォルトで有効。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化可能。
- paper_trading の MockBrokerClient 実装は別モジュール（BrokerClientFactory）に依存。実際のブローカークライアントとモックの切り替えにより安全に動作する設計になっています。

今後の予定（参考）
- research モジュールの完成（ファクター計算・正規化ユーティリティとの統合）。
- 銘柄別単元株情報の取り込みと position_sizing の拡張。
- モニタリング/検証ダッシュボードの整備（DuckDB を使った分析クエリのライブラリ化）。