# Changelog

すべての notable な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

Added
- 初期リリース。以下の主要機能／モジュールを追加。
  - 環境設定 / ロード
    - 自動 .env ロード機構を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパース機能を強化（`export KEY=val`、シングル/ダブルクォート、エスケープ、インラインコメント取り扱い等に対応）。
    - _require() による必須環境変数チェックと Settings クラスで環境依存値のラップを提供。
    - 環境変数の妥当性チェック:
      - KABUSYS_ENV は `development|paper_trading|live` を許容。
      - LOG_LEVEL は `DEBUG|INFO|WARNING|ERROR|CRITICAL` を許容。
      - PAPER_FILL_MODE の妥当性チェック（`instant|partial|never|reject`）。
    - Settings オブジェクトを `kabusys.config.settings` として利用可能。

  - 設定ウィザード CLI
    - `kabusys.config_setup` に対話式ウィザードを実装。
    - `.env` の初期作成／更新を支援。シークレットは表示マスク。
    - 出力される `.env` に注意書き（絶対に Git にコミットしないこと）。
    - 書き込み前の内容確認と保存の確認プロンプトを実装。

  - 設定検証 CLI
    - `kabusys.validate_config` により .env と config/*.yaml の検証を実行可能。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML のパースチェック（PyYAML が無ければスキップして警告）。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 設定の有無、KILL_FLAG_CLEAR_ON_START の危険性等）。
    - `--strict` オプションで警告も失敗扱いにできる。

  - 実行ランナー / 監視ランナー
    - run_execution: ExecutionEngine 起動スクリプトを追加。
      - プロセス優先度を起動時に "high" に設定。
      - paper_trading 環境では専用のペーパートレード用 SQLite（`PAPER_TRADING_SQLITE_PATH` / data/paper_trading.db）を使用し、本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント生成（paper/live に応じて Mock/実クライアントを生成する想定）。
      - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の起動（バックグラウンドスレッド）。
      - 停止フラグ（data/stop_requested.flag）検出時の安全停止、実行 PID ファイル（data/execution.pid）を利用。
      - RiskManager のデフォルト設定を含む（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, 等）。initial_portfolio_value は broker.get_available_cash() で初期化。
    - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 不正な MONITOR_POLL_INTERVAL 値はログ警告を出しデフォルトにフォールバック（0 以下や非数は無効）。
      - 監視は環境に関わらず本番 sqlite_path を使用して監視 DB を初期化（init_monitoring_db）。
      - stop flag 検出でループを終了。例外はログに出力して次回ポーリングまで待機。
      - 起動時にプロセス優先度を "high" に設定。

  - 監視 DB 初期化
    - init_monitoring_db 呼び出しにより監視用テーブルの冪等な初期化を保証（monitoring 側で利用）。

  - プロセス制御ユーティリティ
    - utils.process_priority:
      - cross-platform にプロセス優先度設定（Windows の priority class / POSIX の nice）。
      - set_process_priority(level) の実装（"high"|"normal"|"low"）。権限不足等は警告でスキップ。
      - set_cpu_affinity(cpu_count) を実装（指定が None の場合は何もしない）。権限不足等は警告でスキップ。

  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder:
      - select_candidates: スコア降順（同点は signal_rank 昇順）で上位 N を選択。
      - calc_equal_weights / calc_score_weights: 等金額配分とスコア比例配分（全スコアが 0 の場合は等金額にフォールバックして警告）。
    - portfolio.risk_adjustment:
      - apply_sector_cap: セクター集中上限チェック（max_sector_pct）に基づく候補除外。unknown セクターは適用除外。
      - calc_regime_multiplier: market regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知は 1.0 にフォールバックして警告）。
    - portfolio.position_sizing:
      - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に応じた発注株数計算。
      - risk_based: risk_pct / stop_loss_pct ベースで目標株数を算出し単元株（lot_size）に丸める。
      - equal/score: weight に応じた配分、per-position 上限・aggregate cap を考慮。
      - aggregate cap 超過時はスケールダウンと lot_size 単位での残差処理（remainder に基づき追加配分）。
      - cost_buffer により保守的にコストを見積もるオプションを提供。
      - lot_size や将来的な銘柄別単元対応に関する TODO コメント。

  - リサーチ / ファクター計算
    - research.factor_research:
      - DuckDB を利用したファクター計算（prices_daily / raw_financials を参照）。
        - Momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）。
        - Volatility: ATR(20)、相対 ATR、20日平均売買代金、出来高比率 等（関数内での window 設定や NULL 扱いを注意）。
      - ターゲット日を指定して (date, code) 単位の dict リストを出力。
      - 大きなスキャンウィンドウ（MA200 用等）に対する buffer を考慮。

  - ツール
    - tools.paper_verification_report:
      - Paper Trading 用検証レポート生成 CLI を追加。
      - CLI オプション: --from / --to（日付範囲）および --db（DB パス）。
      - P95 計算、稼働率 / 注文成功率 / 送信率 / リスク却下数 / レイテンシ（avg/max/P95）を算出して PASS/FAIL 判定を行う。
      - デフォルト閾値:
        - 稼働率 >= 99.0%
        - 注文成功率 >= 90.0%
        - 送信率 >= 95.0%
        - P95 レイテンシ <= 200 ms
      - DB が存在しない場合のエラーメッセージを提供。
      - SQL 実行時にテーブル不存在等で sqlite3.OperationalError が発生した場合は個別に N/A 扱いにフォールバック。

Changed
- （このリリースは初出のため該当なし）

Fixed
- （このリリースは初出のため該当なし）

Removed
- （このリリースは初出のため該当なし）

Notes / 注意事項
- .env ファイルには機密情報（API トークン・パスワード等）が含まれます。リポジトリにコミットしないでください。
- run_monitoring は監視用 DB に対して常に「本番」 sqlite_path を参照する設計です（環境変数 KABUSYS_ENV に依らず）。
- paper_trading における発注・ブローカー挙動は MockBrokerClient を介して完全に分離された DB（data/paper_trading.db）に記録されることを想定しています。
- process priority / CPU affinity 設定は実行環境の権限や OS に依存し、失敗した場合は警告ログを出して処理を継続します。

開発中 / 将来的な改善点（ソース内 TODO）
- position_sizing: 銘柄別の lot_size をサポートする設計への拡張。
- apply_sector_cap: price が欠損（0.0）の場合のフォールバック価格（前日終値等）を導入して過少見積りを防ぐ。
- その他ユニットテスト強化、エラーハンドリングの追加。

-- End of changelog --