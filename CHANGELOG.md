# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
日付はリリース日を示します。

## [Unreleased]

## [0.1.0] - 2026-04-21
初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。

### Added
- 全体
  - パッケージ初期版を追加。モジュール構成は config / utils / portfolio / execution / monitoring / research / tools など。
  - パッケージバージョンを `__version__ = "0.1.0"` に設定（src/kabusys/__init__.py）。

- 設定管理
  - 環境変数読み込み・管理モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動ロード（無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート）。
    - .env パース機能はシングル/ダブルクォート・バックスラッシュエスケープ・インラインコメント等に対応。
    - 必須環境変数取得ヘルパー `_require()` および便利なプロパティ群（DB パス、環境種別、Paper Trading 判定、しきい値など）を提供。
  - 対話式 .env 作成ウィザードを追加（src/kabusys/config_setup.py）。
    - 対話形式で主要設定を入力し .env を生成・更新。
    - シークレット項目はマスク表示、保存前の確認プロンプトあり。

- 設定検証 CLI
  - 起動前検証ツールを追加（src/kabusys/validate_config.py）。
    - 必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML が存在する場合）をチェック。
    - `--strict` オプションで警告を失敗として扱う機能。

- ログ・プロセスユーティリティ
  - ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout 出力用 StreamHandler と 日次ローテーション（TimedRotatingFileHandler）を組み合わせた統一的なログ設定。
    - ログディレクトリ作成失敗やファイルハンドラ作成失敗時にフォールバックしてコンソール出力のみで継続。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差を吸収して優先度設定（high/normal/low）および CPU コア固定をサポート。
    - 権限エラー等は警告にフォールバック。

- 実行・監視ランナー
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理をサポート。停止フラグ検知で安全にエンジン停止。
    - 監視テーブル（init_monitoring_db）を起動時に冪等的に初期化。
  - SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバックして警告）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（意図的な設計）。
    - プロセス優先度を高優先（high）に設定してから起動。停止フラグ検知・KeyboardInterrupt に対応。

- Execution / Risk
  - Execution 側の初期リスク設定のデフォルトを実装（src/kabusys/run_execution.py）。
    - max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 関連、max_drawdown などの初期パラメータ。
    - 初期ポートフォリオ値にはブローカーからの get_available_cash() を使用。

- ポートフォリオ構築ライブラリ
  - 候補選定・重み計算を実装（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates: score 降順、同点は signal_rank 昇順で上位 N を選択。
    - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合は等配分へフォールバックして警告）。
  - セクター集中制限・レジーム乗数を実装（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap: 既存保有のセクター別エクスポージャーから過剰セクターを検出して候補をフィルタ（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に対する乗数（未知値は警告して 1.0 をフォールバック）。
  - ポジションサイズ算出を実装（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method = "risk_based" / "equal" / "score" をサポート。
    - lot_size（単元）で丸め、1 銘柄上限・aggregate キャップを考慮してスケーリング、cost_buffer による保守的見積り、残差に基づく追加配分ロジックを実装。

- Paper Trading 検証ツール
  - Paper Trading の検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率（Fill）、送信率（Sent）、P95 レイテンシなどを算出し PASS/FAIL を判定。
    - デフォルトの判定基準（稼働率 >= 99%、Fill >= 90%、送信率 >= 95%、P95 <= 200ms）を定義。
    - 日付フィルタ（--from/--to）や DB パス指定（--db / 環境変数）をサポート。

- 研究用モジュール（骨格）
  - ファクター計算モジュールの骨格を追加（src/kabusys/research/factor_research.py）。
    - モメンタム / MA200 / ATR / 売買代金等の算出方針と定数（窓長等）を明記。DuckDB を用いた計算を想定。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Notes / Important behaviors
- run_monitoring は KABUSYS_ENV にかかわらず "本番の sqlite_path" を使用する設計です。Paper Trading と完全に分離したい場合は run_execution の paper_sqlite_path を利用して運用してください。
- logging_setup は標準エラーではなく標準出力 (stdout) を用いて StreamHandler を作成します。これはジョブスケジューラや cron 等で stdout/stderr を一元管理する運用を想定した設計です。
- process priority / cpu affinity の設定は権限や OS に依存するため、失敗時は警告をログに出して処理を継続します。

---

変更やバグ報告、改善提案は Issue を通じてお寄せください。