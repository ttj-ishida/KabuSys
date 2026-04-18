# Changelog

すべての注目すべき変更を記録します。  
このファイルは「Keep a Changelog」準拠のフォーマットを採用しています。

フォーマットのルール:
- 変更は意味のあるまとまりごとに記載しています（Added / Changed / Fixed / Removed 等）。
- 日付はリリース日です。

## [Unreleased]

（現在の差分はありません）

## [0.1.0] - 2026-04-18

### Added
- 初回リリース: KabuSys 基本機能群を追加。
- 環境設定 / ロード
  - Settings クラスを追加し、環境変数から各種設定を取得可能に（J-Quants / kabuAPI / DB パス / 各種閾値等）。
  - プロジェクトルート（.git または pyproject.toml）を基準に .env 自動読み込みを実装。`.env` と `.env.local` の優先順位を考慮。
  - .env パーサーを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。

- CLI / ユーティリティ
  - config_setup: 対話式の .env 設定ウィザードを追加（鍵/非表示入力、既存値再利用、ファイル書き出し）。
  - validate_config: 起動前の設定検証ツールを追加（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検証（PyYAML が存在する場合））。
    - --strict オプションで警告を FAIL 扱いにできる。
  - tools/paper_verification_report: ペーパートレード検証レポート生成ツールを追加。稼働率・注文成功率・送信率・レイテンシ（P95）等を算出し PASS/FAIL 判定を出力。

- 実行 / 監視ランナー
  - run_execution: ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite (data/paper_trading.db をデフォルト) を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを作成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立ててエンジンをデーモンスレッドで実行。stop flag（data/stop_requested.flag）と PID ファイル管理に対応。
    - RiskManager のデフォルト設定（max_position_pct 等）を指定。初期ポートフォリオ値は broker.get_available_cash() を利用。
  - run_monitoring: SystemMonitor 起動用スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視 (monitoring) は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して起動（監視専用 DB 初期化処理を実行）。
    - 停止フラグファイルを監視して安全にループ終了。

- ロギング / プロセス管理ユーティリティ
  - utils.logging_setup.setup_logging を追加。
    - stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler をルートロガーに設定。
    - ログディレクトリ（LOG_DIR 環境変数 / 引数で上書き可）、ログレベルの優先順位（引数 > LOG_LEVEL > デフォルト）を実装。
    - 日次ローテーションで 30 日分保持。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils.process_priority を追加。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供し、Windows / POSIX（Linux/macOS/FreeBSD）差分を吸収して優先度と CPU affinity を設定。psutil の権限エラーや未実装 API は警告し安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: signal スコアでソートして上位 N を返す（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等分配・スコア正規化重み計算。スコア合計が 0 の場合は等分配にフォールバックして警告。
  - portfolio.risk_adjustment
    - apply_sector_cap: 同一セクターの既存保有比率が閾値を超える場合、そのセクターの新規候補を除外。`sell_codes`（当日売却予定）をエクスポージャー計算から除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知のレジームは 1.0 でフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: risk_based / equal / score の各方式に対応した株数決定を実装。単元株（lot_size）丸め、ポジション上限（max_position_pct）、投下資金上限（max_utilization）、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積もり、残余キャッシュを使った端数配分ロジックを実装。

- research モジュールの骨組み
  - research.factor_research にてモメンタム等のファクター計算のための環境（定数・calc_momentum の骨子）を追加（DuckDB による prices_daily / raw_financials 参照を想定）。（実装は一部のみ含まれる）

- パッケージ情報
  - パッケージ初期バージョンを __version__ = "0.1.0" として設定。

### Changed
- なし（初回リリースのため）

### Fixed
- 入力の妥当性・フェイルセーフを強化
  - MONITOR_POLL_INTERVAL が不正な場合に警告してデフォルト値にフォールバックする挙動を追加。
  - .env 読み込み時の IO エラーを警告で扱い処理を継続するようにした。
  - ログディレクトリ作成失敗や psutil による優先度設定失敗時は警告出力で処理を継続。

### Removed
- なし

### Security
- 環境変数ファイル (.env) を生成する際に、注意書きとして「.env を Git にコミットしないこと」を明示。

---

注意事項 / 実行時の挙動
- 監視 (run_monitoring) は KABUSYS_ENV に依存せず settings.sqlite_path（本番監視 DB）を使用します。実験的に paper_trading を行う場合は run_execution が settings.paper_sqlite_path を使用して DB を分離します。
- run_execution/run_monitoring は起動時に set_process_priority("high") を試みますが、権限不足等で設定できない場合は警告を出して継続します。
- validate_config は PyYAML がインストールされていない場合、config/*.yaml の内容検証をスキップしますが、存在チェックは行います。
- tools/paper_verification_report はデフォルトで data/paper_trading.db を参照します。別パスは環境変数 PAPER_TRADING_SQLITE_PATH または --db オプションで指定できます。

（この CHANGELOG はソースコード内の仕様・コメントから推測して作成しています。実際のリリースノートには追加の運用情報や既知の制限事項を併記することを推奨します。）