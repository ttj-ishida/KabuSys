# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。

## [0.1.0] - 2026-04-19

初回リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定ツール、検証ツール、およびペーパートレード検証レポート生成ツールを含みます。

### 追加
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するメインスクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading 用 SQLite（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と分離して動作。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を実行。
    - 停止フラグファイル（data/stop_requested.flag）を監視し、停止要求を受けるとエンジンを停止・終了。
    - 実行中 PID を記録するための pid ファイル（data/execution.pid）に対応。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path（`SQLITE_PATH`）を使用して動作する設計。
    - 停止フラグ（data/stop_requested.flag）でループを安全に終了。

- 設定管理
  - config.py
    - .env の自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
    - .env の堅牢なパーサを実装（export プレフィックス対応、シングル/ダブルクォート、エスケープ、インラインコメントの扱いを考慮）。
    - OS 環境変数を保護するため、`.env.local` の上書き時に既存 OS 環境変数を保護する機能を実装。
    - Settings クラスを実装し、アプリケーション設定をプロパティ経由で提供:
      - API トークン・パスワード（必須）
      - DB パス（DuckDB / SQLite / Paper Trading 用 SQLite）
      - Paper Trading の fill_mode (`PAPER_FILL_MODE`) 検証（`instant|partial|never|reject`）
      - 監視用パス（pid/kill flag）、KILL_FLAG_CLEAR_ON_START、CPU/Memory/Disk の閾値
      - 環境 (development / paper_trading / live) とログレベルの検証
    - settings 既定インスタンスをエクスポート。

- 設定支援・検証 CLI
  - config_setup.py
    - 対話式ウィザードで .env を新規作成・更新するツールを追加。
    - 必須/任意項目の説明、シークレット入力サポート、既存 .env の読み込みと上書き確認、.env の書き出し機能を提供。
  - validate_config.py
    - 起動前チェック用 CLI を追加。
    - 必須環境変数の存在検査、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および PyYAML があればパース検証、本番環境向けの安全チェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START）を実行。
    - `--strict` オプションにより警告も失敗（exit 1）として扱う。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで共通利用できるログ設定ユーティリティを追加。
    - stdout 出力の StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト: logs/<app_name>.log、30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラをクリアして二重設定を防止。

  - utils/process_priority.py
    - プラットフォームを意識せずプロセス優先度（high/normal/low）を設定する機能を追加（psutil を利用）。
    - POSIX 系（Linux, Darwin, FreeBSD）は nice 値、Windows は HIGH_PRIORITY_CLASS 等を使用。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity() を追加（権限や未対応プラットフォーム時は警告でスキップ）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルから上位 N を選択（スコア降順、同点は signal_rank でブレーク）。
    - calc_equal_weights, calc_score_weights: 等配分・スコア加重配分を提供。スコア合計が 0 の場合は等配分にフォールバックして警告を出す。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限に応じて候補から除外するロジック（売却予定銘柄を除外して既存エクスポージャーを計算）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を返す。未知レジームは 1.0 でフォールバックして警告。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。
    - risk_based: リスク許容率・損切り幅からポジションサイズを算出。
    - Equal/Score: 重みと max_utilization を用いた配分。
    - 単元株（lot_size）丸め、1 銘柄上限・集計上限（available_cash）でスケールダウン、cost_buffer を用いた保守的コスト見積り、スケールダウン後の残差処理（lot 単位での追加配分）をサポート。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から統計を集計し、検証レポートを標準出力に表示するツールを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、リスク却下数、API レイテンシ（avg/max/P95）。
    - P95 算出、空データへの安全処理、期間フィルタ（--from/--to）、閾値による PASS/FAIL 判定を実装。
    - デフォルト閾値:
      - 稼働率: 99.0%
      - 注文成功率: 90.0%
      - 送信率: 95.0%
      - P95 レイテンシ: 200 ms

- 研究用モジュール（骨子）
  - research/factor_research.py
    - DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等の計算を行うためのモジュールの骨子を追加（モジュール設計、定数、calc_momentum のヘッダ等を含む）。（一部実装は継続開発予定）

- パッケージメタ
  - src/kabusys/__init__.py にバージョン文字列 __version__ = "0.1.0" を設定。

### 変更
- -（初回リリースのため変更履歴はありません）

### 修正
- -（初回リリースのため修正履歴はありません）

### 既知の注意点 / マイグレーション
- .env 自動読み込みはプロジェクトルート検出に依存します。配布パッケージ等でプロジェクトルートが検出できない場合は自動ロードがスキップされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で明示無効化可）。
- run_monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（監視用 DB）を使用します。必要に応じて環境変数 SQLITE_PATH を適切に設定してください。
- Paper Trading を行う場合は KABUSYS_ENV=paper_trading を設定し、`PAPER_TRADING_SQLITE_PATH` または Settings.paper_sqlite_path のデフォルト `data/paper_trading.db` を利用してください。
- process_priority / set_cpu_affinity は権限不足や未対応 OS の場合、警告を出してスキップされます（動作の堅牢化のための挙動）。

---

今後の予定（例）
- research/factor_research の完全実装（各ファクター計算ロジックの追加）
- ExecutionEngine / SystemMonitor 周りの詳細なログ・メトリクス拡張
- 単体テスト・統合テストの追加、CLI の入出力改善

もし CHANGELOG に追記してほしい点（特定のファイル変更の強調やリリース日修正等）があれば教えてください。