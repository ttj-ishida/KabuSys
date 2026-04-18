# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。

次のリリースはバージョン 0.1.0（初回リリース想定、コードベースから推測）です。

## [Unreleased]

（現状なし）

## [0.1.0] - 2026-04-18

### Added
- 起動スクリプトを追加 / 実装
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV による paper_trading 用 DB 分離（PAPER_TRADING_SQLITE_PATH）や MockBroker の選択を含む。停止フラグ（data/stop_requested.flag）と PID ファイル管理を備える。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。

- 設定管理
  - config.py: 環境変数・.env 自動読み込み機能を追加（プロジェクトルートを .git / pyproject.toml から検出）。.env/.env.local の優先度ルールを実装し、.env の厳密な行パース（export プレフィックス対応、クォートとバックスラッシュエスケープ、インラインコメントの取り扱い）を実装。Settings クラスを導入し、各種設定（J-Quants トークン、kabu API、DB パス、監視閾値、実行環境フラグ等）をプロパティとして提供。

- 設定支援 CLI
  - config_setup.py: 対話式ウィザードで .env を初期生成/更新する CLI を追加。シークレット項目はマスク表示、既存値の利用やデフォルト適用が可能。
  - validate_config.py: .env および config/*.yaml の整合性チェック CLI を追加。必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML のパース検査（PyYAML が導入されている場合）、本番向けガード（LINE 設定や Kill Switch の警告）等を実装。--strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、同点のタイブレーク）、等金額配分、スコア加重配分（全スコアが 0 の場合に等金額へフォールバック）を実装。
  - portfolio/position_sizing.py: position size（発注株数）計算ロジックを実装。risk_based / equal / score の割当方式、単元株丸め（lot_size）、per-position および aggregate cap の適用、cost_buffer（手数料・スリッページ見積）を考慮したスケーリングを実装。
  - portfolio/risk_adjustment.py: セクター集中上限を適用する apply_sector_cap、マーケットレジームに応じた投資乗数 calc_regime_multiplier を実装（既知のレジームは bull/neutral/bear をサポート、未知レジームはフォールバック）。

- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテート、デフォルト 30 日保持）をルートロガーに設定。既存ハンドラをクリアして二重設定を防止。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定と CPU affinity 設定のユーティリティを追加。Windows と POSIX（Linux/Mac/FreeBSD）間の差分を吸収し、権限不足時は警告して安全にスキップする。

- 監視／データベース連携
  - monitoring_db 初期化呼び出し（init_monitoring_db）や duckdb 接続の統一使用を起動スクリプトに導入（duckdb を分析用途に使用）。

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率（uptime）、注文成立率（fill rate）、送信率、リスク却下数、API レイテンシ（平均・最大・P95）を SQLite（paper_trading.db）から集計して PASS/FAIL 判定を行う。しきい値はスクリプト内で定義（稼働率 >= 99% 等）。日付フィルタ（--from / --to）、DB パスオーバーライド（--db）対応。

- 研究用モジュール
  - research/factor_research.py: DuckDB の prices_daily/raw_financials を用いたファクター計算モジュールの骨組みを追加（Momentum / Value / Volatility / Liquidity 等、設計方針と定数を記載）。（ファイルは途中まで実装されているが、検証・拡張を想定）

### Changed
- ロギング挙動の改善
  - StreamHandler を stdout にして、cron / Task Scheduler 環境での stdout/stderr リダイレクトを想定。既存ハンドラは初期化時に flush/close してから削除するよう変更し、二重ログ出力を防止。
  - ファイルハンドラ作成失敗時には明示的に警告しコンソール出力のみで継続する挙動に。

- .env 読み込みルールの明確化
  - 自動ロードのオン/オフ制御（KABUSYS_DISABLE_AUTO_ENV_LOAD）。読み込み優先度は OS 環境 > .env.local > .env。既存 OS 環境変数は保護され、.env の override 挙動を制御可能。

- Execution / Monitoring の DB 使用ポリシー
  - run_monitoring は環境にかかわらず本番 sqlite_path を使用する方針を明示。
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用し、本番 DB から完全分離する実装に。

- position sizing のスケーリング改善
  - aggregate cap 超過時のスケーリングアルゴリズムにおいて lot_size 単位での切り捨てと残余キャッシュを用いた追加配分ロジックを実装し、再現性確保のため二次キーにコードを使用する等の安定化を行った。

### Fixed / Robustness
- .env パーサの強化
  - export プレフィックス対応、クォート有り/無しの取り扱い（バックスラッシュエスケープ対応）、インラインコメントの正しい無視処理などを実装し、.env の微妙な記述にも耐えるように改善。

- process_priority と CPU affinity の障害耐性
  - 未対応 OS や権限不足時に例外を発生させず警告でスキップするようにして、起動時に致命的エラーとならないようにした。

- monitoring / execution の停止制御
  - data/stop_requested.flag を参照することで外部から安全に停止指示を与えられるようにした。ExecutionEngine のスレッド監視と graceful stop を組み込んでいる（スレッドの join とタイムアウト処理含む）。

- 設定検証の改善
  - validate_config で YAML パーサが存在しない場合でも処理継続し、パースチェックは PyYAML が存在する環境下でのみ実行するようにして依存性がない環境でも使用可能に。

### Documentation / UX
- config_setup.py のウィザードでシークレットをマスクして表示、既存値を再利用できるインタラクションを実装。保存前に確認プロンプトを表示。
- paper_verification_report の出力を見やすいテキスト形式で整形し、欠損値は "N/A" と表示するなどユーザフレンドリーな出力にしている。

### Notes / TODO (推測)
- research/factor_research.py はファクター計算ロジックの実装が途中で切れているため、完全実装とテストが必要。
- position_sizing の TODO にあるように、将来的には銘柄別の lot_size を導入する余地がある。
- apply_sector_cap の価格欠損（price が 0 の場合）の扱いは今後改善（前日終値や取得原価でのフォールバック）すると注記あり。

---

If you want, 上記 CHANGELOG をリポジトリの CHANGELOG.md に追加する用のプレーンテキストを出力します。必要な場合は追記してください。