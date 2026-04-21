# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
なお内容は提供されたコードベースから推測して記載しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- なし

## [0.1.0] - 2026-04-21
初回リリース。自動売買システム KabuSys のコアユーティリティ、実行/監視ランナー、設定管理、ポートフォリオ構築、検証ツール、研究用ファクタ計算の基礎が実装されています。

### Added
- 全体
  - パッケージ初期バージョンを追加（kabusys.__version__ = "0.1.0"）。
  - DuckDB / SQLite を用いたデータ格納を想定した I/O インターフェースを導入（設定経由でパス指定可能）。
- 実行 / エンジン
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper trading DB を使用して実行（本番 DB と分離）。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 起動・停止のための停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) を利用。
    - RiskManager にデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を導入。
- 監視
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用して monitoring テーブルを初期化。
    - 停止フラグによりループ終了、例外発生時はログ出力して次回ポーリングに継続。
- 設定管理
  - config: 環境変数と .env 自動ロード機能を実装。
    - プロジェクトルート（.git / pyproject.toml）を探索して .env / .env.local を自動読み込み（環境変数で無効化可能: KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - .env パースは export 形式、シングル/ダブルクォート、エスケープ、インラインコメントを考慮。
    - Settings クラスを提供し、各種設定値（J-Quants / kabu API / DB パス / Paper Trading 用設定 / 監視閾値 / 環境名 等）をプロパティ経由で取得。
    - 入力検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値、PAPER_FILL_MODE の許容値など）を含む。
  - config_setup: 対話式ウィザードで .env の初期作成・更新を行う CLI を追加。
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等の必須項目に対応。シークレットはマスク表示。
    - 生成/更新された .env の保存をサポート。
  - validate_config: 起動前設定検証 CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検証（PyYAML 有無で挙動分岐）を実装。
    - --strict フラグで警告を失敗扱いにできる。
- ロギング / プロセス管理
  - utils.logging_setup: 統一的なロギング設定ユーティリティを追加。
    - コンソール出力は stdout、ファイル出力は TimedRotatingFileHandler による日次ローテーション（デフォルト logs/<app_name>.log、30 日保持）。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしコンソールのみで継続。
    - 既存ハンドラをクリアして二重設定を防止。
  - utils.process_priority: プロセス優先度（Windows / POSIX を吸収）と CPU affinity 設定ユーティリティを追加。
    - psutil ベースで Windows の優先度クラス、POSIX の nice 値を設定。設定に失敗しても警告ログでスキップ。
    - set_cpu_affinity により先頭 N コアへの固定を可能にする（実装は安全弁付き）。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順）でソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装。スコア合計が 0 の場合は等配分へフォールバック。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック。既存保有を考慮して特定セクターの新規候補を除外可能（unknown セクターは制限除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を提供（未知レジームは警告の上 1.0 でフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method に応じた発注株数計算を実装（risk_based / equal / score）。
    - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap スケーリングを実装。端数は lot_size 単位で再配分。
- ツール
  - tools.paper_verification_report: ペーパートレード用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計。
    - 判定閾値を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）し PASS/FAIL を出力。
    - --from/--to/--db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数に対応。
- 研究モジュール（基礎）
  - research.factor_research: ファクター計算モジュールの骨組みを追加（モメンタム／MA200乖離／ATR 等の定義、calc_momentum の初期実装開始）。DuckDB から prices_daily を参照して計算する方針。

### Changed
- （初回リリースのため該当なし）

### Fixed
- MONITOR_POLL_INTERVAL のパースで不正値（0 / 負数 / 非整数）を検知した場合、警告ログを出してデフォルト（60 秒）にフォールバックするように保護を追加。
- ログ設定・プロセス優先度設定などで環境依存のエラー（ディレクトリ作成失敗や権限不足）が発生した場合、例外で停止させず警告ログでスキップする堅牢性を導入。

### Security
- .env ファイルに含まれるシークレット値（J-Quants トークン、kabu API パスワード等）は config_setup の表示でマスクされ、.env を Git にコミットしないよう README/生成ヘッダで注意喚起。

### Notes / Important behavior
- 自動ロード: 起動時にプロジェクトルートが検出できれば .env/.env.local を自動で読み込みます。テスト等でこれを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading の DB 分離: KABUSYS_ENV=paper_trading の場合、Execution は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用して本番データと分離されます。
- 監視ループは停止フラグ（data/stop_requested.flag）と KeyboardInterrupt を検知して安全に終了します。monitoring は環境にかかわらず設定された sqlite_path（デフォルト data/monitoring.db）を使用します。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。

---

今後の改善候補（推測）
- position_sizing: 銘柄毎の lot_size をマスタから取得する拡張。
- risk_adjustment: price 欠損時のフォールバック価格（前日終値等）を利用する改善。
- research.factor_research: ファクター実装の完成および統合テストの追加。
- CI / テスト: 設定読み込み・CLI の自動テスト整備。

もし特定の変更点（例: あるファイルの差分のみ）にフォーカスした Changelog を希望される場合、対象範囲を教えてください。