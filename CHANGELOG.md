CHANGELOG
=========

すべての notable な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠します。
リリースは semantic versioning に従います。

Unreleased
----------

（現在の作業ブランチに未リリースの変更はありません）

0.1.0 - 2026-04-22
-----------------

Added
- 初回リリース。日本株自動売買システム「KabuSys」のコア機能群を追加。
  - パッケージ基本情報
    - パッケージバージョンを `__version__ = "0.1.0"` として追加。
  - 設定管理
    - 環境変数・設定読み込みモジュール (kabusys.config)
      - プロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動読み込み（OS 環境変数を優先）。
      - .env パースはクォートやエクスポート形式、インラインコメントなどを考慮して安全に処理。
      - Settings クラスで各種設定（J-Quants、kabu API、DB パス、Paper Trading 設定、監視閾値、環境種別など）をプロパティで取得。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - 設定ユーティリティ / CLI
    - 環境設定ウィザード (kabusys.config_setup)
      - 対話式で .env の作成・更新を支援。秘密値のマスク表示、選択肢・デフォルトのサポート。
    - 設定検証ツール (kabusys.validate_config)
      - 必須環境変数の存在確認、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース検証（PyYAML が存在する場合）などを実行。--strict オプションで警告もエラー化可能。
  - 実行・監視プロセス起動スクリプト
    - 実行エンジン起動スクリプト (kabusys.run_execution)
      - 環境に応じて paper_trading 用 DB を分離して使用（PAPER_TRADING_SQLITE_PATH / settings.is_paper）。
      - BrokerClientFactory を用いてブローカークライアントを生成。OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine を起動。
      - 停止フラグ（data/stop_requested.flag）や execution.pid を扱う仕組みを実装。スレッドで engine.run_session を実行し、停止フラグ検知で Engine.stop() を呼び出す。
    - 監視ループ起動スクリプト (kabusys.run_monitoring)
      - SystemMonitor を初期化しポーリングループで monitor.check_once() を定期実行。
      - MONITOR_POLL_INTERVAL 環境変数 (秒) によるポーリング間隔上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
      - 監視は環境にかかわらず本番 sqlite_path を使用する（モニタリング用 DB の統一）。
  - 監視 DB 初期化（監視テーブルの冪等な初期化呼び出しを実装）
    - init_monitoring_db を起動スクリプトで呼び出し、監視テーブル存在を保証。
  - ツール
    - Paper Trading 検証レポート生成スクリプト (kabusys.tools.paper_verification_report)
      - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均 / 最大 / P95）等を集計してレポート出力。
      - P95 計算、期間フィルタ、閾値による PASS/FAIL 判定（デフォルト閾値: 稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。
  - ポートフォリオ構築モジュール (kabusys.portfolio)
    - portfolio_builder
      - select_candidates: BUY シグナルのスコア降順で上位 N を選択（タイブレークは signal_rank）。
      - calc_equal_weights / calc_score_weights: 等分配およびスコア加重（スコア合計が 0 の場合は等分配へフォールバック）。
    - risk_adjustment
      - apply_sector_cap: セクター集中の既存保有比率を評価し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームはフォールバック 1.0）。
    - position_sizing
      - calc_position_sizes: risk_based / equal / score の各配分法に対応し、lot_size（単元）で丸め、per-stock 上限と aggregate キャップ、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリングを行う。空価格や価格不足の銘柄はスキップ。
  - 研究モジュール（骨組み）
    - research.factor_research: DuckDB を用いてモメンタム等のファクター計算を行う骨組みを追加（モジュール内に定数・関数雛形を用意）。※ 一部実装が続く（ファイル末尾で未完）。
  - ユーティリティ
    - ロギング設定ユーティリティ (kabusys.utils.logging_setup)
      - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。LOG_DIR / LOG_LEVEL の環境変数を尊重。既存ハンドラをクリアして二重設定を防止。
    - プロセス優先度 / CPU affinity 設定ユーティリティ (kabusys.utils.process_priority)
      - Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収してプロセス優先度（high/normal/low）を設定。set_cpu_affinity により最初の N コアに固定する機能を提供。権限不足等は警告でスキップ。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Notes / 重要な挙動
- .env の自動ロードはデフォルトで有効。テスト等で無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 監視 (run_monitoring) は KABUSYS_ENV にかかわらず監視用 sqlite_path（デフォルト data/monitoring.db）を使用します。実行エンジンは paper_trading 環境時に専用 DB（data/paper_trading.db）を使用して本番 DB と分離します。
- プロセス優先度や CPU affinity の設定は実行環境の権限に依存します。権限不足時は警告ログが出力され、処理は継続されます。
- research.factor_research 内の一部実装は未完の箇所があるため、利用時は実装の完成度を確認してください。

今後の予定
- research.factor_research の完全実装（ファクター計算ロジックの完成）。
- ExecutionEngine / Broker クライアント周りのユニットテスト強化。
- バックテスト・シミュレーションツールの追加と分析機能拡張。

ライセンスや貢献方法などのメタ情報は別途 README.md に記載してください。