# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルでは公開リリースごとの主要な追加・変更・修正点を日本語で記載しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-18

### 追加
- 初期リリースとして以下の主要機能・モジュールを実装・公開。
  - 起動スクリプト / デーモン類
    - run_execution.py — ExecutionEngine 起動スクリプト（スレッドでエンジン実行、停止フラグ監視）。paper_trading 環境では専用の MockBroker + 専用 SQLite DB を使用。
    - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能、停止フラグ検出で終了）。
  - 設定関連 CLI / ユーティリティ
    - config_setup.py — 対話式 .env 作成ウィザード（秘密値のマスク表示・既存値の再利用対応）。
    - validate_config.py — 設定検証 CLI（必須環境変数、パス、YAML の存在・パース確認、--strict モード）。
  - 運用ツール
    - tools/paper_verification_report.py — Paper Trading 用検証レポート生成スクリプト（稼働率、注文成功率、レイテンシ等を集計・判定）。
  - ポートフォリオ構築（純粋関数群、DB 参照なし）
    - portfolio.portfolio_builder: 候補選定（スコア順）・等金額/スコア加重の重み計算。
    - portfolio.risk_adjustment: セクター上限適用、レジームに基づく投下資金乗数。
    - portfolio.position_sizing: 株数計算（risk_based / equal / score）、単元株丸め、aggregate cap のスケーリング処理。
  - 研究モジュール（骨格）
    - research.factor_research: DuckDB によるファクター計算の設計（モメンタム / MA / ATR 等の計算を想定）。
  - 汎用ユーティリティ
    - utils.logging_setup: StreamHandler (stdout) + TimedRotatingFileHandler（デイリーローテート）で一貫したログ設定。ログディレクトリの自動作成失敗に対するフォールバックあり。
    - utils.process_priority: Windows/Linux/macOS を抽象化したプロセス優先度設定と CPU affinity 設定。アクセス権限がない場合は警告を出してスキップ。
  - パッケージ初期化
    - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。

### 変更 / 設計上の注記
- 環境変数の自動ロード
  - プロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を自動読み込み（既存 OS 環境変数を保護）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントなどに対応するよう拡張。
- Settings（設定抽象化）
  - Settings クラスを通じて環境変数へアクセスする統一インターフェースを提供（J-Quants / kabu API / DB パス / 監視閾値など）。
  - paper_trading 用のパス・設定（paper_sqlite_path, paper_fill_mode 等）を明示的に分離。
  - env 値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を追加。
- run_monitoring の動作
  - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化する設計（注: 意図的に本番監視 DB を参照する仕様）。
  - MONITOR_POLL_INTERVAL 環境変数を導入。1 秒未満や不正な値はデフォルト 60 秒にフォールバックして警告を出す実装。
  - 停止は data/stop_requested.flag によるフラグ検出で制御。
  - monitor.check_once() 呼び出し中の例外はキャッチしてログ出力し、次のポーリングまで待機するよう堅牢化。
- run_execution の動作
  - paper_trading 環境では settings.is_paper を用いて専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離。
  - BrokerClientFactory を経由して MockBrokerClient / 実ブローカーを切り替える設計。
  - ExecutionEngine は別スレッドで run_session を実行し、停止フラグで engine.stop() を呼び出す安全な停止手順を実装。
  - 実行時に監視テーブル（init_monitoring_db）を冪等に初期化しておく（監視データ構造が存在することを保証）。
- ロギング
  - setup_logging は stdout を使用する StreamHandler をルートに設定（cron などで stdout/stderr を一本化する運用に配慮）。
  - ログファイルは <log_dir>/<app_name>.log を日次ローテート（30 日保持）で出力。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - 既存ハンドラがある場合は一旦 flush/close してから再設定（多重ハンドラ設定の防止）。
- Paper Trading 検証レポート
  - tools/paper_verification_report.py により、稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計・評価する CLI を追加。閾値はソースコード冒頭で定義（稼働率 >= 99% 等）。
  - P95 はパーセンタイル算出ロジックで実装。データ不足時は N/A で表示。
- ポートフォリオ / ポジションサイズ
  - select_candidates: スコア降順、同点は signal_rank 昇順でタイブレーク。
  - calc_score_weights: 全銘柄のスコアが 0 の場合は等金額配分にフォールバック（警告ログ）。
  - apply_sector_cap: セクター毎の既存エクスポージャーを計算し、上限超過セクターに属する新規候補を除外。unknown セクターは上限適用の対象外。
  - calc_regime_multiplier: "bull"/"neutral"/"bear" に対応（それぞれ 1.0/0.7/0.3）。未知のレジームは警告を出して 1.0 にフォールバック。
  - calc_position_sizes:
    - allocation_method="risk_based" を実装（許容リスク率、stop_loss_pct を考慮して株数を算出）。
    - equal/score 方式でも重みと max_utilization 等を考慮した計算を実装。
    - 単元株（lot_size）での丸め、price 欠損時のスキップ、aggregate cap（available_cash 超過時のスケーリング）と残差処理（fractional remainder に基づく追加配分）を実装。
    - cost_buffer により手数料/スリッページ分を保守的に見積もる挙動を追加。
- process_priority / CPU affinity
  - Windows の優先度クラス定数を安全に参照（getattr を使って存在しない定数に対応）。
  - 未対応 OS や権限不足時は警告を出してスキップする耐障害性を追加。

### 修正（バグ修正相当 / 安全性向上）
- .env 読み込み:
  - .env のクォート・エスケープ・コメント処理を堅牢化。export プレフィックスのサポートを追加。
- run_monitoring:
  - MONITOR_POLL_INTERVAL の不正値（0 や負数、非整数）で time.sleep に渡して例外になるのを防ぐため、バリデーションとフォールバックを実装。
- logging_setup:
  - ログディレクトリ作成失敗時に FileHandler 作成で落ちるケースを防ぎ、コンソールログのみで継続するフォールバックを追加。
- process_priority / set_cpu_affinity:
  - 権限不足や非対応プラットフォームによる例外をキャッチし、ログ出力後に処理を継続するように修正。

### ドキュメント / 使用法の注記
- 主要 CLI / スクリプト
  - .env 作成: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Execution 起動: python -m kabusys.run_execution
  - Monitoring 起動: python -m kabusys.run_monitoring
  - Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 重要な環境変数（抜粋）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
  - KABUSYS_ENV (development | paper_trading | live)
  - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
  - LOG_LEVEL, LOG_DIR
  - MONITOR_POLL_INTERVAL
  - PAPER_FILL_MODE (instant | partial | never | reject)
  - KILL_FLAG_CLEAR_ON_START, KILL_FLAG_PATH
  - KABUSYS_DISABLE_AUTO_ENV_LOAD（自動 .env 読み込みを無効化）

### 既知の制約 / TODO（今後の改善予定）
- portfolio.position_sizing:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積もられる可能性があるため、前日終値や取得原価等のフォールバック価格を将来的に導入する予定（TODO 注釈あり）。
  - 将来的には銘柄別の lot_size（単元）対応のためマスタ参照に拡張予定。
- research.factor_research:
  - モジュール骨格を実装中（コメントに設計方針と定数が含まれる）。完全実装は今後の作業。

---

（注）上記はソースコードの実装内容から推測してまとめた CHANGELOG です。実際のリリース履歴や日付はプロジェクト運用に合わせて調整してください。