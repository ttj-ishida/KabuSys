CHANGELOG.md
=============
※本ファイルは "Keep a Changelog" の形式に準拠しています。  
セマンティックバージョニングに従います。

Unreleased
----------
- 今後の改善予定・既知の TODO:
  - portfolio.position_sizing: 銘柄ごとの単元情報（lot_size）をマスタから読み込む対応
  - portfolio.risk_adjustment: 価格欠損時のフォールバック（前日終値等）の実装
  - research.factor_research: ファクター計算の実装完了（ファイル途中までの実装が含まれています）
  - テストカバレッジの拡充（特に allocation/scaling ロジック・DBマイグレーション）

[0.1.0] - 2026-04-18
-------------------

Added
- 実行スクリプト
  - run_execution.py を追加。ExecutionEngine の起動スクリプトを提供。
    - プロセス優先度を "high" に設定して起動する。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と完全分離する。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の起動を行う。
    - 停止制御は data/stop_requested.flag によるフラグ監視および execution.pid による PID ファイルをサポート。
    - スレッドで engine.run_session をデーモン実行し、フラグ検知時に安全に停止する仕組みを実装。

- 監視（Monitoring）
  - run_monitoring.py を追加。SystemMonitor のポーリングループを起動するスクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値や 0/負値を検知してデフォルトにフォールバックし警告を出す。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視 DB は分離された想定）。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。例外はログに記録して次回ポーリングへ（堅牢化）。

- 設定管理
  - kabusys.config: 環境変数ラッパー Settings を実装。
    - .env/.env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサは export プレフィックス・シングル/ダブルクォート・エスケープ・インラインコメント等に対処する堅牢な実装。
    - 各種プロパティ: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE（妥当性検証）など。
    - env 判定ヘルパー（is_live / is_paper / is_dev）を提供。
    - settings = Settings() のグローバルインスタンスを公開。

- 設定ユーティリティ
  - kabusys.config_setup: 対話式ウィザードで .env の初期作成・更新を支援。
    - シークレット項目は表示時にマスク、既存値の再利用、選択肢の検証、保存前の確認をサポート。
    - デフォルト値や項目説明つきで分かりやすく設定できる。

  - kabusys.validate_config: 起動前の設定検証 CLI を追加。
    - 必須環境変数や KABUSYS_ENV/LOG_LEVEL の妥当性、DuckDB/SQLite のパスの親ディレクトリ存在確認、config/*.yaml の存在・パース（PyYAML が利用可能な場合）などを検査。
    - --strict オプションで警告も FAIL 扱いにできる。終了コードで結果を反映。

- ポートフォリオ構築/資金配分
  - kabusys.portfolio モジュールを追加。
    - portfolio_builder: select_candidates（スコア順選出）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）。
    - risk_adjustment: apply_sector_cap（セクター集中制限で候補除外）、calc_regime_multiplier（market regime に応じた投下資金乗数: bull/neutral/bear）。
    - position_sizing: calc_position_sizes（allocation_method に応じた株数算出）。
      - risk_based / equal / score をサポート。
      - 単元（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash を超える場合のスケーリング）、cost_buffer（手数料・スリッページ見積り）を実装。
      - スケーリング後の残余キャッシュで端数を lot 単位で再配分するロジックを採用。

- ユーティリティ
  - kabusys.utils.logging_setup: 統一ロギング設定関数 setup_logging を追加。
    - コンソール（stdout）への StreamHandler と 日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / 引数での上書き対応、既存ハンドラのクリーンアップ、ファイル作成失敗時のフォールバックを実装。

  - kabusys.utils.process_priority: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX (Linux, macOS 等) の差異を吸収して set_process_priority(level) を提供（high/normal/low）。
    - set_cpu_affinity(cpu_count) により最初の N コアにピンニング可能。権限不足や未対応 OS の場合は警告を出してスキップ。

- ツール
  - kabusys.tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）で DB を指定。期間フィルタ（--from / --to）対応。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）を算出し、閾値に基づき PASS/FAIL を出力。
    - P95 計算、NULL/データ欠損時のハンドリング、閾値定義を実装。

- リサーチ（下地）
  - kabusys.research.factor_research: DuckDB を用いたファクター計算モジュールの骨組みを追加。
    - Momentum / Value / Volatility / Liquidity の仕様・定数が定義され、モメンタム計算関数（calc_momentum）の実装が開始されています（ファイルは途中まで含まれる）。

- パッケージ情報
  - __version__ = "0.1.0" を設定。主要 API の __all__ を定義。

Changed
- （初版のため該当なし）

Fixed
- .env パーサの堅牢化により、引用・エスケープ・コメント処理に起因する設定ミスの回避を改善。

Removed
- （初版のため該当なし）

Security
- セキュリティ上の注意:
  - .env ファイルは生成時に明示的に Git コミットしない旨を README に明記（config_setup の書き出しヘッダに注意書きあり）。
  - 実行スクリプトは本番モード（KABUSYS_ENV=live）での起動前に validate_config で設定を慎重に確認することを推奨。

Notes / Important behaviors
- 監視プロセスは KABUSYS_ENV に関わらず Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。これは監視情報の一貫性確保のための設計です。
- run_execution は paper_trading モード時に paper 用の SQLite を使用するため、本番 DB とは完全に分離されます。
- MONITOR_POLL_INTERVAL に 0 以下や非数値を設定するとログ警告の上でデフォルト（60 秒）にフォールバックします。
- KILL_FLAG_CLEAR_ON_START 環境変数は本番で 1 にするのは推奨されません（validate_config で警告）。
- 一部の箇所に TODO コメント（価格フォールバック、銘柄別 lot_size 導入等）が残っています。次期リリースでの対応を予定しています。

Contributing
- バグや改善提案は issue を作成してください。Pull Request にはユニットテスト（特に position sizing / scaling ロジック・.env パーサ）を同梱してください。

References
- Keep a Changelog: https://keepachangelog.com/ (開発運用時のルール参考)