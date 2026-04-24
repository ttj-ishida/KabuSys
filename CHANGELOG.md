# CHANGELOG

すべての注目すべき変更履歴を Keep a Changelog 準拠で記録します。  
フォーマット: https://keepachangelog.com/（日本語訳に準拠）

## [0.1.0] - 2026-04-24
初回リリース — 基本機能を実装しました。

### Added
- 全体
  - パッケージ初期バージョンを追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を基準）し、.env 自動読み込みを行う仕組みを提供（src/kabusys/config.py）。
  - .env の高度なパーサを実装。export 構文、クォート値のエスケープ、コメント処理をサポート（src/kabusys/config.py）。
  - Settings クラスを追加し、環境変数から設定値を安全に取得・検証するプロパティを提供（J-Quants、kabu API、DB パス、監視閾値、実行環境判定など）（src/kabusys/config.py）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動 .env ロード無効化をサポート。

- 実行／監視スクリプト
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と完全分離する動作を実装。
    - BrokerClientFactory 経由でブローカークライアントを作成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）検出による安全停止、PID ファイル管理、デーモンスレッドでの実行制御を実装。
  - SystemMonitor（監視）起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境にかかわらず監視は本番 sqlite_path を使用する仕様。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。無効な値はデフォルトにフォールバック。
    - 停止フラグ検出、例外ハンドリング（check_once 内の例外を捕捉してループ継続）、KeyboardInterrupt の扱いを実装。

- ログ・プロセス関連ユーティリティ
  - 統一的なログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。
    - 既存ハンドラの二重設定防止、ログディレクトリ作成失敗時のフォールバック動作を搭載。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収して nice/priority を設定、psutil による安全なエラーハンドリングを実装。

- 設定関連 CLI
  - 対話式 .env 作成ウィザードを実装（src/kabusys/config_setup.py）。
    - 複数項目定義（実行環境、API トークン、DB パス、LOG_LEVEL、Kill Switch 設定 等）と既存 .env 読み込み・マスク表示を実装。
    - 保存確認と .env 生成機能を提供。
  - 設定検証 CLI を実装（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および PyYAML によるパース検証（PyYAML 未インストール時はスキップ）、本番環境（live）向けの追加警告等を実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純関数群）
  - 候補選定と重み計算を実装（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates: スコア降順＋タイブレーク（signal_rank）で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重（スコアが全て 0 の場合は等分へフォールバック）。
  - セクター集中制限とレジーム乗数を実装（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合、新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた資金乗数（bull/neutral/bear）を提供。未知レジームはフォールバック 1.0。
    - セクター露出計算に関する将来的改善点（価格フォールバック TODO）を注記。
  - ポジションサイジングを実装（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - 損切り率、許容リスク、単元株（lot_size）での丸め、1 銘柄上限（max_position_pct）、投下資金上限（max_utilization）を考慮。
    - aggregate cap 超過時のスケールダウンロジックと残差を考慮した追加配分を実装。
    - 将来的な拡張（銘柄別 lot_size）に関する TODO を注記。

- Paper Trading 検証ツール
  - paper_verification_report を追加（src/kabusys/tools/paper_verification_report.py）。
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から指標を集計しレポート出力（稼働率、注文成功率/送信率、リスク却下数、API レイテンシ（avg/max/P95））。
    - P95 計算ユーティリティ、期間フィルタ（--from/--to）、閾値に基づく PASS/FAIL 判定を実装。
    - データ欠損時のフォールバック処理を実装。

- データ研究モジュール（着手）
  - factor_research モジュール開始（src/kabusys/research/factor_research.py）。
    - モメンタム・ボラティリティ・バリュー等の計算方針と定数を定義。DuckDB 接続を受ける設計。実装は途中（ファイル末尾が切れており継続実装が必要）。

### Changed
- なし（初回リリースのため該当なし）

### Fixed
- なし（初回リリースのため該当なし）

### Known issues / Notes
- factor_research の実装が途中で終了しているため、ファクター計算の完全な実装は未完。
- risk_adjustment.apply_sector_cap では価格が欠損（0.0）の場合に露出が過少評価される旨の TODO があり、将来的な価格フォールバックが必要。
- position_sizing は現状全銘柄共通の lot_size（既定 100）を想定しており、銘柄別単元対応は未実装（TODO）。
- ログディレクトリ作成失敗時はファイル出力が無効化され、コンソール出力のみで継続する設計。運用時はログディレクトリの権限等を確認してください。

### Security
- なし（公開 API トークン等の取り扱いは .env にて秘匿する方針。.env は絶対に Git にコミットしない旨をドキュメントに記載済み）

---

今後の予定（例）
- factor_research の完成および単体テスト追加
- ExecutionEngine / Monitor 周りの統合テスト整備
- 銘柄別 lot_size 対応、価格フォールバックロジック追加
- ドキュメント（README / Operation Guide）拡充

もし CHANGELOG に追加してほしい差分（抜けや強調したい点）があれば教えてください。