# Changelog

すべての変更は Keep a Changelog のフォーマットに従い、セマンティック バージョニングを採用しています。
このファイルでは主にコードベースから推測される追加機能・改善点・注意点を記載しています。

リリース日: 2026-04-22

## [Unreleased]
- （現在未リリースの変更はありません）

## [0.1.0] - 2026-04-22
初期リリース。日本株自動売買システム「KabuSys」のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、各種 CLI ツール群を含みます。

### Added
- 基本情報
  - パッケージバージョンを src/kabusys/__init__.py にて `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用の SQLite パス（Settings.sqlite_path）を使用。
    - stop フラグ（data/stop_requested.flag）を検知してクリーンに停止。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の SQLite(DB) を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（paper/live 切替想定）。
    - エンジンは別スレッドで実行し、停止フラグにより停止可能（data/stop_requested.flag）。
    - PID ファイル管理（data/execution.pid）に対応。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - src/kabusys/config.py
    - .env ファイルの自動読み込み（プロジェクトルートに基づく。OS 環境変数は優先）。
    - .env のパース機能を実装（コメント、クォート、export 形式、エスケープシーケンス対応）。
    - Settings クラスを実装し、アプリケーションで使用する各種設定値（J-Quants、kabu API、DB パス、監視閾値、環境判定など）をプロパティとして提供。
    - 環境名やログレベル等の妥当性チェックを実施。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能。

- 設定支援・検証 CLI
  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI を追加。
    - 入力のデフォルト、隠蔽（シークレット）、選択肢、確認プロンプト等を実装。
    - .env の既存値読み込みと上書きサポート、最終的に .env を安全に書き出す機能を提供。
  - validate_config.py
    - 起動前の設定検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL 確認、DB パス（親ディレクトリの存在確認）、config/*.yaml の存在確認と（PyYAML があれば）パースチェック、本番環境向けの追加ガードを実装。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - 統一ロギング設定ユーティリティを追加。
    - stdout（StreamHandler）と日次ローテート（TimedRotatingFileHandler、30日保持）をルートロガーへ設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - LOG_LEVEL / LOG_DIR の環境変数や引数での上書きに対応。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定を追加。
    - CPU affinity 設定関数も提供。
    - 権限不足時には警告を出しスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - 候補選定（score 降順・同点は signal_rank）select_candidates。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコア 0 の場合は等分配にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有のセクター比率が閾値を超えている場合に新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマップ、未知レジームは警告の上 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - position sizing ロジックを追加。
    - allocation_method による株数計算（"risk_based" / "equal" / "score"）。
    - 損切り率・リスク許容度に基づく risk_based、lot_size（単元）丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケールダウン）を実装。
    - cost_buffer による保守的なコスト見積もり、残余配分のための端数処理ロジックも実装。

- 研究モジュール（ファクター算出）
  - research/factor_research.py
    - Momentum, Value, Volatility, Liquidity 等のファクターを計算するための設計と一部実装（モメンタム計算の方針、定数定義）。DuckDB を用いた prices_daily/raw_financials 参照を想定。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py
    - paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数等。
    - 指標に対する閾値を設定し、PASS/FAIL 判定を行う。
    - 日付フィルタ（--from / --to）と DB パス指定（--db）に対応。

- 監視 DB 初期化ユーティリティ（参照）
  - monitoring.monitoring_db.init_monitoring_db を run_script から呼び出して監視テーブルの冪等初期化を保証。

- Execution 周りのコンポーネント組立て（参照）
  - execution 側のコンポーネント（BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager, Reconciler）を組み合わせて実行可能な起動フローを実装している（詳細は各モジュールを参照）。

### Changed
- N/A（初期リリースにつき変更履歴なし）

### Fixed
- N/A（初期リリースにつき修正履歴なし）

### Notes / Known limitations
- research/factor_research.py のモメンタム計算実装はファイル末尾が途中で切れている（未完の可能性あり）。実際の利用前に関数実装の完了が必要。
- apply_sector_cap は price_map に価格が欠損（0.0）の場合にエクスポージャーが過少見積りされる旨の TODO コメントが存在。将来的に価格フォールバックの実装を検討。
- process_priority, set_cpu_affinity 等は権限不足や非対応 OS の場合に例外を出さず警告でスキップする設計になっているため、期待どおりに優先度が設定されない可能性あり。
- .env 自動読み込みはプロジェクトルートの検出に依存。配布後や特殊環境では自動ロードがスキップされる場合がある。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定。
- run_monitoring は「監視は環境にかかわらず本番 sqlite_path を使用する」と明示しているため、開発・テスト時は意図せず本番 DB を参照しないよう注意が必要。

### Security
- シークレット値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE tokens 等）は .env に保存する設計だが .env は絶対に Git にコミットしない旨の注意書きを config_setup.py に記載。

---

（補足）
- より詳細な変更／設計意図は各ソースファイルのドキュメント文字列およびコメントを参照してください。追加の修正や機能要望があれば教えてください。