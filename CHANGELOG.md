# Changelog

すべての変更は Keep a Changelog のフォーマットに従い、セマンティックバージョニングを想定します。

現在のバージョン: 0.1.0 — 初回リリース (2026-04-18)

## [0.1.0] - 2026-04-18

### Added
- プロジェクト初期リリースとして以下の機能群を追加。
  - 実行・監視プロセス
    - run_execution.py
      - ExecutionEngine 起動用のエントリポイント。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（data/paper_trading.db または PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離。
      - ブローカークライアントを BrokerClientFactory から生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで実行。
      - 停止フラグ (data/stop_requested.flag) を監視し、検知時はエンジンを停止して終了。
      - 実行時 PID ファイル (data/execution.pid 等) をサポート。
    - run_monitoring.py
      - SystemMonitor ポーリングループ起動用エントリポイント。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はログ警告のうえデフォルトにフォールバック。
      - 監視起動時はプロセス優先度を "high" に設定。
      - 監視は環境にかかわらず（KABUSYS_ENV に依存せず）本番 sqlite_path（SQLITE_PATH）を使用して監視テーブルを初期化。
      - 停止フラグ (data/stop_requested.flag) 検知でループを終了。
  - 設定管理
    - config.py
      - Settings クラスで環境変数を型安全に取得。
      - .env / .env.local の自動読み込み機能（プロジェクトルートが特定できる場合）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - .env 解析は export 形式、クォート・エスケープ、インラインコメント等に対応する独自パーサを実装。
      - 各種設定プロパティ（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PAPER_FILL_MODE 等）を提供。PAPER_FILL_MODE は "instant"|"partial"|"never"|"reject" のみ許容。
      - KABUSYS_ENV / LOG_LEVEL の妥当性チェックとユーティリティフラグ（is_live / is_paper / is_dev）。
    - config_setup.py
      - 対話式ウィザードで .env を初期作成・更新する CLI。
      - デフォルト値や選択肢の提示、シークレット入力サポート、保存確認・書き出し機能を提供。
  - 設定検証
    - validate_config.py
      - .env と config/*.yaml の起動前チェック CLI。
      - 必須環境変数の存在チェック、KABUSYS_ENV の妥当性、ログレベルチェック、DB パスの親ディレクトリ存在チェック、YAML のパース検査（PyYAML を利用。未インストール時は警告）等を実施。
      - --strict オプションで警告も失敗扱いにできる。
  - ロギング／プロセス制御ユーティリティ
    - utils/logging_setup.py
      - 共通ロギング初期化ユーティリティ。stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/、30日保持）を設定。
      - ログディレクトリ作成失敗時はファイル出力をスキップして標準出力のみで継続。
    - utils/process_priority.py
      - クロスプラットフォームでのプロセス優先度と CPU affinity 設定を提供。
      - Windows / POSIX (Linux, Darwin, FreeBSD) に対応。権限不足や未サポート環境では警告を出してスキップ。
  - ポートフォリオ構築ロジック（純粋関数）
    - portfolio/portfolio_builder.py
      - シグナル選別 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。全てメモリ内純粋関数で副作用なし。
      - calc_score_weights は全スコアが 0 の場合に等金額配分にフォールバックして警告を出す。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中上限（max_sector_pct）を適用して候補を除外するロジック。sell_codes により当日売却予定銘柄をエクスポージャー算出から除外可能。
      - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは 1.0 にフォールバックして警告）。
    - portfolio/position_sizing.py
      - calc_position_sizes:
        - allocation_method: "risk_based" / "equal" / "score" に対応。
        - 単元株（lot_size）丸め、銘柄ごとの上限（max_position_pct）、総投下上限（max_utilization / available_cash）を考慮。
        - コストバッファ (cost_buffer) を使った保守的コスト見積りと、必要時のスケーリング（有効キャッシュに合わせて比率縮小・端数処理）を実装。
  - Paper Trading 検証ツール
    - tools/paper_verification_report.py
      - ペーパートレード SQLite DB（PAPER_TRADING_SQLITE_PATH または --db）を解析して検証レポートを生成。
      - 指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）を算出。
      - デフォルト閾値: 稼働率 99% / 成立率 90% / 送信率 95% / P95 レイテンシ 200ms。基準未達なら FAIL として出力。
      - --from / --to で期間フィルタを指定可能。
  - research/factor_research.py（骨格）
    - DuckDB 接続を受けてモメンタム等のファクターを計算する設計の開始。（ファイル末尾は未完で計算関数群を提供予定）

### Changed
- 初回リリースにつき既存挙動の変更はありません（新規追加中心）。

### Fixed
- 初回リリースにつきバグ修正履歴はありません。

### Notes / Important behavioral details
- 監視 (run_monitoring) は KABUSYS_ENV にかかわらず Settings.sqlite_path（SQLITE_PATH）を使用して監視テーブルを初期化します。開発環境でも監視 DB を明示的に分離したい場合は SQLITE_PATH を設定してください。
- 実行エンジン (run_execution) は is_paper 判定に基づき PAPER_TRADING_SQLITE_PATH を使用し、ペーパートレードと本番データを分離します。
- .env 自動読み込みはプロジェクトルート検出に依存します（.git または pyproject.toml）。自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PAPER_FILL_MODE は許容値が限定されており、誤った値を設定すると起動時に例外が発生します。利用可能値: "instant", "partial", "never", "reject"。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリ作成に失敗するとファイル出力は無効化され、コンソール出力のみになります。
- process_priority の設定は OS 権限に依存し、設定に失敗すると警告を記録して継続します（例: 権限不足で nice が変更できない等）。

### Known limitations / TODO
- portfolio.position_sizing.calc_position_sizes:
  - price が欠損（0 や None）の場合のフォールバック（前日終値や取得原価など）は未実装（TODO コメントあり）。
  - 将来的に銘柄別 lot_size をサポートする拡張を検討（現状は全銘柄共通 lot_size 引数）。
- research.factor_research.py は計算関数の実装途中（ファイル末尾が未完）であり、完全なファクター計算パイプラインは今後追加予定。
- validate_config の YAML 検査は PyYAML に依存。PyYAML 未導入環境では YAML 検査をスキップして警告を出します。

---

変更・既知問題の追跡や次のリリース計画については ISSUE/TRACKER にて議論してください。