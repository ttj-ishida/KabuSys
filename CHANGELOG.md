# CHANGELOG

すべての変更点は「Keep a Changelog」準拠の形式で記載しています。

## [Unreleased]

（次回リリースに向けた未リリースの変更点をここに記載してください）

---

## [0.1.0] - 2026-04-19

初回リリース。KabuSys のコアユーティリティ、実行・監視ランチャ、設定ツール、ポートフォリオ構築・ポジションサイジング、ペーパートレード検証等を提供します。

### Added
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用の Paper Trading 用 SQLite DB（data/paper_trading.db、環境変数で上書き可）と MockBrokerClient を使用して本番 DB と完全分離。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用。
- 設定関連
  - config.py: .env 自動読み込み機能（.env / .env.local、OS 環境変数の保護対応）、.env パースロジック（export 形式、クォート/エスケープ、インラインコメント扱い等）、各種設定プロパティを追加。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。シークレットは表示をマスクして入力可能、保存用のテンプレートを生成。
  - validate_config.py: 起動前設定検証 CLI を追加。必須環境変数の未設定チェック、KABUSYS_ENV 検証、ログレベル、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML 未インストール時は警告）、本番環境向けのガードチェック、--strict モードを提供。
- ユーティリティ
  - utils/logging_setup.py: ルートロガーの統一セットアップを追加。StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、既定 30 日保持）を設定。LOG_DIR/LOG_LEVEL の解決順に対応。ログディレクトリ作成失敗時はファイル出力をスキップして警告。
  - utils/process_priority.py: プロセス優先度（high/normal/low）および CPU affinity の設定ユーティリティを追加。Windows / POSIX 差分を吸収し、権限不足や未対応 OS の場合は警告を出して安全にスキップ。
- ポートフォリオ構築・リスク調整・ポジションサイジング
  - portfolio/portfolio_builder.py: 候補選定（スコア降順・signal_rank によるタイブレーク）、等金額配分、スコア加重配分（全スコアが 0 の場合は等分配へフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中上限適用（既存保有を考慮、unknown セクターは上限適用除外）、市場レジームに応じた投下資金乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" マッピング、未知レジームは警告の上で 1.0 にフォールバック）を実装。
  - portfolio/position_sizing.py: allocation_method に基づく株数計算を実装（"risk_based", "equal", "score"）。単元株丸め、1 銘柄上限、aggregate cap（available_cash を超える場合はスケールダウン）や cost_buffer を考慮したスケーリング／端数処理を実装。
- 監視・モニタリング DB 初期化フック（monitoring.monitoring_db.init_monitoring_db を起動スクリプトから呼び出し、監視テーブルの冪等初期化を保証）。
- ペーパートレード検証ツール
  - tools/paper_verification_report.py: SQLite（ペーパートレード DB）から統計を集計して検証レポートを生成する CLI を追加。稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を算出し、閾値判定（デフォルト閾値を備え PASS/FAIL 判定）を行う。
- リサーチ（ファクター計算）
  - research/factor_research.py: DuckDB 上の prices_daily / raw_financials を用いたファクター計算モジュール（Momentum, Value, Volatility, Liquidity）を追加（モジュール設計と定数、calc_momentum の骨組みを含む）。※一部実装は今後の拡張対象。

### Changed
- パッケージ情報
  - src/kabusys/__init__.py にバージョン 0.1.0 を設定。

### Notes / 動作上の重要な挙動
- run_monitoring.py は監視用の SQLite DB に対して環境に依存せず settings.sqlite_path（本番用パス）を使用します。Monitoring をテスト環境で分離するには設定の調整が必要です。
- MONITOR_POLL_INTERVAL 環境変数の値が不正（整数でない、0 以下など）の場合は警告を出してデフォルト（60 秒）にフォールバックします。
- run_execution.py は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB とデータ分離します。
- logging_setup は標準出力を stdout に統一して出力します（stderr ではない）。ログディレクトリの作成失敗やファイルハンドラ作成失敗時はコンソール出力にフォールバックします。
- process_priority 設定は権限不足や未対応 OS の場合に安全にスキップし、警告ログを出します。
- .env 自動ロードは OS 環境変数を保護（.env の上書きを抑止）します。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- config_setup のウィザードはシークレット項目をマスクして表示し、保存前に確認プロンプトを行います（.env を絶対に Git にコミットしない旨がコメントとしてファイルに入ります）。
- validate_config は PyYAML 未インストール時に YAML の内容検証をスキップして警告を出します。--strict を付けると警告があっても exit(1) で失敗扱いになります。
- portfolio 関連の関数は副作用なし（純粋関数）でメモリ内計算を行う設計です。将来的に銘柄別単元の導入等を想定した TODO コメントがあります。

### Security
- config_setup の対話入力でシークレット（API トークン等）はマスク表示されますが、.env 自体は平文で保存されます。`.env` をリポジトリに含めない（.gitignore に追加）ことを強く推奨します（生成ファイルヘッダにも同旨を記載）。

### Known limitations / TODO
- research/factor_research.py はモジュール化・関数実装が進行中（calc_momentum の実装途中）。
- position_sizing の lot_size は現在全銘柄共通。将来的に銘柄別 lot_map を受け取る設計へ拡張予定。
- apply_sector_cap は price 欠損時にエクスポージャーが過少評価される可能性がある旨をコメントで指摘しており、前日終値や取得原価のフォールバックを検討中。

---

（以降のリリースでは、Unreleased → リリース名に移し、変更点を追記してください）