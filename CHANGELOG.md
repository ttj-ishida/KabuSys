# CHANGELOG

すべての注目すべき変更点を記載します。形式は "Keep a Changelog" に準拠しています。

- リポジトリの変更は主に初期実装（v0.1.0）の追加を反映しています。
- ここに記載の内容はソースコードから推測した機能説明・挙動であり、実際の設計意図と差異がある場合があります。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-21

### Added
- 実行エントリ・監視エントリ
  - run_execution: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用の SQLite（デフォルト: data/paper_trading.db）に完全分離して記録。
    - エンジンはスレッドで実行し、data/stop_requested.flag の検出で安全に停止可能。実行用 PID ファイル (data/execution.pid) を扱う。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に依らず本番用 sqlite_path を使用して監視データを書き込む。

- 設定・環境変数管理
  - Settings クラスを実装し、環境変数経由で設定値を集中管理。
    - J-Quants / kabuステーション / DB パス / LINE 通知設定 / しきい値等をプロパティで提供。
    - PAPER_FILL_MODE（instant | partial | never | reject）の検証ロジックを追加。
    - paper_trading 用 DB パス PAPER_TRADING_SQLITE_PATH をサポート。
    - KABUSYS_ENV 値検証（development / paper_trading / live）とログレベル検証を実装。
  - 自動 .env ロード機能:
    - プロジェクトルート（.git または pyproject.toml）を探索し、.env/.env.local をロード（OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - config_setup: 対話式ウィザードで .env を生成/更新する CLI を追加。
    - シークレット入力のマスク表示、選択肢、デフォルト値、.env ファイルへの安全な書き込みをサポート。

- 設定検証ツール
  - validate_config: .env と config/*.yaml の簡易検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML のパース検証（PyYAML 未インストール時は警告）を実施。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils.logging_setup: StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を用いた統一ロギング設定を追加。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル/ログディレクトリの解決順を実装（引数 > 環境変数 > デフォルト）。
  - utils.process_priority: クロスプラットフォームでプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを追加。
    - Windows / POSIX (Linux, Darwin, FreeBSD) に対応し、権限不足時は警告を出してフォールバック。

- ポートフォリオ構築モジュール
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順、同点は signal_rank 昇順でソートして上位 N 件を返す。
    - calc_equal_weights: 等金額分配を実装。
    - calc_score_weights: スコア加重分配を実装。全銘柄スコアが 0 の場合は等金額にフォールバックし警告ログを出力。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター別エクスポージャーが閾値を超える場合に同セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に基づく投下資金乗数を実装。未知のレジームは警告ログを出して 1.0 でフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method に応じた株数計算を実装（risk_based / equal / score）。
      - リスクベース（risk_pct, stop_loss_pct）・単元株（lot_size）丸め・1銘柄上限・aggregate cap（available_cash に対するスケーリング）をサポート。
      - cost_buffer による手数料/スリッページの保守的見積り、余剰キャッシュを用いた繰上げ配分（lot 単位）を実装。
      - 価格欠損時のスキップとログ出力。

- Paper Trading 検証ツール
  - tools.paper_verification_report: ペーパートレード DB（デフォルト: data/paper_trading.db）から検証レポートを生成するスクリプトを追加。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなど。
    - 閾値を定義し PASS/FAIL 判定を行う。テーブルが存在しない場合は graceful に N/A を扱う。
    - --from/--to/--db オプションをサポート。

- データ解析基盤（着手）
  - research.factor_research: DuckDB 接続を受けてモメンタム・ボラティリティ等を計算するモジュールを追加（モジュール実装の一部を含む）。DuckDB の prices_daily / raw_financials を前提にした設計。

### Changed
- ロギングの標準出力: StreamHandler に stderr ではなく stdout を使用するように変更（cron 等でリダイレクトしやすくするため）。
- .env 読み込みの挙動:
  - OS 環境変数を保護しつつ .env/.env.local を順に読み込む仕組みを明確化（.env.local は上書き可能）。
  - .env パースはクォート・エスケープ・インラインコメントを考慮する実装に拡張。
- 監視起動の DB 挙動:
  - run_monitoring は KABUSYS_ENV にかかわらず監視用 DB 接続に settings.sqlite_path（本番想定のパス）を使用する旨を明示。
- process_priority のフォールバック実装:
  - Windows の定数が無い環境でも安全にモジュールをロードできるよう getattr によるフォールバックを使用。

### Fixed / Robustness
- run_monitoring.loop 内で monitor.check_once() が例外を投げてもループを継続して次のポーリングまで待機するよう例外ハンドリングを追加（ログ出力あり）。
- run_execution: 起動前に停止フラグが既に存在する場合は起動を中止するガードを追加。
- DB 初期化: init_monitoring_db を起動時に呼ぶことで監視テーブルの存在を保証（冪等）。
- logging_setup: 既存ハンドラがある場合は flush/close のうえで削除し、二重設定を防止。
- validate_config: PyYAML 未導入時は YAML 検証をスキップして警告を出す。config/*.yaml の存在・パース検証を実装。

### Documentation / UX
- config_setup による .env ウィザードで入力のヒント、既存値の再利用、保存前の確認を行うユーザー対話を実装。
- README 相当の注意事項（.env を絶対に Git にコミットしないなど）を .env 出力ヘッダに記載。

### Security
- .env の取り扱いに関する注意を明記（生成スクリプトが .env にシークレットを書き込むため、git 管理に含めないことを強調）。

### Known limitations / Notes
- research.factor_research モジュールは部分実装で終了している（末尾で実装継続が必要）。
- position_sizing の lot_size は現状全銘柄共通の前提。将来的に銘柄別 lot_map を受け取る拡張を想定する TODO が残る。
- apply_sector_cap は price が欠損（0.0）の場合にエクスポージャーが過少見積もられる可能性があり、フォールバック価格の導入が検討事項としてコメントで残されている。
- process_priority / set_cpu_affinity は権限不足や未対応 OS の場合に安全にスキップするが、環境によっては効果が限定的。

---

（以降のリリースでは、実装の完了、テスト追加、research モジュールの完成、バグ修正やドキュメント充実を反映してください。）