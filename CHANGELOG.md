# Changelog

すべての注目する変更点を記録します。本ファイルは「Keep a Changelog」フォーマットに準拠しています。
セマンティックバージョニングを使用します。  

## [Unreleased]
- なし

## [0.1.0] - 2026-04-25
初期リリース。KabuSys のコアユーティリティ、実行/監視スクリプト、ポートフォリオ構築・リスク調整ロジック、設定関連ツール群、および紙トレード検証ツールを実装。

### Added
- 実行系
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV に応じてペーパートレード用の専用 SQLite（data/paper_trading.db）を使用する仕組みを追加（本番 DB と分離）。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて実行エンジンを起動し、別スレッドで run_session を実行。停止フラグ（data/stop_requested.flag）検出時に安全に停止。
    - エンジン PID ファイル管理（data/execution.pid）をサポート。
    - RiskManager の初期設定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。

- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - Monitoring は環境に依らず本番 sqlite_path を使用して監視テーブルを初期化（init_monitoring_db）。
    - duckdb 接続を併用。

- 設定管理
  - config.py: Settings クラスを実装。
    - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）。
    - 環境変数のパースロジックを強化（export プレフィックス、クォート文字列のエスケープ、インラインコメント処理など対応）。
    - 各種設定プロパティ（DB パス、PID ファイルパス、Kill Switch 関連、しきい値、PAPER_FILL_MODE 等）を提供。
    - KABUSYS_ENV/LOG_LEVEL の値検証と判定ユーティリティ（is_live, is_paper, is_dev）。

  - config_setup.py: .env を対話式に作成/更新するウィザード CLI を追加。
    - 複数の設定項目を対話式に入力（シークレット対応、デフォルト/選択肢表示、既存値の再利用）。
    - .env ファイルの書式で出力し、保存を確認するフローを実装。

  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および PyYAML によるパース検証（PyYAML 未インストール時はスキップ）を行う。
    - --strict モードで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア順の銘柄選定ロジックを実装（タイブレーク: signal_rank）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を実装（スコア合計 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター単位の集中制限ロジックを実装。売却予定銘柄を除外可能。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を実装（未知のレジームは 1.0 でフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数決定ロジックを実装。
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer による保守的見積り、残余の端数処理（fractional remainder に基づく追加配分）を実装。

- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - stdout 向け StreamHandler（標準出力）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。
    - LOG_DIR/LOG_LEVEL 環境変数または引数で上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラをクリアして二重設定を防止。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収し、set_process_priority("high"/"normal"/"low")、set_cpu_affinity を提供。
    - 権限不足や未サポート環境では警告を出して安全にスキップ。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py: SQLite（paper_trading DB）から集計して Paper Trading の検証レポートを生成する CLI を追加。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計し PASS/FAIL を判定する閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - 日付フィルタ（--from/--to）と DB パス指定（--db / 環境変数）をサポート。データ欠損時の N/A 表示に対応。

- 研究向けファクター計算（骨格）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨格を追加（モメンタム/ボラティリティ/バリュー等の計算方針、定数、関数枠組みを実装）。関数 calc_momentum の実装開始（ファイル末尾で途中まで記述）。

- パッケージ情報
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。

### Changed
- （初期リリースのため該当なし）

### Fixed
- .env パーサでクォート文字内のエスケープやインラインコメントの扱いを適切に処理することで、複雑な値の読み込みが安定（config.py）。
- ログ設定でログディレクトリ作成に失敗した場合にもアプリが停止しないようフォールバックを実装（logging_setup.py）。

### Security
- 設定ウィザードと .env 取り扱いにおいて、生成された .env を Git にコミットしないようヘッダで注意喚起（config_setup.py）。

### Notes / Known limitations
- research/factor_research.py の一部（calc_momentum の末尾）は未完で、完全なファクター計算ロジックは今後の実装予定。
- position_sizing の lot_size は現状は全銘柄共通の想定。将来的に銘柄毎の単元情報を導入する余地あり（TODO コメントあり）。
- apply_sector_cap で価格が欠損（0.0）の場合にエクスポージャーが過少評価され得る点はコメントで注意喚起している（フォールバック価格の拡張検討）。

---

このCHANGELOG はコードベース（src/ 以下）を解析して推測した初期リリースの内容を記載しています。実際のコミット履歴やリリースノートと差異がある場合があります。必要であればさらに詳細な分割（小さな機能ごとのリリース記録化）や、未完成箇所のチケット化を行います。