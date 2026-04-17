# Changelog

すべての重要な変更をここに記載します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

## [0.1.0] - 2026-04-17

初回リリース（ベース機能の実装）。

### Added
- 基本パッケージ・モジュール
  - kabusys パッケージを追加。バージョン: 0.1.0。
- 実行 / 監視用の起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI ライクなスクリプトを実装。
    - プロセス優先度を起動時に "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は本番 DB と分離して paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用。
    - BrokerClientFactory 経由でブローカークライアントを作成（モック/実ブローカーの切替を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を別スレッド（daemon）で実行。
    - 停止は data/stop_requested.flag によるファイルフラグ検知で行う。実行中は execution.pid を利用。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを実装。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（デフォルト 60 秒）で上書き可能。不正値はデフォルトにフォールバックし警告ログを表示。
    - 監視（monitoring）用 SQLite DB は環境にかかわらず settings.sqlite_path（本番パス）を使用する挙動を明示。
    - 停止は data/stop_requested.flag による検知でループを終了。
- 設定・環境管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
    - .env ファイルのパースは export KEY=val、クォート・エスケープ、インラインコメントなどを考慮した柔軟な実装。
    - Settings クラスを提供し、各種環境変数（J-Quants / kabuAPI / DB パス / 監視閾値 / env 判定 等）を型付きプロパティで取得可能。
    - PAPER_FILL_MODE のバリデーション、有効値: instant/partial/never/reject。
    - KABUSYS_ENV、LOG_LEVEL のバリデーションと is_live/is_paper/is_dev の補助プロパティを提供。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成/更新する CLI を実装。
    - 推奨デフォルト値やシークレットマスク表示、保存の確認などを備える。
  - validate_config.py
    - 起動前に環境変数と config/*.yaml を検証する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の値チェック、DB パス親ディレクトリ存在チェック、YAML パーサ（PyYAML があれば内容検証）、本番環境時の追加ガード（LINE 設定不足、KILL_FLAG_CLEAR_ON_START の危険設定）等を実施。
    - --strict オプションで警告も失敗扱いにできる。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順でタイブレーク）で選別。
    - calc_equal_weights: 等金額配分（1/N）を計算。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等金額配分にフォールバックして警告ログ。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限(max_sector_pct) を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた投下資金乗数を返す（未定義値は 1.0 にフォールバックして警告）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method に応じて銘柄ごとの発注株数を計算（risk_based / equal / score）。
    - 単元株（lot_size）で丸め、1 銘柄上限（max_position_pct）・総投下上限（max_utilization / available_cash）を考慮。
    - コストバッファ(cost_buffer) を考慮し、投資合計が available_cash を超える場合はスケールダウンし、端数は残差順で lot 単位で割当てる再現性のあるアルゴリズムを実装。
- 研究用ファクター計算
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB 経由で計算。
    - calc_volatility (途中まで): ATR、相対 ATR、20日平均売買代金、出来高比などを計算するクエリ実装（DuckDB を利用）。
    - DuckDB を用いて prices_daily / raw_financials テーブルを参照し、メモリ内で計算結果を返す設計。
- ツール
  - tools.paper_verification_report.py
    - Paper Trading 検証レポート生成ツールを実装。
    - 指標: システム稼働率(uptime_pct)、注文成功率(fill_rate)、送信率(send_rate)、P95 レイテンシ等を集計。
    - PASS/FAIL 判定用の閾値を定義（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 latency <= 200ms）。
    - 日付フィルタ対応、--db で DB パス上書き可能。テーブルが存在しない場合は安全に N/A を返す。
- ユーティリティ
  - utils.process_priority
    - set_process_priority(level) を実装。Windows と POSIX（Linux / macOS / FreeBSD）での差分を吸収して優先度を設定、権限不足や未対応 OS は警告でスキップ。
    - set_cpu_affinity(cpu_count) を実装（指定が None の場合は無効化）。権限不足や未対応は警告でスキップ。

### Changed
- （初回リリースのため履歴上の過去変更はなし。今後ここに後続変更を追記します。）

### Fixed
- （初回リリースのため特定のバグ修正履歴はなし。）

### Security
- 環境ファイル (.env) は生成スクリプトが明確に「絶対に Git にコミットしないこと」を出力。シークレット項目はウィザード中にマスク表示。

### Notes / Implementation details / 限界
- .env の自動読み込みはデフォルトで有効。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- run_monitoring は「監視 DB に本番 sqlite_path を常に使用する」設計。監視データを本番と分けたい場合は設定変更が必要。
- position_sizing の lot_size は現状すべての銘柄で共通の仮定（デフォルト 100）。将来的に銘柄別単元対応を想定した拡張コメントを残している。
- research.factor_research の実装は DuckDB に依存。prices_daily / raw_financials のスキーマが前提。
- paper_verification_report は SQLite テーブルが存在しない場合でも例外を回避して N/A を返す耐性を持つ。

今後の予定（例）
- ExecutionEngine / SystemMonitor の単体テスト追加。
- 銘柄別 lot_size や手数料モデルの導入。
- duckdb 接続周りのコネクションプールやパフォーマンス改善。
- monitor のメトリクス拡張・アラート機能（LINE 通知等）の強化。