# Changelog

すべての注目すべき変更はここに記録します。本ファイルは Keep a Changelog の形式に準拠しています。  

※ 以下は提示されたソースコードから推測して作成した変更履歴です。

## Unreleased
- （なし）

---

## [0.1.0] - 2026-04-17

初回公開リリース。本リリースでは自動売買システム KabuSys のコアユーティリティ、起動スクリプト、設定管理、ポートフォリオ構築ロジック、Paper Trading 検証ツール等を収録しています。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 設定読み込み・管理
  - `kabusys.config`：
    - .env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
    - .env のパースを強化（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、空行・コメント行の無視）。
    - 環境変数取得ヘルパーと必須チェック `_require()` を提供。
    - 各種設定プロパティを集約した `Settings` クラスを追加（DBパス、Paper Trading 用設定、監視閾値、環境種別判定など）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化をサポート。

- 環境設定ウィザード
  - `kabusys.config_setup`：
    - 対話式で .env を作成・更新するウィザードを実装。
    - 入力項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 関連など）を内蔵。
    - シークレット値はマスク表示、デフォルト値・選択肢サポート、保存プレビュー、.env 書き込み機能を提供。
    - 生成される .env に関する注意コメント（Git にコミットしない等）を出力。

- 設定検証 CLI
  - `kabusys.validate_config`：
    - 実行前に環境変数や config/*.yaml の存在・基本整合性を検証する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DBパスの親ディレクトリ存在確認、YAML パース検証（PyYAML があれば実施）等を行う。
    - `--strict` オプションで警告をエラー扱いにできる。

- 起動スクリプト / デーモン類
  - `kabusys.run_monitoring`：
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。不正値は警告してデフォルトを使用。
    - 監視は環境にかかわらず本番用 SQLite パス（Settings.sqlite_path）を使用する設計。
    - プロセス起動時にプロセス優先度を High に設定（`set_process_priority("high")`）。
    - 停止フラグ（data/stop_requested.flag）の検出で安全にループ終了。

  - `kabusys.run_execution`：
    - ExecutionEngine 起動スクリプトを実装。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用の専用 SQLite（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）に記録して本番 DB と分離。
    - 起動時にプロセス優先度を High に設定。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - RiskManager のデフォルト設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を注記。
    - ExecutionEngine は別スレッドで run_session を実行し、停止フラグ検知時に engine.stop() を呼んでシャットダウン。

- データベース / 分析基盤
  - DuckDB を分析用に統合（Settings.duckdb_path、各スクリプトで duckdb.connect を使用）。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report`：
    - Paper Trading の結果（SQLite）から検証レポートを生成する CLI を実装。
    - 指標: 稼働率(uptime)、注文成功率(fill rate)、送信率(send rate)、リスク却下数、レイテンシ（avg/max/P95）を算出。
    - P95（95パーセンタイル）計算実装。
    - 各指標の閾値判定（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）に基づく PASS/FAIL 判定を出力。
    - コマンドライン引数で期間指定（--from/--to）および DB パス指定（--db）をサポート。

- ポートフォリオ構築ロジック（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`：
    - 候補選定 select_candidates（スコア降順、同点は signal_rank でタイブレーク）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコアが 0 の場合は等金額にフォールバックし警告）。

  - `kabusys.portfolio.risk_adjustment`：
    - apply_sector_cap：セクター集中制限。既存保有のセクター別時価を計算し、上限超過セクターの候補を除外。unknown セクターは上限の対象外。
    - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは 1.0 にフォールバック（警告）。

  - `kabusys.portfolio.position_sizing`：
    - calc_position_sizes：各銘柄の発注株数計算。allocation_method（risk_based / equal / score）対応。
    - risk_based 計算（risk_pct, stop_loss_pct に基づくベース株数算出）。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、利用上限（max_utilization）の適用。
    - aggregate cap により予算超過時のスケーリングと残差処理（lot 単位での再配分）。
    - cost_buffer（スリッページ・手数料見積）を考慮した保守的計算。
    - 不足価格/欠損価格時のログ出力（スキップ）。

- ユーティリティ
  - `kabusys.utils.process_priority`：
    - プロセス優先度・CPU affinity 設定ユーティリティを実装。
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収。`set_process_priority(level)` と `set_cpu_affinity(cpu_count)` を提供。
    - 権限不足や未対応プラットフォームでは警告を出して安全にスキップ。

- 研究用ファクター計算
  - `kabusys.research.factor_research`（DuckDB を利用）：
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20）、流動性（20日平均売買代金）などのファクター計算関数を実装（calc_momentum, calc_volatility 等）。
    - prices_daily テーブルのみ参照する設計で外部 API に依存しない。
    - データ不足時は None を返す安全設計。

### Changed
- なし（初回リリースに該当）。

### Fixed
- なし（初回リリースに該当）。

### Notes / 注意事項
- 監視（run_monitoring）は「環境にかかわらず本番 sqlite_path を使う」と明記されています。開発環境で監視データを本番 DB に書きたくない場合は設定（SQLITE_PATH）やコードの運用方法に注意してください。
- .env 自動ロードはプロジェクトルートの検出に依存します。配布後やインストール環境で期待どおりに動作しない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自分で環境変数を適用してください。
- process_priority の設定は権限に依存します（Linux の負の nice 値設定には管理者権限が必要になる場合があります）。失敗時は警告となり処理継続します。
- Paper Trading は本番 DB と分離される設計（PAPER_TRADING_SQLITE_PATH）ですが、環境変数の設定ミスにより実運用データを書き込む危険がないよう注意してください。
- config_setup により生成される .env は機密情報（API トークン等）を含みます。リポジトリにコミットしないでください。

---

今後の改善候補（ソースコードからの推測）
- stocks 毎の lot_size 対応（position_sizing の TODO に記載）。
- apply_sector_cap の price 欠損時フォールバックロジック（前日終値や取得原価など）。
- factor_research のファクター計算の追加（Value/ROE 等の財務指標の計算補完）。
- validate_config の YAML パースを強化してスキーマチェックを追加。