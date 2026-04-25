# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。

次のバージョンに関する未確定の変更は "Unreleased" に記載します。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-25
初回リリース。日本株自動売買システム「KabuSys」の基本的なランタイム、設定管理、ポートフォリオ構築、ユーティリティ、診断ツール群を追加。

### Added
- 基本バージョン情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で間隔を変更可能。  
    - 監視は環境に関わらず本番用の sqlite_path を使用。停止はプロジェクト内の stop_requested.flag ファイルで制御。
  - run_execution: ExecutionEngine の起動スクリプトを追加。  
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用の DB に記録して本番 DB と分離。  
    - 実行中は PID ファイルの書き出し・停止フラグの監視による安全停止を実装。

- 設定・環境管理
  - Settings クラスを追加（kabusys.config）。  
    - .env ファイルおよび環境変数から設定を取得。  
    - 自動ロード順序は OS 環境変数 > .env.local > .env。プロジェクトルートを .git または pyproject.toml で探索するため CWD に依存しない。  
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロードを無効化可能。  
    - 各種設定プロパティ（DB パス、API トークン、Paper Trading 関連設定、監視阈値など）を提供。  
    - `PAPER_FILL_MODE` の検証を実装（"instant" | "partial" | "never" | "reject" のみ許容）。

- 設定支援 CLI
  - config_setup: 対話式ウィザードで .env を初期作成／更新する CLI を追加。  
    - シークレット項目は表示をマスク、既存値の再利用、確認プロンプト、ファイル書き込み機能を備える。
  - validate_config: 起動前の設定検証 CLI を追加。  
    - 必須環境変数の有無チェック、KABUSYS_ENV／LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在・パースチェック（PyYAML が無ければ警告）。  
    - `--strict` オプションで警告を FAIL 扱いにできる。ライブ環境向けのガード（LINE トークン未設定、KILL_FLAG_CLEAR_ON_START の危険設定等）を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのソート／上位絞り込み。  
    - calc_equal_weights, calc_score_weights: 等金額・スコア加重の重み計算（スコア全 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェックに基づく候補除外。売却予定銘柄の除外や "unknown" セクターの扱いを定義。  
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは 1.0 でフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づき発注株数を計算。  
      - 単元（lot_size）丸め、1銘柄上限や aggregate cap（利用可能現金超過時のスケールダウン）、cost_buffer による保守見積り、端数再配分ロジックを実装。  
      - パラメータ化（risk_pct, stop_loss_pct, max_position_pct, max_utilization, lot_size, cost_buffer）を提供。  
      - 現在の実装では全銘柄共通単元を想定（将来的に銘柄別拡張を想定する TODO が存在）。

- ユーティリティ
  - utils.logging_setup: 一貫したロギング設定ユーティリティを追加。  
    - stdout へ StreamHandler、日次ローテート（30日保持）の TimedRotatingFileHandler をルートロガーに設定。  
    - ログディレクトリの自動作成（失敗時はファイル出力をスキップしてコンソールのみで継続）。  
    - ログ出力を stdout にすることでスケジューラや cron との相性を考慮。
  - utils.process_priority: クロスプラットフォームのプロセス優先度 / CPU affinity 設定を追加（psutil 利用）。  
    - Windows / POSIX（Linux, macOS, FreeBSD）を吸収。アクセス権限不足や未対応 OS の場合は警告を出してスキップ。

- ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite の統計から検証レポートを生成する CLI を追加。  
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（平均/最大/P95）を算出し PASS/FAIL 判定を出力。  
    - デフォルト DB パスは data/paper_trading.db。コマンドラインで期間指定および DB 指定可能。

- 研究用モジュール（骨組み）
  - research.factor_research: ファクター計算モジュール（Momentum / Value / Volatility / Liquidity 設計方針と一部実装）。  
    - DuckDB を受け取り prices_daily / raw_financials を参照して因子を計算する設計。※一部実装が継続中（ファイル末尾で未完の箇所あり）。

### Changed
- DB 分離ポリシーの明確化
  - ExecutionEngine 起動時は paper_trading 環境なら専用の PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用して本番データと完全に分離するように実装。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用（監視は本番 DB に対して行う設計意図）。

- ログ設定の挙動
  - 既存のハンドラをクリアしてから再設定することで多重設定を防止。  
  - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップして stdout のみで継続するフェイルセーフを追加。

- .env 読み込みの堅牢化
  - .env パーサーは export 付き行、シングル/ダブルクォート、エスケープ、インラインコメントの扱いを考慮するよう拡張。  
  - 自動ロードがプロジェクトルート検出に依存する仕様とし、ルートが特定できない場合は自動ロードをスキップする設計に変更。

- run_* スクリプトの初期化順序
  - ログ設定 → プロセス優先度設定 → 設定読み込み → DB 初期化 の順で起動するよう明確化（プロセス優先度は最初に設定）。

### Fixed
- 環境変数値検証の改善
  - MONITOR_POLL_INTERVAL の不正値（非整数や 0 以下）に対してデフォルトへフォールバックし、警告ログを出すように修正（time.sleep に渡す値による例外回避）。
  - Settings.env / LOG_LEVEL / PAPER_FILL_MODE 等で不正な値を検出して明確なエラーメッセージを出すように改善。

- ロギングの二重出力防止
  - setup_logging が既存ハンドラを適切に削除するようにしたため、複数回呼び出した際の重複ログ出力を防止。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

### Known issues / TODO
- research.factor_research モジュールはファクター計算の設計に沿った骨組みを実装済みだが、ファイル末尾に未完のコード（切れている行）が存在するため完全実装が必要。  
- portfolio.risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少評価される可能性があり、前日終値や取得原価でのフォールバックを行う TODO コメントあり。  
- position_sizing: 将来的に銘柄別の lot_size をサポートする拡張の TODO が残る。

---

作業の全体像（概要）
- このリリースでは、システムの起動／設定管理／検証／運用監視／ポートフォリオ構築／注文サイズ決定／ログ／プロセス優先度設定など、運用に必要な基盤を一通り整備しました。Paper Trading と本番データの分離、安全な起動プロセス、ログのローテーション、設定の対話式ウィザード、検証ツールなど運用性を重視した実装が含まれます。