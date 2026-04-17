# Changelog

すべての注目すべき変更点をここに記録します。フォーマットは "Keep a Changelog" に準拠しています。

なお、本ログは与えられたコードベースから推測して作成しています（実際のコミット履歴ではありません）。

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 基本パッケージ初期実装を追加。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。
- 実行／監視のエントリポイントを追加。
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient（分離される専用 SQLite DB に記録）を使用する仕組みをサポート。
    - エンジンはスレッドで実行、停止フラグ検知で安全停止。
    - PID ファイル (data/execution.pid) を扱う。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止フラグ (data/stop_requested.flag) によるループ終了。
    - 監視用 DB 初期化（init_monitoring_db）と DuckDB 接続を行う。
    - 起動時にプロセス優先度を "high" に設定。
- 環境設定・検証・ウィザード用 CLI を追加。
  - config.py
    - .env 自動ロード（プロジェクトルート検出: .git または pyproject.toml）。
    - .env パースの改善（export プレフィックス対応、クォート・エスケープ処理、インラインコメントの扱い）。
    - Settings クラスでアプリ設定値をプロパティとして提供（パス、閾値、KABUSYS_ENV 等）。
    - `paper_fill_mode` のバリデーションを実装（有効値チェック）。
  - validate_config.py
    - .env と config/*.yaml の事前検証ツール（CLI）。
    - --strict モードで警告を失敗扱いにできる。
    - 必須環境変数チェック、パス存在チェック、YAML パースチェック（PyYAML 未インストール時はスキップ）、本番向けガードチェックを実装。
  - config_setup.py
    - 対話式ウィザードで .env を生成/更新するツール。
    - 各設定項目の説明・デフォルト・シークレットマスク表示を備える。
- Paper Trading の検証レポートツールを追加。
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite (`data/paper_trading.db` デフォルト) から各種指標（稼働率、注文成功率、送信率、レイテンシ等）を集計してレポート出力。
    - P95 計算、フィルタ期間指定（--from/--to）、閾値による PASS/FAIL 判定を実装。
- ポートフォリオ構築・リスク調整・ポジションサイズ計算モジュールを追加。
  - portfolio.portfolio_builder
    - 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。スコアが全て 0 の場合はフォールバックで等配分し警告を出す。
  - portfolio.risk_adjustment
    - セクター集中制限 (apply_sector_cap)、レジーム乗数 (calc_regime_multiplier) を実装。unknown セクター扱いの挙動、レジームに対するデフォルトマップを持つ。
  - portfolio.position_sizing
    - ポジションサイズ決定ロジック (calc_position_sizes) を実装。
    - risk_based / equal / score の配分方式対応、単元株（lot_size）丸め、最大ポジション・aggregate cap、コストバッファを考慮したスケーリングと端数処理（remainder に基づく追加割当）を実装。
- ユーティリティ: プロセス優先度と CPU affinity 設定。
  - utils/process_priority.py
    - Windows と POSIX (Linux/Mac/FreeBSD) を吸収する set_process_priority 実装。
    - set_cpu_affinity によるプロセス CPU 固定機能。
    - 権限不足や未対応環境で安全にフォールバックし警告する。

- 研究用ファクター計算モジュール（DuckDB 利用）を追加。
  - research/factor_research.py
    - momentum, volatility など主要ファクターの計算関数を実装（DuckDB SQL による集計）。
    - prices_daily テーブル参照、MA200、ATR、各種リターンや出来高指標を算出。

### 変更 (Changed)
- .env の自動ロード順序・保護動作の仕様明確化。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - OS 環境変数は protected として .env.local の上書き対象外。
  - プロジェクトルートが特定できない場面では自動ロードをスキップする（配布後も安全）。
- 設定値の厳密チェックを追加。
  - Settings.env（KABUSYS_ENV）・LOG_LEVEL・PAPER_FILL_MODE 等で許容値チェックを行い、不正値は ValueError を送出。
- run_monitoring の挙動明確化。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（monitoring 用 DB は環境分離しない設計）。
- run_execution の DB 接続ロジック。
  - paper_trading 環境時は paper_sqlite_path を使用して発注ログ等を本番 DB と分離。

### 修正 (Fixed)
- .env パーサーの強化により、クォート内のバックスラッシュエスケープやコメント処理の不整合を回避。
- process_priority／set_cpu_affinity が権限不足やプラットフォーム差異で例外を投げるのを防ぎ、警告ログでフォールバックするよう修正（安定化）。
- portfolio.position_sizing の集計スケーリング処理で、端数処理による再現性と安全弁（_max_per_stock）を確保するロジックを導入。

### 破壊的変更 (Breaking)
- 監視プロセス（run_monitoring）は「環境に依存せず本番 sqlite_path を使用する」設計になっています。従来想定していた環境分離（development/paper_trading の DB を使う）を期待している場合は注意してください。
- Settings のプロパティで不正な環境変数値を与えると ValueError を送出するため、起動前に .env の内容を validate_config で検証することを推奨します。

### ドキュメント / ヘルプ (Docs)
- 各 CLI スクリプトにヘルプ/usage コメントを追加（config_setup, validate_config, paper_verification_report 等）。
- run_monitoring/run_execution のスクリプト内に挙動や重要な設計注記（停止フラグ、PID、DB 分離、ポーリング間隔）が記載。

---

今後の改善候補（コード中の TODO などから推測）
- position_sizing: 銘柄ごとの lot_size をサポートするための拡張（stocks マスタからの取得）。
- risk_adjustment: price が欠損時のフォールバック（前日終値や取得原価）を導入してエクスポージャー算出精度を改善。
- factor_research: 追加ファクターの実装や欠損データ処理の厳密化、パフォーマンスチューニング。

（以上）