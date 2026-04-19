# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
リリースの日付はコードベースから推測して記載しています。

## [0.1.0] - 2026-04-19

### Added
- 全体
  - 初回公開相当の機能群を追加。プロジェクトのエントリポイント、設定管理、ユーティリティ、ポートフォリオ構築、実行／監視スクリプト、ツールを含む。
  - パッケージバージョンを `__version__ = "0.1.0"` に設定（src/kabusys/__init__.py）。

- 設定・CLI
  - Settings クラスによる環境変数ベースの設定取得を実装（src/kabusys/config.py）。
    - 必須値チェック用の `_require()`、環境の検証（development / paper_trading / live）、ログレベル検証等を提供。
    - デフォルトパス（DuckDB/SQLite 等）や paper trading 用 DB パス、PAPER_FILL_MODE 検証などを含む。
  - 自動 .env ロード機能を追加（プロジェクトルートの特定に .git または pyproject.toml を使用）。`.env` → `.env.local` の優先度で読み込む（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
  - 設定検証 CLI `kabusys.validate_config` を追加（src/kabusys/validate_config.py）。
    - 必須環境変数の有無、KABUSYS_ENV・LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および PyYAML によるパースチェック、live 環境用のガードを実装。
    - `--strict` オプションで警告を失敗扱いにできる。
  - 対話式環境設定ウィザード `kabusys.config_setup` を追加（src/kabusys/config_setup.py）。
    - `.env` の初期作成・更新を支援。J-Quants / kabu API / DB パス / LINE 通知設定等の項目を対話的に編集・保存できる。

- 実行・監視スクリプト
  - 実行エンジン起動スクリプト `run_execution.py` を追加（src/kabusys/run_execution.py）。
    - 起動時にプロセス優先度を "high" に設定するユーティリティを呼び出す。
    - `KABUSYS_ENV=paper_trading` の場合は paper trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組み立てとデーモンスレッドでの実行制御を実装。
    - 停止フラグ（data/stop_requested.flag）が存在する場合は起動・実行中にエンジン停止する制御を実装。
  - 監視ポーリング起動スクリプト `run_monitoring.py` を追加（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60秒）。不正な値はデフォルトにフォールバックして警告を出す。
    - Monitoring は環境にかかわらず本番の sqlite_path を使用する旨を明示。
    - 停止フラグ検出でループを終了し、例外発生時はロギングして次のポーリングまで待機する堅牢性を持たせている。

- データベース / ツール
  - 監視テーブル初期化ユーティリティ init_monitoring_db を利用して DB の存在保証を行う呼び出しを実装（init_monitoring_db の呼び出しは冪等）。
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs テーブルから稼働率、注文成功率、送信率、レイテンシ（P95 など）を集計して PASS/FAIL を判定するレポートを出力。
    - 閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）を定義。
    - 日付フィルタリング、P95 計算、データ欠損時の扱いを実装。

- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: score 降順、同点は signal_rank でタイブレークして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。全スコアが 0 の場合は等配分にフォールバックして警告。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター別時価を計算してセクター上限を超える場合に候補を除外。unknown セクターは上限除外対象外。
    - calc_regime_multiplier: レジーム(bull/neutral/bear) に応じた投下資金乗数を返す。未知レジームは警告を出して 1.0 をフォールバック。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の各配分方式に基づいて銘柄ごとの発注株数を算出。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）超過時のスケーリングおよび残差処理を実装。
    - cost_buffer による手数料・スリッページ見積りをサポート。

- ユーティリティ
  - logging_setup（src/kabusys/utils/logging_setup.py）
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定するユーティリティを追加。既存ハンドラはクリアしてから再設定する。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップし stdout のみで継続。stdout を利用することで cron 等からのリダイレクト運用に配慮。
  - process_priority（src/kabusys/utils/process_priority.py）
    - Windows / POSIX（Linux/Mac/FreeBSD）を吸収するプロセス優先度設定（set_process_priority）を追加。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。
    - 権限や未実装 API で失敗した場合は警告を出して安全にスキップする設計。

- 研究モジュール（着手）
  - factor_research のモジュール骨子を追加（src/kabusys/research/factor_research.py）。モメンタム・ボラティリティ・流動性等の計算方針を定義し、DuckDB 接続を受けて計算する設計が示されている（実装途中）。

### Changed
- ロギング
  - console 出力を stderr ではなく stdout にする方針を採用（setup_logging）。cron / systemd 等でのログ統合運用を考慮。

### Fixed
- 環境変数パースの堅牢化（src/kabusys/config.py）
  - .env パーサで `export KEY=val` 形式、クォート付き値（エスケープ対応）、インラインコメント処理（クォート外）などに対応し、不正行をスキップする実装とした。
- run_monitoring のポーリング間隔取得で不正値が指定された場合にデフォルトへフォールバックして警告を出すように（MONITOR_POLL_INTERVAL の取り扱い）。
- DB ハンドラの安全なクローズを追加（run_execution / run_monitoring の finally ブロックで sqlite & duckdb 接続を閉じる）。

### Security
- .env の取り扱いに関する注意書きを config_setup に追記（.env を Git にコミットしないことを明記）。

### Notes / Implementation details
- Paper Trading 周りは本番 DB と完全分離する設計（paper_sqlite_path を使用）。これによりペーパートレードデータが本番データに影響しないようになっている。
- 監視（monitoring）は環境にかかわらず本番 sqlite_path を参照する設計になっており、監視情報は共通 DB に保管される。
- 一部モジュール（factor_research 等）は実装が途中でファイル末尾が未完となっている箇所があるため、今後の追加実装で完全化予定。

---

上記はソースコードの実装内容から推測してまとめた ChangeLog です。細かな振る舞いや追加の修正（例: BrokerClient の実装や ExecutionEngine の詳細）は該当モジュールの実装に依存します。必要であれば、各モジュールごとにもう少し詳細な開発履歴や既知の TODO（未実装箇所）を追記できます。どのレベルの詳細を出力しますか？