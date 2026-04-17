# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-17

### Added
- 基本アプリケーション構成を実装（初期リリース）。
  - パッケージ情報:
    - バージョン: 0.1.0（src/kabusys/__init__.py）
- 環境変数／設定管理（src/kabusys/config.py）
  - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先順: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプション。
  - .env パーサの強化:
    - export KEY=val 形式に対応。
    - シングル／ダブルクォートの中でのバックスラッシュエスケープを正しく処理。
    - インラインコメント処理（クォートなしの場合は '#' の直前がスペース・タブならコメントと認識）。
  - 必須環境変数チェック用ユーティリティ（_require）。
  - 多数の設定プロパティを提供（J-Quants, kabuステーション, LINE, DB パス, 監視閾値 等）。
  - PAPER_FILL_MODE のバリデーション（有効値: "instant", "partial", "never", "reject"）。
  - DB パスや PID/kill flag 等のパス取得ユーティリティ。

- 設定ウィザード CLI（src/kabusys/config_setup.py）
  - 対話式ウィザードで .env を初期作成・更新。
  - 秘匿項目は表示マスク（****）で扱う。
  - デフォルト値・選択肢サポート、確認プロンプト、.env の書き出しロジックを提供。

- 設定検証 CLI（src/kabusys/validate_config.py）
  - 起動前に環境変数や config/*.yaml の存在・基本妥当性を検証するツール。
  - 必須環境変数のチェック、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML がインストールされている場合）を実施。
  - KABUSYS_ENV=live 向けの追加警告（LINE 通知設定確認や KILL_FLAG_CLEAR_ON_START 警告）。
  - --strict オプションで警告を FAIL 扱いにする機能。

- 実行用エントリスクリプト（src/kabusys/run_execution.py）
  - ExecutionEngine を起動するエントリポイントを実装。
  - 環境に応じた DB 分離:
    - paper_trading 環境では PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離。
  - BrokerClientFactory によるブローカークライアントの生成（paper_trading 時は MockBrokerClient 想定）。
  - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立て。
  - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、初期ポートフォリオ値をブローカーから取得。
  - エンジンは別スレッドで run_session を実行。停止フラグ (data/stop_requested.flag) を検知して安全に停止。

- 監視用エントリスクリプト（src/kabusys/run_monitoring.py）
  - SystemMonitor のポーリングループを実装。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
  - 監視データベースは環境にかかわらず本番 sqlite_path を使用（監視は常に本番 DB に記録）。
  - Process 優先度設定（起動時に high を指定）と停止フラグ検出、例外を捕捉してループ継続。

- モニタリング DB 初期化フック（init_monitoring_db の呼び出し）を両スクリプトで行い、テーブル存在を保証（冪等）。

- ユーティリティ: プロセス優先度・CPU affinity（src/kabusys/utils/process_priority.py）
  - cross-platform 実装（Windows / POSIX 系を吸収）。
  - set_process_priority(level) — "high" / "normal" / "low" をサポート。権限不足時は警告を出してスキップ。
  - set_cpu_affinity(cpu_count) — 最初の N コアに固定する機能。未対応 OS / 権限不足は警告。

- ポートフォリオ構築モジュール（src/kabusys/portfolio/*）
  - portfolio_builder:
    - select_candidates: score 降順＋signal_rank をタイブレークにして候補選定。
    - calc_equal_weights, calc_score_weights（score が全て 0 の場合は等分配にフォールバックして警告）。
  - risk_adjustment:
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは除外対象としない）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear のマップ、未知レジームは警告して 1.0 にフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method に応じて発注株数を算出（"risk_based", "equal", "score" をサポート）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer による保守的見積り、残差に対する再配分ロジックを実装。

- 研究モジュール（src/kabusys/research/factor_research.py）
  - DuckDB 接続を受けてファクター計算を行う純粋関数群（prices_daily / raw_financials テーブル参照）。
  - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算（データ不足時は None）。
  - calc_volatility: ATR, 相対 ATR, 20日平均売買代金、出来高比率等（詳細な窓処理と NULL 伝播制御を実装）。
  - パフォーマンス上の配慮としてスキャン範囲にバッファを設ける。

- ツール: Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
  - SQLite（paper_trading DB）から集計して検証レポートを生成する CLI。
  - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数 等を算出。
  - P95 計算ユーティリティ、日付フィルタ、欠損時のフォールバック処理を実装。
  - デフォルト基準値（しきい値）を定義し、PASS/FAIL を判定:
    - 稼働率 >= 99%
    - 注文成功率 >= 90%
    - 送信率 >= 95%
    - P95 レイテンシ <= 200 ms
  - --from / --to / --db オプション対応。環境変数 PAPER_TRADING_SQLITE_PATH を優先的に利用。

### Changed
- なし（初期リリースのため変更履歴はなし）

### Fixed
- なし（初期リリース）

### Security
- .env ファイルについて注意喚起をドキュメント出力（config_setup が .env を生成する際に Git へのコミット禁止を明記）。

---

注記:
- 実行スクリプト（run_execution/run_monitoring）は PID ファイル・停止フラグ・kill flag 等のファイルベースの制御を使用しています。運用環境では data ディレクトリの適切な権限と監視を推奨します。
- .env の自動読み込みは OS 環境変数を上書きしない設計（protected set）。テスト等で自動読み込みを停止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。