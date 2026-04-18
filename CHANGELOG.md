CHANGELOG
=========

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

- なし（現時点でリリース済みの変更点は下記 0.1.0 に含まれます）

[0.1.0] - 2026-04-18
-------------------

Added
- 基本アーキテクチャと起動スクリプトを追加
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境に応じて本番 / ペーパートレード用の DB を切り替え、BrokerClientFactory を用いて実際のブローカークライアント／モックを生成する。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag により制御。
- 設定管理と初期化ツール
  - config.py: .env 自動読み込み（プロジェクトルート検出）と Settings クラスを追加。各種環境変数（J-Quants、kabuAPI、DB パス、監視閾値、環境種別など）をプロパティとして提供。
    - .env、.env.local の読み込み順序を実装（OS 環境変数を保護して上書き抑止）。
    - 複雑な .env 行（export プレフィックス、クォート、エスケープ、インラインコメント）に対するパースロジックを実装。
  - config_setup.py: 対話式ウィザードで .env を作成／更新する CLI を追加。
  - validate_config.py: 起動前チェック CLI を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在や YAML パースを検証。--strict で警告を FAIL 扱いにするオプションを提供。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのソート／上位 N 選定。
    - calc_equal_weights / calc_score_weights: 等金額配分／スコア加重配分を実装（スコア全0 の場合は等配分にフォールバックして警告）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中禁止ロジック（既存保有を考慮して新規候補除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）と未知レジームのフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: risk_based / equal / score の複数配分方式を実装。単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer を使った保守見積り、残差の再配分ロジックなどを実装。
- 実行時ユーティリティ
  - utils.logging_setup: 統一的なログ設定ユーティリティを追加。stdout ストリームハンドラと日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時にはファイル出力をスキップしてコンソール出力のみ継続。
  - utils.process_priority: psutil を使ったプロセス優先度設定 + CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分を吸収し、権限や未対応環境では警告を出してスキップする。
- Paper Trading 向け検証ツール
  - tools.paper_verification_report: ペーパートレード SQLite（デフォルト data/paper_trading.db）を読み、稼働率・注文成功率・送信率・レイテンシ（P95 など）やリスク却下数を集計してレポートを出力する CLI を追加。判定閾値を定義（例: 稼働率 >= 99%、P95 <= 200ms 等）。
- DuckDB 連携
  - 複数箇所で DuckDB 接続をサポート（分析用データベース統合）。
- パッケージメタ
  - __init__.py にバージョン __version__ = "0.1.0" を設定。

Changed
- なし（初期リリース）

Fixed
- 起動時やランタイムの堅牢性改善
  - logging_setup: ログディレクトリ作成に失敗した場合はファイルハンドラを作成せず、標準出力のみで継続するように変更（エラー時に標準エラーへ警告を出力）。
  - process_priority: 未対応 OS・権限エラー・psutil の例外を捕捉して警告を出し、起動を止めない挙動に。
  - run_monitoring: MONITOR_POLL_INTERVAL が不正（数値以外や 0 以下）の場合はデフォルト 60 秒にフォールバックして警告を出力。
  - run_execution/run_monitoring: 停止フラグ（data/stop_requested.flag）検知による安全停止を実装。起動直後に停止フラグが立っている場合は起動を中止する扱いを実装。
  - config._load_env_file: .env 読み込みで OS 環境変数を保護する仕組みを導入（protected set）。.env.local は既存 OS 環境の上書き（ただし protected キーは除く）。
  - calc_score_weights, calc_regime_multiplier 等で不整合時に警告を出してフォールバックするように。

Security
- なし（特にセキュリティ修正は今回の差分からは見受けられません）
- 注意: .env は絶対に Git にコミットしない旨を config_setup のヘッダに明記

Notes / Migration
- Paper Trading と本番 DB は明確に分離
  - run_execution は KABUSYS_ENV=paper_trading 時に settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、ペーパートレード用の MockBroker と合わせて本番 DB と完全分離される設計です。運用時は環境変数 PAPER_TRADING_SQLITE_PATH でパスを指定できます。
- 監視（monitoring）は環境にかかわらず Settings.sqlite_path（監視用 DB）を使用する実装になっています。運用上必要であれば設定を確認してください。
- .env 自動読み込みはプロジェクトルートが検出できない場合や環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されている場合はスキップされます。
- PAPER_FILL_MODE（instant|partial|never|reject）のバリデーションが設定されています。無効値は ValueError を発生させます。

Acknowledgements / TODO
- factor_research モジュールはモメンタム等ファクタ計算の実装が開始されていますが、一部（ファイル末尾で途中切れ）で未完の箇所があります。今後のリリースで完全実装・テスト追加が期待されます。
- position_sizing の price 欠損時のフォールバック（前日終値や取得原価の利用）は TODO コメントとして残されています。将来的な改善ポイントです。