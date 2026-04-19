# Changelog

すべての変更は Keep a Changelog の慣例に準拠して記載しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-19

初期リリース — KabuSys のコア機能を実装しました。主な追加点は以下のとおりです。

### Added
- 基本情報
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として追加。

- 実行用スクリプト / ランタイム
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用に分離された SQLite（デフォルト: data/paper_trading.db）を利用する挙動を実装。
    - BrokerClientFactory / ExecutionEngine / OrderManager / RiskManager / Reconciler 等の組み立て・起動フローを実装。
    - 停止フラグ（data/stop_requested.flag）検出による安全停止、実行 PID ファイル管理、データベース接続のクローズを含む。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する仕様。
    - 停止フラグ検出によるループ終了、例外キャッチとログ出力、DB／DuckDB コネクションのクローズ処理を実装。

- 設定周り
  - config.py
    - Settings クラスを追加し、環境変数や .env ファイルから設定を取得・検証する仕組みを実装。
    - .env 自動読み込み機能を実装（優先順位: OS 環境変数 > .env.local > .env）。自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env のパース周りでシングル／ダブルクォート、エスケープ、`export KEY=val` 形式、インラインコメント処理等に対応。
    - 各種設定プロパティを実装（DB パス、PID/kill フラグパス、しきい値、env/log level 判定、paper trading 関連設定等）。

  - config_setup.py
    - 対話式の .env 作成・更新ウィザードを追加。
    - デフォルト値、選択肢、シークレット入力表示（マスク）など UX を実装。
    - .env の読み書きロジックを実装（既存の .env を尊重して更新）。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在および（PyYAML が入っていれば）パース検証、KABUSYS_ENV=live の追加ガード等を実装。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガー設定ユーティリティを追加。
    - StreamHandler（stdout）および TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定。
    - LOG_DIR / LOG_LEVEL の解決順序を実装し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続するフェイルセーフを備える。

  - utils/process_priority.py
    - プロセス優先度（nice / Windows 優先度）を OS 非依存に設定するユーティリティを追加。
    - CPU affinity 設定関数（set_cpu_affinity）も実装。
    - psutil を利用し、権限不足や未対応環境では警告を出してスキップする挙動。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（score 降順、signal_rank によるタイブレーク）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - 全スコアが 0 の場合は等分配へフォールバックして警告を出す。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター時価を計算して上限を超えるセクターの新規候補を除外する。
    - レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear のマッピング、未知レジームはフォールバックして警告）。

  - portfolio/position_sizing.py
    - 発注株数計算ロジックを実装（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - lot_size（単元）丸め、1 銘柄上限・aggregate cap（available_cash）を考慮したスケーリング、cost_buffer による保守的見積り、残余キャッシュを用いた端数配分アルゴリズム等を実装。
    - 価格欠損時のスキップやデバッグログを備える。

  - portfolio/__init__.py
    - 上記関数を公開するパッケージ API を追加。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 指標: システム稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出し、しきい値（例: uptime >= 99%, fill_rate >= 90% 等）に基づく PASS/FAIL 判定を実装。
    - DB パスの指定は引数 `--db` / 環境変数 `PAPER_TRADING_SQLITE_PATH` / デフォルトの順で解決。

- リサーチ
  - research/factor_research.py
    - ファクター計算モジュールの骨格を追加（モメンタム・MA200・ATR・出来高などを計算する設計）。
    - DuckDB 接続を受けて prices_daily / raw_financials を参照する方針で実装を進めるための定数や関数雛形を実装（モジュールは今後の拡張を想定）。

### Fixed
- .env パーサーの堅牢性
  - クォート内のバックスラッシュエスケープ対応、export プレフィックス対応、インラインコメントの扱いなど、.env パースのエッジケースに対応して安定性を改善。
- ログ設定の堅牢性
  - ログディレクトリ作成失敗時にファイルハンドラ生成をスキップすることで、ディスクアクセス権限による起動失敗を回避。

### Notes / Implementation details
- DB
  - SQLite（監視/発注ログ等） と DuckDB（分析）を併用するアーキテクチャを採用。
  - monitoring の初期化処理（init_monitoring_db）を起動フローに組み込み、監視テーブルの存在を保証（冪等）。

- 実運用向けガード
  - KABUSYS_ENV=live の場合に注意喚起するチェック（LINE 通知設定や Kill Switch の挙動）を validate_config で実装。

- 設定の保護
  - .env 自動ロード時に OS 環境変数を保護（上書き禁止）する挙動を実装。

- エラーハンドリング
  - 長時間実行プロセス（監視ループ / Engine 実行）に対して停止フラグ検出・例外キャッチ・リソースクリーンアップを組み込み、安全停止を重視。

---

注: 本 CHANGELOG は提示されたコードベースの実装内容から推測して作成したものです。内部実装の細部や将来の変更により実際のリリースノートは差分が生じる可能性があります。