# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記載します。ソースコードから推測して作成した最初のリリース記録です。

## [0.1.0] - 2026-04-19

### 追加
- プロジェクト初期実装を追加。
  - パッケージのバージョンを `__version__ = "0.1.0"` として定義。
- 環境設定 / 管理
  - Settings クラスを実装し、環境変数からアプリ設定を取得可能に。
    - J-Quants / kabuステーション / LINE / DB パス / 監視閾値などをプロパティ経由で取得。
    - KABUSYS_ENV の検証（`development` / `paper_trading` / `live`）。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START 等の設定をサポート。
  - 自動 .env 読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - .env 解析の堅牢化:
    - export プレフィックス対応、クォートされた値とエスケープ、インラインコメント処理などに対応。
    - 読み込み時に既存 OS 環境変数を保護する仕組みを実装（override / protected の概念）。
- 設定ユーティリティ / CLI
  - config_setup: 対話式ウィザードで .env の初期作成・更新が可能。
    - 複数の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LOG_LEVEL、Kill Switch の自動クリア設定等）を対話的に入力/保存。
  - validate_config: 起動前に設定不備を検出する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml ファイル存在確認（PyYAML 未インストール時はパーススキップ）など。
    - `--strict` オプションで警告も失敗扱いにできる。
- 実行スクリプト
  - run_execution: ExecutionEngine 起動用スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=`paper_trading` の場合は paper_trading 用の専用 SQLite DB を使用して本番 DB と完全分離（デフォルト: data/paper_trading.db）。
    - BrokerClientFactory を用いたブローカー抽象化、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組み立て。
    - 停止フラグ (data/stop_requested.flag) を監視して安全にシャットダウン。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。無効値は警告を出してデフォルトにフォールバック。
    - 起動時にプロセス優先度を "high" に設定。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（意図的な動作）。
    - 停止フラグ検知、check_once() 内の例外はロギングして次回ポーリングに継続。
- ログ / プロセスユーティリティ
  - logging_setup: 統一的なロギング設定ユーティリティを追加。
    - stdout への StreamHandler（標準出力）と、日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続するフォールバックを実装。
    - ログレベル解決順: 引数 > LOG_LEVEL 環境変数 > "INFO"。
  - process_priority: プラットフォーム差分を吸収してプロセス優先度と CPU affinity を設定するユーティリティを追加。
    - Windows/Linux/macOS に対応（存在しない定数や権限不足は警告出力で安全にスキップ）。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
- ポートフォリオ構築モジュール
  - portfolio_builder:
    - select_candidates: スコア降順・タイブレークに signal_rank を使って上位 N を選出。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（全スコア 0 の場合は等配分にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限を適用（既存ポジション時価を算出し max_sector_pct を超えるセクターの新規候補を除外。unknown セクターは適用対象外）。sell_codes を受け取り当日売却予定銘柄はエクスポージャー計算から除外。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた投下資金乗数を返す（未知のレジームは 1.0 にフォールバックして警告）。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づき発注株数を計算。lot_size（単元株）や cost_buffer（手数料・スリッページ見積り）を考慮した aggregate cap スケーリングを実装。
    - risk_based: 損切り幅・risk_pct に基づく数量算出。価格欠損時のスキップロジックあり。
    - aggregate cap 超過時のスケールダウンと残差処理（lot_size 単位での再配分）を実装。
- 研究 / ファクター計算（部分実装）
  - research/factor_research モジュールを追加（モメンタム / MA200 / ATR / 出来高などを想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。ただしソースは途中（切り出し）であり、今後続きを実装予定。
- ツール
  - tools/paper_verification_report: ペーパートレード結果検証用レポート出力ツールを追加。
    - デフォルト DB パスは PAPER_TRADING_SQLITE_PATH（または data/paper_trading.db）。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標を算出し、閾値に基づく PASS/FAIL 判定を行う。
    - CLI オプション: --from / --to / --db。
    - P95 計算、指標の N/A 処理、SQLite のテーブル欠如に対する耐性を実装。

### 変更
- なし（初回リリースのため該当なし）。

### 修正
- なし（初回リリースのため該当なし）。

### 既知の制限 / 注意事項
- run_monitoring はコード内ドキュメントのとおり「監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用」するため、テスト実行時は注意が必要（本番 DB への書き込みリスク）。
- .env の自動読み込みはプロジェクトルートを検出して行うが、検出できない場合はスキップする（テスト時などに便利な KABUSYS_DISABLE_AUTO_ENV_LOAD を用意）。
- research/factor_research は完全部分実装ではなく、継続開発が必要（ソースが途中で切れている箇所あり）。
- position_sizing の price フォールバックは未実装で、price が 0 や欠損の場合に過小評価される可能性がある旨の TODO コメントあり。
- process_priority / set_cpu_affinity は権限不足や未サポート環境で動作しない場合があり、その際は警告を出してスキップする実装になっている。

### 今後の予定（コード内コメントに基づく）
- position_sizing: 銘柄ごとの lot_size を stocks マスタに持たせるなど、銘柄別設定への拡張。
- factor_research の続き実装（ファクター群の完全実装、DuckDB SQL/計算の完成）。
- 監視・実行の運用向け微調整（ログ・エラー通知・LINE 通知の強化等）。

--- 

この CHANGELOG はコードのコメントや実装内容から推測して作成しています。実際のリリースノート作成時は、コミット履歴や PR 記録に基づいて差分を確認のうえ更新してください。