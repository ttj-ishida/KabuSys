# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを採用します。  

参照: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- 今のところ未リリースの変更はありません。

## [0.1.0] - 2026-04-18
初回リリース。KabuSys の基本的なコア機能・ユーティリティと CLI を実装しました。

### Added
- 全体
  - パッケージ初版を追加。バージョンは src/kabusys/__init__.py の __version__ = "0.1.0"。
  - プロジェクトルート探索機能を実装し、.env ファイルの自動読み込みをサポート（kabusys.config）。
  - 環境変数パースの堅牢化（クォート・エスケープ・インラインコメント対応、export 形式対応）。

- 設定・セットアップ
  - Settings クラスを実装（kabusys.config）。多数の環境変数をプロパティとして取得・検証:
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（有効値検証）
    - データベースパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
    - Paper Trading 関連（PAPER_FILL_MODE）
    - 監視用閾値・PID/kill flag 関連
  - 対話式 .env ウィザードを追加（kabusys.config_setup）。.env の生成/更新をサポート。
  - validate_config CLI を追加（kabusys.validate_config）。.env と config/*.yaml の妥当性チェック機能（--strict オプションあり）。

- 実行系 / 監視
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用し、本番 DB と完全に分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（Mock を含む実装想定）。
    - ExecutionEngine を別スレッドで実行し、データディレクトリの停止フラグで安全に停止。
    - 起動時にプロセス優先度を「high」に設定。
  - SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検出でループ終了。
    - 監視 DB は環境に関わらず本番 sqlite_path を使用して初期化。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み付け（kabusys.portfolio.portfolio_builder）:
    - select_candidates: スコア降順 + tie-breaker を実装。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重（スコアが全て 0 の場合は警告して等分配にフォールバック）。
  - セクター集中・レジーム調整（kabusys.portfolio.risk_adjustment）:
    - apply_sector_cap: 既存保有比率が上限を超えるセクターの候補除外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear をサポート。未知はフォールバック）。
  - 株数決定・リスク制限（kabusys.portfolio.position_sizing）:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数算出、単元株（lot_size）丸め、aggregate cap スケーリング、cost_buffer（手数料/スリッページ考慮）対応。
    - risk_based では stop_loss_pct / risk_pct に基づく算出、per-stock 上限判定を実装。
    - aggregate cap 超過時のスケールダウンと端数配分ロジックを実装。

- ユーティリティ
  - ロギング初期化ユーティリティを追加（kabusys.utils.logging_setup）:
    - stdout ストリームハンドラ + 日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の環境変数を尊重。ファイルハンドラ作成失敗時はコンソール出力のみにフォールバック。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）:
    - set_process_priority(level): Windows / POSIX を吸収して優先度設定を試行（権限不足等は警告でスキップ）。
    - set_cpu_affinity(cpu_count): 指定コア数へのピン留めをサポート（権限やプラットフォームで制限あり）。

- 監視・検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）:
    - 指標: 稼働率（uptime）、注文成功率、送信率、リスク却下数、平均/最大/P95 レイテンシなどを算出して標準出力レポートを生成。
    - デフォルト DB パスは data/paper_trading.db。--from/--to/--db オプションをサポート。
    - P95 算出ロジックと閾値（稼働率 >= 99%, 成功率/送信率 等）を組み込み。

- 研究モジュール（基盤）
  - ファクター計算モジュールを追加（kabusys.research.factor_research）:
    - モメンタム / MA200 / ATR / 流動性等を計算する設計を開始。DuckDB 接続を受け取り prices_daily, raw_financials を参照する方針。
    - （注意）モジュールは一部実装中（calc_momentum の実装が途中）で、追加実装が必要。

### Changed
- N/A（初回リリースのため既存機能の変更はなし）

### Fixed
- N/A（初回リリースのため修正履歴はなし）

### Removed
- N/A

### Security
- 環境変数の取り扱い:
  - .env ファイルの自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 対話式ウィザードでは .env を Git にコミットしないよう注意喚起を出力。

### Notes / Known issues / TODO
- factor_research.calc_momentum が途中で終わっており、ファクター計算ロジックの残り実装が必要。
- apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる旨の TODO コメントあり。将来的に価格フォールバックを追加予定。
- position_sizing: 将来的に銘柄毎の lot_size をサポートする拡張が想定されている（現状はグローバル lot_size）。
- process_priority / set_cpu_affinity: 実行 OS や権限に依存し、失敗時は警告して処理を継続する実装（安全志向）。期待通りに動作しない環境があり得る点に注意。
- ログディレクトリ作成やファイルハンドラ作成に失敗した場合、コンソール出力にフォールバックする設計。
- Execution / Monitoring の停止は data/stop_requested.flag により制御する。Kill Switch 等の運用ルールは運用ドキュメントを参照のこと。

---

開発者向け補足:
- CLI
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper Trading レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 起動スクリプト
  - 監視プロセス: python -m kabusys.run_monitoring
  - 実行プロセス: python -m kabusys.run_execution

今後のリリースでは、research モジュールの完成、テストカバレッジ拡充、ブローカークライアントの抽象化強化、運用向けドキュメント整備を予定しています。