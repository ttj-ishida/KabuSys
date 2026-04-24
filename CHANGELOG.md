# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
日付はリリース日または推定日です（コードベースから推測して記載）。

なお、本 CHANGELOG はソースコードから機能や設計意図を推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-24
初回公開（推定）。以下の主要コンポーネントと機能を実装。

### Added
- 全体
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
  - 標準的なロギング設定ユーティリティを追加（kabusys.utils.logging_setup）。
    - stdout 出力用 StreamHandler と日次ローテーションの TimedRotatingFileHandler（30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決ロジックを実装。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows / POSIX（Linux, macOS, FreeBSD）に対応。
    - set_process_priority(level) / set_cpu_affinity(cpu_count) を提供。
  - 環境設定管理モジュールを追加（kabusys.config）。
    - .env / .env.local の自動読み込み（プロジェクトルート検出）。自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD あり。
    - 各種設定プロパティ（DBパス、APIトークン、KABUSYS_ENV、ログレベル、監視しきい値等）を提供。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
  - .env を対話的に生成・更新するウィザード CLI を追加（kabusys.config_setup）。
    - 必須項目（J-Quants, kabu API など）やデフォルト値、説明を含む対話形式。
    - 保存前の確認と .env の書き出しを実装。
  - 起動前に設定不備を検出する検証ツールを追加（kabusys.validate_config）。
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DBパスの親ディレクトリチェック、config/*.yaml の存在・パース検証（PyYAML が利用可能な場合）。
    - --strict オプションで警告を FAIL 扱いにできる。
  - 実行用スクリプトを追加
    - 実行エンジン起動スクリプト（kabusys/run_execution.py）
      - ExecutionEngine を構築してバックグラウンドスレッドで run_session を実行。
      - BrokerClientFactory によるブローカークライアント生成。KABUSYS_ENV=paper_trading 時は専用の paper DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
      - 停止フラグ（data/stop_requested.flag）検出により安全終了。PID ファイルの取り扱い。
      - 起動時にプロセス優先度を high に設定。
      - RiskManager / OrderManager / Reconciler 等の組み立てロジックを実装。RiskConfig のデフォルト値を設定し、初期ポートフォリオ値を broker.get_available_cash() で取得。
    - 監視ポーリング起動スクリプト（kabusys/run_monitoring.py）
      - SystemMonitor を用いたポーリングループを実装。デフォルトポーリング間隔 60 秒（環境変数 MONITOR_POLL_INTERVAL で上書き可能）。
      - 監視は環境にかかわらず本番 sqlite_path（settings.sqlite_path）を使用する設計。
      - 停止フラグ検出および KeyboardInterrupt による終了処理、DB接続のクローズを実装。
  - 監視用 DB 初期化ユーティリティ参照（kabusys.monitoring.monitoring_db を使用している箇所がある）。
  - Paper Trading 検証レポート生成ツールを追加（kabusys.tools.paper_verification_report）。
    - 指定期間（--from, --to）または DB 全体に対して、稼働率、注文成功率、送信率、リスク却下数、APIレイテンシ（avg/max/P95）などを計算して標準出力にレポートを出力。
    - デフォルト DB パス: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能）。
    - 判定基準（閾値）:
      - 稼働率 >= 99.0%
      - 注文成功率（fill_rate） >= 90.0%
      - 送信率（send_rate） >= 95.0%
      - P95 レイテンシ <= 200 ms
  - ポートフォリオ構築ライブラリを追加（kabusys.portfolio パッケージ）
    - portfolio_builder: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。スコアが全て 0 の場合は等配分にフォールバックして警告を出す。
    - risk_adjustment: セクター集中上限の適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）（"bull","neutral","bear" をマッピング、未知レジームはフォールバックして 1.0）。
    - position_sizing: allocation_method（risk_based / equal / score）に基づく発注株数計算（単元株丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap のスケーリング等）。lot_size（デフォルト 100）対応、手数料スリッページを cost_buffer で考慮。
  - 研究用ファクター計算モジュールを追加（kabusys.research.factor_research）
    - Momentum, Value, Volatility, Liquidity 等のファクターを DuckDB の prices_daily / raw_financials テーブルから計算する設計（calc_momentum 等の関数が存在）。
    - 時間窓や定数（MA200, ATR など）を定義。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 機密値（J-Quants トークン、kabu API パスワード、LINE トークン）は .env に格納する設計。config_setup では入力をマスク表示して扱うことを明示。

### Notes / Known limitations / TODO（コード内コメントより）
- config の自動読み込みはプロジェクトルートの検出に依存する（.git または pyproject.toml）。見つからない場合は自動読み込みをスキップする。
- risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）の場合、エクスポージャーが過少見積りされ除外が適切に働かない可能性あり。将来的に前日終値や取得原価でのフォールバックを想定。
- position_sizing:
  - 個別銘柄ごとの lot_size を扱う拡張は未実装（TODO コメントあり）。
- research.factor_research モジュールはファイル末尾が途中で切れている（実装継続が必要な箇所あり）。
- ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続する堅牢設計。
- process_priority / set_cpu_affinity は権限不足や未対応 OS の場合に安全にスキップする処理が入っている。

---

今後のリリースでは以下を想定:
- 研究モジュールの完成（ファクター計算関数の実装完了、テスト追加）
- ExecutionEngine / SystemMonitor の具体的実装詳細（ここでは起動・連携部分が確認できるが、内部ロジックは別モジュール）
- テスト（ユニット・統合）、CI 設定、パッケージング・ドキュメントの追加

もし特定ファイルごとにより詳細な変更点（行単位の差分推定など）を希望される場合は、その旨を教えてください。コードを参照してより granular な CHANGELOG を生成します。