CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- 特になし

0.1.0 - 2026-04-19
------------------

Added
- 初回公開リリース。
- コア機能
  - Portfolio 構築パイプライン（kabusys.portfolio）
    - 銘柄選定: select_candidates（スコア降順・タイブレーク処理を実装）
    - 重み算出: calc_equal_weights / calc_score_weights（スコアが全て 0 の場合は等分配へフォールバック）
    - ポジションサイジング: calc_position_sizes（risk_based / equal / score 対応、単元株丸め、aggregate cap によるスケールダウン、コストバッファ対応）
    - リスク調整: apply_sector_cap（セクター集中制限、"unknown" セクターの扱い）、calc_regime_multiplier（レジーム乗数、未知レジームは警告してフォールバック）
  - 研究モジュール（kabusys.research）
    - factor_research: モメンタム / ボラティリティ 等のファクター計算の枠組みを実装（DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計）
  - 実行系 / 発注
    - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時はペーパートレード用 DB を使用し MockBrokerClient を利用可能（本番 DB と分離）。
    - ExecutionEngine 用のコンポーネント組立（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler）を初期実装。RiskManager の初期設定例を組み込み（max_position_pct 等）。
  - 監視
    - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視用 DB は環境に関わらず本番 sqlite_path を使用。
    - 監視 DB 初期化ユーティリティ（監視テーブルの冪等初期化）を用意。
  - ユーティリティ
    - config: 環境設定読み込み・検証モジュール。プロジェクトルート自動検出（.git / pyproject.toml 基準）・.env/.env.local の自動読み込み（OS 環境変数保護付き）を実装。値検証（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）を実装。
    - config_setup: .env の対話式ウィザード（作成・更新）を追加。既存値再利用やシークレットマスキングに対応。
    - validate_config: 起動前チェック CLI。必須環境変数、パス、config/*.yaml の存在および YAML パース（PyYAML があれば実施）を検証。--strict フラグで警告を FAIL 扱いに可能。
    - tools/paper_verification_report: ペーパートレード検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を集計し PASS/FAIL 判定を出力。期間指定・DB パス指定オプションあり。
    - logging_setup: 統一ログ設定ユーティリティを追加。stdout への StreamHandler と 日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートに設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティを追加。Windows/Linux(macOS等)の差を吸収し、権限不足や未対応 OS の場合は安全にスキップして警告を出力。
- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として設定。

Changed
- （初回リリースのため無し）

Fixed
- （初回リリースのため無し）

Removed
- （初回リリースのため無し）

Security
- sensitive な環境変数は config_setup の出力でマスク（表示時に **** を使用）して直接表示を避ける設計。.env の Git 管理禁止を README に促す文言を .env 作成処理に含める。

Notes / 実装上の注記
- .env 読み込み
  - export プレフィックス対応、引用符付き値のバックスラッシュエスケープ処理、インラインコメント処理（クォートあり・なしでの扱い差）を実装。プロジェクトルートが見つからない場合は自動ロードをスキップ。
  - 自動環境ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）。
- Logging
  - ログディレクトリ作成に失敗した場合はファイルハンドラを作らず stdout のみで動作するフェイルセーフを採用。
- process_priority/set_cpu_affinity
  - 権限不足や未対応 OS (psutil の機能が無い等) の場合は警告ログを出して処理を継続。
- Portfolio / Position sizing
  - 単元 (lot_size) による丸め処理、aggregate cap が available_cash を超えた場合のスケールダウンと端数処理（残余キャッシュで lot 単位を再配分）を実装。
  - price が欠損（0.0）の場合に一部ロジックで過少見積りになる可能性を TODO コメントで指摘。
- Risk / Regime
  - calc_regime_multiplier は未知レジームに対して警告を出し 1.0 でフォールバック。Bear レジームでは戦略上 BUY シグナルが出ない設計のため、乗数は補助的な安全弁であることを注記。
- run_execution / run_monitoring
  - 両スクリプトともプロセス優先度を最初に "high" にセットする処理を含む（set_process_priority 呼び出し）。停止制御はプロジェクトの data/stop_requested.flag（または設定されたパス）を監視して行う。
  - run_execution は paper_trading 環境時に paper_trading 用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と隔離。
- tools/paper_verification_report
  - P95 計算はメモリ内ソートによる実装。データ欠損時は N/A 表示。
  - 判定閾値はソース内定数で定義（稼働率 99.0%、注文成功率 90% 等）。

既知の制限 / 今後の改善候補
- research.factor_research の実装は途中（ファイル末尾で未完の行あり）であり、追加実装/テストが必要。
- 単元情報 (lot_size) を銘柄別に持たせる拡張（将来的な stocks マスタとの連携）が想定されている。
- position_sizing の価格欠損時のフォールバック（前日終値や取得原価など）を改善する必要あり。
- YAML パース検証は PyYAML に依存。環境により検証がスキップされる場合がある点に注意。

Contributing
------------
バグ報告・改善提案は Issue を立ててください。Pull Request は機能追加 / 修正ごとに分け、ユニットテストと簡単な説明を添えて提出してください。

License
-------
本リポジトリに含まれるコードのライセンス情報はプロジェクトルートの LICENSE を参照してください。