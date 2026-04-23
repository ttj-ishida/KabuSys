# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に従います。

## [0.1.0] - 2026-04-23
初期リリース。

### 追加
- 起動スクリプト
  - run_execution: 実行エンジン (ExecutionEngine) 起動用スクリプトを追加。プロセス優先度を最初に "high" に設定し、BrokerClientFactory 経由でブローカークライアントを生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててスレッドで ExecutionEngine を実行。停止はプロジェクト配下の data/stop_requested.flag を監視して行う。KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離する。
  - run_monitoring: システム監視ループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒、無効値はデフォルトにフォールバック）。監視は環境に関わらず本番 sqlite_path を使用し、SQLite／DuckDB 接続を確立して SystemMonitor.check_once() を定期実行する。停止フラグによりループを終了する。

- 設定・環境管理
  - config: 環境変数/.env の管理クラス Settings を追加。.env 自動読み込み（OS 環境 > .env.local > .env）や KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。.env パーサは export プレフィックス、クォート付き値内のバックスラッシュエスケープ、インラインコメントの扱い等に対応。必須値取得用の _require() を提供。PAPER_FILL_MODE のバリデーションや各種パス／閾値／実行環境判定プロパティを含む。
  - config_setup: 対話式 .env 作成ウィザードを追加。主要な環境変数項目を定義し、既存 .env 読み込みとマスク表示、保存用テンプレート出力を行う。

- 設定検証ツール
  - validate_config: .env と config/*.yaml の整合性チェック CLI を追加。必須環境変数の有無、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在確認、PyYAML があれば YAML パース検証、KABUSYS_ENV=live 時の追加ガードチェックを実施。--strict で警告を FAIL 扱いにできる。

- ロギング・プロセスユーティリティ
  - utils/logging_setup: ルートロガー向けセットアップ関数を追加。StreamHandler を stdout に出力し、TimedRotatingFileHandler（日次、30 日保持）を用いてファイル出力を行う。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。重複ハンドラを避けるため既存ハンドラをクリアする。
  - utils/process_priority: プラットフォーム差を吸収するプロセス優先度設定を追加（Windows の priority class または POSIX の nice 値を使用）。CPU affinity を最初の N コアに固定する set_cpu_affinity() も提供。権限不足や未対応 OS では警告を出してスキップする。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder: BUY シグナルの候補選定（score 降順、同点は signal_rank でタイブレーク）、等重み・スコア重みの計算関数を追加。スコア全零時は等重みへフォールバックして警告を出す。
  - portfolio/risk_adjustment: セクター集中を制限する apply_sector_cap()、市場レジームに応じた投下資金乗数 calc_regime_multiplier() を追加。regime の未知値は 1.0 にフォールバックして警告を出す。セクター "unknown" は上限適用対象外。
  - portfolio/position_sizing: ポジションサイズ決定関数 calc_position_sizes() を追加。allocation_method に "risk_based" / "equal" / "score" をサポートし、銘柄単位の上限、単元株（lot_size）の丸め、コストバッファ (cost_buffer) を考慮した aggregate cap のスケーリングと残差分の lot 単位での追加配分ロジックを実装。

- Paper Trading 向け検証ツール
  - tools/paper_verification_report: paper_trading 用 SQLite を読み、稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95レイテンシ等を集計して PASS/FAIL 判定付きレポートを生成する CLI を追加。--from／--to／--db オプションをサポート。DB 欠損やテーブル欠如に対しては適切に N/A 扱いや既定値を返す。

- リサーチ（骨組み）
  - research/factor_research: ファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity の設計方針を記載）。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。calc_momentum の実装開始（定数・方針の定義あり）。

- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として設定。

### 変更
- なし（初回リリースのため）。

### 修正
- なし（初回リリースのため）。

### 注意事項 / 実装上の挙動
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行うため、カレントワーキングディレクトリに依存しない。
- MONITOR_POLL_INTERVAL の不正値（数値でない、0 以下など）はログ警告の上デフォルト値（60 秒）にフォールバックする。
- run_monitoring は監視 DB に対して常に Settings.sqlite_path（本番パス）を使用する設計。run_execution は KABUSYS_ENV が paper_trading の場合に専用の paper_sqlite_path を使用して本番 DB と分離する。
- ログは標準出力（stdout）へ出力するため、cron や Task Scheduler などで stdout/stderr を一本化して扱いやすい。
- process_priority / set_cpu_affinity は権限が不足する環境や未サポート OS 上では警告を出して安全にスキップする。

### 既知の制限 / TODO（将来の改善候補）
- position_sizing: lot_size を銘柄別に扱う拡張（stocks マスタからの読込）を想定しているが未実装。
- risk_adjustment: price が欠損（0.0）の場合にエクスポージャーが過少評価される可能性があるため、将来的にフォールバック価格（前日終値等）の導入を検討。
- research/factor_research: モジュールは方針・定数の整備済みだが、各ファクターの完全な実装とユニットテストの整備が必要。

---

（注）この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートに反映する際は、コミット履歴やリリース作業記録と照合してください。