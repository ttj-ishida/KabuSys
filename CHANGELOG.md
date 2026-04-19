# CHANGELOG

すべての重要な変更はこのファイルに記録します。形式は Keep a Changelog に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース。KabuSys の基本機能群を実装しました（環境設定、起動スクリプト、監視/実行コンポーネント、ポートフォリオ構築ロジック、ユーティリティ、各種 CLI ツールなど）。

### Added
- 基本バージョン情報を追加
  - pakcage version: `kabusys.__version__ = "0.1.0"` を導入。

- 環境設定・読み込み
  - `kabusys.config.Settings` クラスを追加。環境変数経由で設定を取得する統一インターフェースを提供。
  - .env 自動読み込み機構を追加（プロジェクトルートの探索に .git / pyproject.toml を使用）。
  - .env / .env.local の読み込みルール（優先順位: OS 環境 > .env.local > .env）および保護（OS 環境変数を上書きしない）を実装。
  - 環境変数パースの強化: `export` プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント扱いに対応。

- 起動スクリプト
  - `run_execution.py` を追加: ExecutionEngine 起動スクリプト。`KABUSYS_ENV=paper_trading` 時は専用のペーパートレード DB を使用する設計。
  - `run_monitoring.py` を追加: SystemMonitor のポーリングループ起動スクリプト。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。監視 DB は環境にかかわらず本番 sqlite_path を使用するように設計。

- 設定支援ツール
  - `config_setup.py` を追加: 対話式ウィザードで .env を作成・更新する CLI。
  - `validate_config.py` を追加: .env や config/*.yaml の事前検証 CLI。`--strict` オプションをサポート（警告を失敗扱いにする）。

- 監視・レポート
  - `kabusys.tools.paper_verification_report` を追加: ペーパートレード結果の検証レポート生成ツール。稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等を集計し PASS/FAIL を判定する閾値を導入。

- ポートフォリオ構築ロジック（純関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定 `select_candidates`
    - 等分配 `calc_equal_weights`
    - スコア加重 `calc_score_weights`（スコアが全て 0 の場合は等分配へフォールバック）
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限 `apply_sector_cap`
    - レジーム乗数 `calc_regime_multiplier`（bull/neutral/bear をマッピング、未知レジームはフォールバック）
  - `kabusys.portfolio.position_sizing`:
    - ポジションサイズ計算 `calc_position_sizes`（risk_based / equal / score の各方式、単元株丸め、aggregate cap のスケーリングロジック、コストバッファ対応）

- 研究用モジュール
  - `kabusys.research.factor_research` を追加。Momentum / Value / Volatility / Liquidity 等のファクター計算方針を実装するための基盤を追加。DuckDB を利用した prices_daily / raw_financials に対する集計ロジックを想定（モメンタム計算部分を実装中の箇所あり）。

- ロギング・プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加。StreamHandler（stdout）と日次ローテートの FileHandler をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - `kabusys.utils.process_priority` を追加。Windows / POSIX を透過的に扱い、プロセス優先度の設定と CPU affinity 固定機能を提供。権限不足などで失敗した場合は警告ログを出して安全にスキップ。

- 監視 DB 初期化
  - `monitoring.monitoring_db.init_monitoring_db` を呼び出して監視テーブルの冪等な作成を保証（起動スクリプト内で SQLite 接続後に呼出し）。

### Changed
- DB 接続ポリシー
  - 実行エンジン（Execution）は `KABUSYS_ENV=paper_trading` の場合に専用の paper_trading SQLite を使用して本番 DB と分離するように実装。
  - 監視プロセス（Monitoring）は環境にかかわらず本番の sqlite_path を参照する設計とした（運用上の意図を反映）。

- ログ出力先の決定
  - ログのコンソール出力は標準エラーではなく標準出力（stdout）を使用するように設計。cron / Scheduler 等で stdout/stderr を一元化しやすくするため。

- .env の読み込み挙動
  - プロジェクトルート探索を __file__ ベースで行うようにして、カレントワーキングディレクトリに依存しない設計に変更。
  - .env.local は .env よりも後に読み込み（上書き）され、ただし OS 環境変数は保護され上書きされない。

- 実行時のプロセス優先度設定
  - 起動直後にプロセス優先度を "high" に設定するように変更（run_execution / run_monitoring の冒頭）。

- ポートフォリオ計算の安全弁
  - position_sizing のスケールダウンロジック（aggregate cap）では端数配分を lot_size 単位で再配分するアルゴリズムを導入し、再現性のためソート安定化を実施。

### Fixed
- 環境変数パーサーの堅牢性向上
  - export プレフィックス、クォート文字中のバックスラッシュエスケープ、インラインコメントの扱いなどに対応し、誤ったパースによる設定ミスを軽減。

- MONITOR_POLL_INTERVAL の不正値対処
  - ポーリング間隔を環境変数から読み込む際に不正な数値（負数・0・非数）が指定された場合、警告を出してデフォルト（60 秒）へフォールバックするように修正。

- 監視ループの停止制御強化
  - 停止フラグファイル（data/stop_requested.flag）を監視して安全にループを終了する処理を追加。KeyboardInterrupt 発生時も適切に接続をクローズするようにした。

- DB 接続のクリーンアップ
  - 起動スクリプトで finally ブロックにて SQLite / DuckDB 接続を確実に閉じるように修正。

- process_priority / set_cpu_affinity の安全化
  - 権限不足やプラットフォーム差異による例外（AccessDenied, NotImplementedError 等）をキャッチして警告ログとし、起動失敗に繋がらないよう改善。

- logging_setup の耐障害性
  - ログディレクトリの作成失敗時にファイルハンドラ作成をスキップし、標準出力のみでログを継続するように改善。既存ハンドラは再設定前に flush/close して二重出力を防止。

- Paper Trading レポートの堅牢性
  - データ欠損やテーブル未存在時に sqlite3.OperationalError を捕捉してデフォルト値でレポートを生成するようにし、ツールが途中でクラッシュしないように対応。
  - P95 計算の実装と欠損時の N/A 表示を追加。

### Known issues / Notes
- research.factor_research のモメンタム計算関数は実装途中の箇所が存在します（ソースが途中で切れているため、完全な実装は今後追加予定）。実用化の前に追加実装・テストが必要です。
- 一部の TODO コメント（例: position_sizing の銘柄別 lot_size 拡張や price のフォールバックロジック）あり。将来的な拡張を検討しています。
- config_setup による .env 書き込みは平文で保存します。.env の取り扱い（秘密情報の管理）には注意してください（絶対に Git にコミットしないこと）。

---

今後の予定:
- factor_research の完成とユニットテスト追加
- Execution / Monitoring の E2E テスト並びに運用ドキュメント整備
- 各構成要素のログ／メトリクス強化とアラート連携（LINE など）の統合

もし特定ファイルごとの詳細な変更ログ（行単位の差分やリリースノートの英語版）が必要であればお知らせください。