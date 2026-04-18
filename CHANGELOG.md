# Changelog

すべての注目すべき変更は「Keep a Changelog」フォーマットに従って記載しています。  
各バージョンは semantic versioning に従います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

### Added
- 初回リリース。
- 基本アプリケーションの設定管理機能を追加
  - kabusys.config.Settings: 環境変数ベースの設定読み出し、値チェック（KABUSYS_ENV, LOG_LEVEL 等）。
  - 自動 .env ロード機能（プロジェクトルート検出: .git / pyproject.toml を基準）。
  - .env パースの強化: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応。
  - Settings によるデフォルト値と検証ロジック（PAPER_FILL_MODE の有効値チェック等）。

- 環境設定ウィザード CLI を追加
  - kabusys.config_setup: 対話式で .env を作成・更新するウィザード。
  - 秘匿入力（マスク表示）や選択肢サポート、既存 .env の読み込み・再利用、最終確認・書き込み機能を提供。

- 設定検証 CLI を追加
  - kabusys.validate_config: .env と config/*.yaml の事前検証ツール。
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスや config YAML の存在/パース検証、KABUSYS_ENV=live 時の追加ガード。
  - --strict モードをサポート（警告を FAIL と扱う）。

- 実行系 / 監視系起動スクリプトを追加
  - run_execution: ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと起動処理（PID ファイル、停止フラグ対応）。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec 等）と initial_portfolio_value を broker.get_available_cash() から初期化。

  - run_monitoring: SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、1 秒以上に正規化）。
    - 監視 DB は環境にかかわらず Settings.sqlite_path（本番 sqlite_path）を使用。
    - 停止フラグファイル（data/stop_requested.flag）による安全停止対応。
    - 例外を捕捉してループ継続、KeyboardInterrupt による終了処理。

- ログ・プロセスユーティリティを追加
  - kabusys.utils.logging_setup.setup_logging:
    - stdout 出力用 StreamHandler（stdout）、日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ自動作成、作成失敗時はコンソールのみで継続。
    - ログレベルの解決順（関数引数 > 環境変数 LOG_LEVEL > デフォルト）。
    - ログは stdout を使うことでスケジューラや cron の出力リダイレクトに配慮。

  - kabusys.utils.process_priority:
    - プロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティ。
    - Windows（psutil の priority class）と POSIX（nice 値）の差分を吸収。
    - 権限不足や未対応 OS を想定したフォールバックと警告ログ。

- ポートフォリオ構築モジュールを追加
  - kabusys.portfolio.portfolio_builder:
    - 候補選定（select_candidates: スコア降順・タイブレークで signal_rank）。
    - 重み計算（calc_equal_weights, calc_score_weights）。スコアが全て 0 の場合は等金額配分にフォールバックし警告。

  - kabusys.portfolio.risk_adjustment:
    - セクター集中制限適用（apply_sector_cap）。
      - 既存保有のセクター別エクスポージャー計算（売却予定銘柄の除外対応）。
      - "unknown" セクターは制限を適用しない仕様。
      - 将来的な価格フォールバックの TODO コメントを含む。
    - レジーム乗数（calc_regime_multiplier）: bull/neutral/bear に基づく乗数を返す（未知レジームは 1.0 でフォールバックし警告）。

  - kabusys.portfolio.position_sizing:
    - 発注株数計算（calc_position_sizes）。
      - allocation_method による分岐: "risk_based" / "equal" / "score"。
      - 単元株（lot_size）での丸め、1銘柄上限（max_position_pct）、集約上限（available_cash / max_utilization）を考慮。
      - cost_buffer による保守的コスト見積もり、合計コスト超過時のスケーリングと端数補正アルゴリズムを実装。
      - 価格欠損時にスキップするロジック、デバッグログ出力。

- リサーチ（ファクター計算）モジュールを追加（部分実装）
  - kabusys.research.factor_research: DuckDB 接続を受け取って prices_daily / raw_financials を参照し、Momentum / Value / Volatility / Liquidity 等のファクターを計算する方針を実装。
  - モメンタム計算（calc_momentum）の設計と定数（MA/ATR/期間など）を定義（実装は継続中 / 一部省略）。

- Paper Trading 検証ツールを追加
  - kabusys.tools.paper_verification_report:
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から期間集計を行い、稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を出力。
    - 判定基準（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）を定義し PASS/FAIL レポートを生成。
    - 日付フィルタ（--from / --to）と --db オプションをサポート。
    - P95 計算ユーティリティ、NULL/テーブル不存在に対する耐性（OperationalError のハンドリング）。

- パッケージ情報
  - バージョン番号を __version__ = "0.1.0" として設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- 環境変数パーサーやユーティリティでの堅牢性向上（無効な値は警告/例外で明示する挙動を導入）。
  - MONITOR_POLL_INTERVAL が不正な値（0 以下や非整数）の場合、デフォルト（60 秒）にフォールバックし警告を出力。
  - 環境設定の自動ロードで OS 環境変数を保護（.env の上書きを防止）する機構を追加。

### Security
- .env ファイルの生成スクリプト（config_setup）で「.env を決して Git にコミットしない」旨の注記を出力。

### Notes / Known issues
- factor_research.calc_momentum の実装が途中で切れている（コメント/定数は存在）。DuckDB を使ったファクター実装は継続開発が必要。
- position_sizing の価格フォールバック（前日終値など）が未実装のため、price が欠損した場合にエクスポージャーが過小評価される恐れあり（TODO コメントあり）。
- process_priority / set_cpu_affinity は権限不足やプラットフォーム差異により設定できない場合がある。失敗時は警告ログを出して安全にスキップする設計。

---

開発者向けメモ:
- 今後は monitoring_db、system_monitor、execution 内部コンポーネント（Engine 実装、BrokerClient 実装など）を含めた統合テストを推奨します。
- ドキュメント: PortfolioConstruction.md / StrategyModel.md など参照箇所が多数あるため、ドキュメント整備を進めてください。