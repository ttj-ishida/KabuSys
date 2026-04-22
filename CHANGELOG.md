CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

最新リリース
------------

Unreleased
^^^^^^^^^^

- （現在該当なし）

[0.1.0] - 2026-04-22
-------------------

Added
^^^^^

- 全体
  - KabuSys の初期公開リリース。モジュール構成や各種 CLI・ユーティリティを提供。
  - パッケージバージョンを __version__ = "0.1.0" として設定。

- 起動スクリプト / 実行管理
  - run_execution.py: 実行エンジン起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - エンジンは別スレッドで稼働し、 data/stop_requested.flag による外部停止を監視。
    - 起動時に process priority を "high" に設定（set_process_priority を呼び出し）。

  - run_monitoring.py: システム監視用ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に関係なく本番の sqlite_path を使用して監視テーブルを初期化。
    - stop フラグ（data/stop_requested.flag）を検知して安全にループ終了。
    - check_once() 実行中の例外はログに記録して次ポーリングに継続。

- 設定 / 環境変数
  - config.py: 環境変数読み込み・Settings クラスを実装。
    - プロジェクトルートを .git / pyproject.toml から検出して自動で .env / .env.local を読み込む（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env ローダで export 形式、クォート、インラインコメント、エスケープをサポートする堅牢なパーサを実装。
    - 必須パラメータ取得のための _require、各種パス／フラグ／しきい値等のプロパティを提供（DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、KILL_FLAG_CLEAR_ON_START、CPU/MEM/DISK 閾値等）。

  - config_setup.py: .env 初期作成・更新を対話式に支援するウィザードを追加。
    - J-Quants、kabu API、DB パス、LINE 通知など主要項目を対話的に入力・保存可能。
    - 既存 .env の読み込み、シークレットマスク表示、保存前の確認を実装。

  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数の未設定チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在とパース確認（PyYAML がある場合）。
    - --strict モードで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates(): score 降順、同点は signal_rank 昇順で上位 N 件を選択。
    - calc_equal_weights(), calc_score_weights(): 等金額・スコア加重配分を提供。全スコア 0 の場合は等金額にフォールバックしてログ警告。

  - portfolio.risk_adjustment
    - apply_sector_cap(): 既存保有を基にセクター集中上限（max_sector_pct）をチェックし、上限超過セクターの新規候補を除外。unknown セクターは除外対象外とする。
    - calc_regime_multiplier(): 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（デフォルトで未知レジームは 1.0、未知レジームで警告）。

  - portfolio.position_sizing
    - calc_position_sizes(): allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。
      - risk_based: 許容リスク率・損切り率から株数を算出。
      - equal/score: 重みと max_utilization に基づいて算出。
      - 単元株（lot_size）で丸め、1 銘柄上限（max_position_pct）と aggregate cap（available_cash）を考慮したスケーリング（残差を用いた追加配分ロジックを含む）。
      - cost_buffer による保守的なコスト見積りを反映。

- ユーティリティ
  - utils.logging_setup: StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーへ設定するユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils.process_priority: Windows / POSIX を透過するプロセス優先度設定と CPU affinity 設定を実装。権限不足などで失敗した場合は警告ログを出してスキップ。

- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を run_* スクリプト内で呼び出して監視テーブルの存在を保証（冪等動作）。

- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）などを集計。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を用いて PASS/FAIL を判定。
    - --from/--to/--db オプションに対応。PAPER_TRADING_SQLITE_PATH 環境変数も利用可能。

Changed
^^^^^^^

- なし（初回リリース）

Fixed
^^^^^

- なし（初回リリース）

Deprecated
^^^^^^^^^^

- なし

Removed
^^^^^^^

- なし

Security
^^^^^^^^

- なし

Known issues / Notes
-------------------

- research.factor_research モジュールはファクター計算機能を実装中（モメンタム等の計算ロジックを含む設計あり）。一部実装が途中で切れている箇所があるため、完全な実装は今後のリリースで提供予定。
- position_sizing と risk_adjustment 内にいくつかの TODO が残っています（例: price 欠損時のフォールバック、銘柄別 lot_size サポート）。
- process priority / CPU affinity の設定は権限やプラットフォームに依存し、失敗した場合はログ警告のうえスキップされます。
- .env の自動ロードは OS 環境変数を優先して保護する設計ですが、プロジェクトルートの自動検出に失敗した場合は自動ロードをスキップします。テスト環境で自動ロードを無効にするための KABUSYS_DISABLE_AUTO_ENV_LOAD フラグを提供。

開発者向けメモ
---------------

- 起動スクリプト（run_execution/run_monitoring）は必ず setup_logging() → set_process_priority() の順で呼び出すことでログと優先度設定の初期化を行っています。変更する場合は順序に注意してください。
- validate_config と config_setup を用いることで、運用前に設定の検証と .env の作成をガイドできます。運用環境（KABUSYS_ENV=live）では特に LINE の通知設定や KILL flag の取り扱いに注意してください。

今後の予定（例）
----------------

- research.factor_research の完了とユニットテスト追加
- strategy / execution 周りの E2E テスト整備
- 銘柄別 lot_size や価格フォールバックロジックの導入
- より詳細な監視アラート（LINE 通知等）の追加

-----
この CHANGELOG はコードベースの内容から推測して作成しました。実際のリリースノートとして使う際は必要に応じて調整してください。