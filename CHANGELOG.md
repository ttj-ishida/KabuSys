# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

- リリースポリシー: 可能な限り意味のあるまとまった機能追加・改善ごとにバージョンを切ります。  
- 日付はリリース日を示します。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-20

初回公開リリース。本リポジトリは日本株自動売買システム「KabuSys」のコアユーティリティ、起動スクリプト、ポートフォリオ構築・ポジションサイズ計算、設定管理、検証ツール、Paper Trading 検証レポートなどを含みます。

### Added
- 基本パッケージ情報
  - パッケージバージョン定義: `kabusys.__version__ = "0.1.0"`。

- 環境／設定管理
  - Settings クラス（`kabusys.config.Settings`）を実装。環境変数から各種設定（DB パス、API トークン、運用モード、監視閾値など）を取得するプロパティを提供。
  - .env 自動ロード機能: プロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` と `.env.local` を読み込み。OS 環境変数の上書きを防ぐ保護機構を導入。自動ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - .env パーサ (`_parse_env_line`) を実装: `export KEY=val`、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応。

- 設定ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを実装。`.env` の初期作成・更新を支援し、必須/任意/シークレット項目を扱う。デフォルト値や選択肢表示、保存の確認を行う。

- 設定検証 CLI
  - `kabusys.validate_config` に設定検証ツールを実装。必須環境変数の有無、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在、`config/*.yaml` の存在・パース検証（PyYAML が存在する場合）などをチェック。`--strict` モードを追加（警告を FAIL 扱いにする）。

- 起動スクリプト
  - `run_execution.py`（ExecutionEngine 起動スクリプト）
    - プロセス優先度を起動時に "high" に設定する仕組みを呼び出す。
    - 運用モードが `paper_trading` の場合、Paper Trading 用の専用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離する設計。
    - ブローカークライアント作成のためのファクトリ `BrokerClientFactory.create(settings)` を呼び出す。
    - OrderRepository / OrderManager / RiskManager / Reconciler を構成し、ExecutionEngine（`engine.run_session`）を別スレッドで起動。停止フラグ（`data/stop_requested.flag`）を監視して安全に停止できる。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を提供し、初期ポートフォリオ値に broker.get_available_cash() を使用して設定する。
  - `run_monitoring.py`（SystemMonitor ポーリングループ起動スクリプト）
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出す。
    - 監視は環境にかかわらず本番用の sqlite_path を使用。
    - 停止フラグ（`data/stop_requested.flag`）を検知してループを終了する実装。
    - 各起動スクリプトでログ設定（`setup_logging(app_name=...)`）とプロセス優先度設定を共通で使用。

- ロギングユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`
    - ルートロガーに StreamHandler（stdout）と日次ローテートの TimedRotatingFileHandler（デフォルト `logs/<app_name>.log`）を追加。30 日分保持。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル解決順を実装（関数引数 > 環境変数 LOG_LEVEL > デフォルト INFO）。

- プロセス優先度ユーティリティ
  - `kabusys.utils.process_priority`
    - Windows と POSIX（Linux/Mac/FreeBSD）での優先度（nice / HIGH_PRIORITY_CLASS 等）を吸収して提供。
    - CPU affinity 設定関数 `set_cpu_affinity` を追加（最初の N コアに固定）。権限不足等の例外はログ警告でスキップ。

- ポートフォリオ構築ライブラリ
  - `kabusys.portfolio.portfolio_builder`
    - シグナル選定（スコア降順、タイブレークに signal_rank）: `select_candidates`
    - 等金額配分: `calc_equal_weights`
    - スコア加重配分（スコア合計が 0 の場合は等金額にフォールバック）: `calc_score_weights`
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中対策: `apply_sector_cap`（既存保有と当日売却予定を考慮し、特定セクターの新規候補を除外）
    - レジームに基づく投下資金乗数: `calc_regime_multiplier`（bull/neutral/bear のマッピング、未知値は 1.0 にフォールバックして警告）
  - `kabusys.portfolio.position_sizing`
    - ポジションサイズ計算: `calc_position_sizes`
      - allocation_method: `risk_based` / `equal` / `score` をサポート
      - 単元株（lot_size）丸め、単銘柄上限、aggregate cap（available_cash を超える場合にスケールダウン）を実装
      - cost_buffer を考慮した保守的コスト見積り、残差の扱いによる補正ロジックを実装
      - 入力データ欠損時のスキップやログ出力あり

- 研究／ファクター計算
  - `kabusys.research.factor_research` の導入（Momentum / Value / Volatility / Liquidity を想定した設計）
    - DuckDB を使った prices_daily / raw_financials を参照する設計方針。
    - モメンタム計算関数 `calc_momentum` を実装開始（関数の冒頭まで確認できる状態）。※一部実装が続く形でファイル途中で終了（今後の作業が必要）。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading 用 SQLite のトレードログ・監視ログから稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（平均・最大・P95）などを集計して標準出力にレポートを生成。
    - デフォルト DB パスは `data/paper_trading.db`。コマンドラインで日付範囲（--from/--to）や DB パス（--db）指定可能。
    - 指標の閾値に基づく PASS/FAIL 判定を実装（稼働率、成功率、送信率、P95 レイテンシなど）。

- その他ユーティリティ
  - `kabusys.utils.__init__`, `kabusys.tools.__init__` 等のパッケージ初期化ファイルを追加。
  - 各種 TODO コメント・堅牢性注記をコード内に追加（例: price 欠損時のフォールバック検討、将来的な lot_size 拡張など）。

### Changed
- 初回リリースのため変更履歴なし（新規実装群）。

### Fixed
- 初回リリースのため修正履歴なし。

### Deprecated
- なし

### Removed
- なし

### Security
- 機密情報（J-Quants トークン、kabu API パスワード、LINE トークン）は .env に保存することを想定し、README 等で .env を Git 管理しないよう注意喚起（config_setup にコメントヘッダを追加）。

### Known limitations / 注意点
- factor_research モジュールは設計方針・定義はあるもののファイルの途中で実装が途切れている箇所が確認されます。完全実装は今後のリリースで対応予定です。
- `SystemMonitor`, `ExecutionEngine`, `BrokerClientFactory` などの実体（詳細実装）はこの差分で参照されているが、今回のスナップショットでは一部の内部実装ファイルがここに含まれていない可能性があります（ただし起動スクリプト側の組み立て方針・安全処理は実装済み）。
- .env の自動読み込みロジックはプロジェクトルート検出に依存するため、パッケージ配布後も想定どおり動作するよう親ディレクトリ探索を行う設計です。テストや CI 等で自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を用意しています。
- 実行時にログディレクトリ作成やプロセス優先度設定が権限不足で失敗する可能性があります。これらは警告でスキップする設計になっています。

---

（注）本 CHANGELOG は提供されたソースコードを基に推測して作成しています。実際の変更履歴やリリースノートと差異がある場合は適宜調整してください。