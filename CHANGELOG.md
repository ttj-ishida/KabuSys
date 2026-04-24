# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog のフォーマットに準拠しています。

## [0.1.0] - 2026-04-24

### 追加 (Added)
- 初期リリースとして以下の主要機能を追加。
  - 実行/監視用起動スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV による paper_trading の分離（MockBrokerClient と専用 SQLite: data/paper_trading.db）を実装。実行中は PID ファイル (data/execution.pid) を使用し、data/stop_requested.flag による停止制御を行う。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に依らず本番の sqlite_path を使用し、停止フラグ (data/stop_requested.flag) を検知して終了する。
  - 設定管理
    - config.py: Settings クラスを追加。環境変数の取得ラッパー、env/log_level の検証、paper_trading 用パスや PAPER_FILL_MODE の検証などを実装。プロジェクトルート検出に基づく .env 自動読み込み（.env → .env.local の優先順位）、自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - config_setup.py: 対話式 .env 作成・更新ウィザードを追加（対話入力・既存値継承・.env 書き込み）。
    - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在チェック、KILL / LINE 設定に関する本番向け警告などを行い、--strict オプションで警告を失敗扱いにできる。
    - .env パーサー: export KEY=val, クォート文字列、インラインコメントの扱いなどを考慮した堅牢なパース実装を実装。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - portfolio.portfolio_builder:
      - select_candidates: スコア降順で銘柄選定（同点は signal_rank でタイブレーク）。
      - calc_equal_weights / calc_score_weights: 等分配・スコア加重の重み計算（スコア合計が0のとき等配フォールバック）。
    - portfolio.risk_adjustment:
      - apply_sector_cap: セクター集中制限の適用（売却予定銘柄の除外、unknown セクターは制限適用しない）。
      - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear をサポート、未知レジームは 1.0 でフォールバック）。
    - portfolio.position_sizing:
      - calc_position_sizes: 複数の配分方式（risk_based / equal / score）に対応した発注株数計算。単元株(lot_size)丸め、1銘柄上限・aggregate cap、コストバッファ（手数料/スリッページ見積り）を考慮したスケールダウンロジックを実装。
  - ユーティリティ
    - utils.logging_setup: 統一的なログ設定ユーティリティを追加。stdout 出力（StreamHandler）と日次ローテートファイル出力（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。LOG_DIR / LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - utils.process_priority: Windows / POSIX 間の差を吸収してプロセス優先度を設定するユーティリティを追加。set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足や未対応 OS は警告を出してスキップ。
  - ツール
    - tools.paper_verification_report: Paper Trading の検証レポート生成 CLI を追加。system_status / trade_logs / risk_logs などの SQLite テーブルから稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）を算出し、閾値比較による PASS/FAIL 判定を行う。PAPER_TRADING_SQLITE_PATH 環境変数または --db で DB を指定可能。既定閾値（稼働率 99%、成立率 90% 等）を定義。
  - リサーチモジュール（部分実装）
    - research.factor_research: Momentum 等のファクター計算モジュールを追加（DuckDB 接続を受け取り prices_daily / raw_financials を用いて計算する設計）。モメンタム（1M/3M/6M、MA200 乖離）計算関数の骨組みを整備（一部未完）。

### 変更 (Changed)
- パッケージメタデータ
  - kabusys.__version__ を "0.1.0" に設定（初期バージョン）。
- 実行フローの改善
  - run_execution / run_monitoring の起動時に最初にプロセス優先度を "high" に設定するように統一。
  - run_execution: paper_trading 環境では paper_sqlite_path を使用して本番 DB と分離（安全措置）。

### 修正 (Fixed)
- .env 読み込みの堅牢化
  - .env 読み込みでファイルアクセス失敗時に警告を出し、処理を継続するように変更（テスト環境での扱いを改善）。
  - .env の自動ロードで OS 環境変数を保護する仕組み（protected set）を実装。これにより既存の OS 環境変数を .env によって不意に上書きしない。

### ドキュメント (Documentation)
- 各モジュールに docstring / 使用方法コメントを充実させ、CLI の使い方や設計上の注意点（例: データ不足時の挙動、単元株丸めロジック、レジームの扱い等）を記載。

### 注意事項 / 既知の問題 (Known issues)
- research.factor_research の実装は途中で切れている箇所があり、完全実装が必要（モメンタム計算の SQL/処理続きが未完）。
- 一部の機能（Process priority / CPU affinity / ファイル作成）は権限や環境に依存し、失敗時には警告を出してスキップする設計。運用環境での挙動確認を推奨。
- PAPER_FILL_MODE の値チェックを厳密に行うため、誤った値を設定すると起動時に例外が発生する点に注意。

---- 

今後の予定:
- research.factor_research の完成（ファクター群の算出ロジック実装）。
- ExecutionEngine / Monitoring の統合テストと運用向け安定化（例: 冗長性、再試行ロジックの強化）。
- 銘柄ごとの lot_size マスタ化（position_sizing の拡張）。