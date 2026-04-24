# Changelog

すべての変更は Keep a Changelog の仕様に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-24

### Added
- 初回リリース: KabuSys のコアユーティリティ・CLI・ポートフォリオ・モジュール群を追加。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト直下の data/stop_requested.flag により検知。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を利用する設計。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db、環境変数で上書き可）と MockBrokerClient を使用し、本番 DB と完全分離。
    - 起動前に停止フラグを確認し、フラグがあれば起動を中止。
    - デーモンスレッドで ExecutionEngine を実行し、停止フラグ検知で安全に停止させる仕組みを提供。
    - 起動時にプロセス優先度を "high" に設定。
- 設定・環境管理
  - config.py: 環境変数読み込み／Settings クラスを追加。
    - プロジェクトルートを .git または pyproject.toml を基準に自動検出し、.env/.env.local を自動ロード（OS 環境変数優先、.env.local は .env を上書き）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパースはシングル/ダブルクォート、エスケープ、inline コメント等に対応。
    - 必須設定取得用の _require()、各種設定プロパティ（DB パス、paper_trading 用設定、監視閾値、ログレベルなど）を提供。
    - PAPER_FILL_MODE（paper trading の fill mode）に対する入力検証を実装（instant/partial/never/reject）。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 代表的な設定項目のプロンプト、既存値の再利用、シークレットマスク表示、保存機能を提供。
    - 保存後に validate_config での検証を促すメッセージを表示。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在とパース（PyYAML 利用時）を検証。
    - 本番（live）用の追加ガードチェック（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険性の警告）を実装。
    - --strict モードで警告を失敗扱いにできる機能を提供。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保管）を設定する共通ユーティリティを追加。
    - ログレベル、ログディレクトリの解決順や失敗時のフォールバック動作（ファイル出力をスキップしてコンソールのみ）を実装。
    - stdout を利用することでスケジューラ実行時のリダイレクト運用を容易に。
  - utils/process_priority.py:
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を追加。
    - Windows / POSIX 系を吸収し、権限不足や未サポート環境では警告を出して安全にスキップ。
- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選択。
    - calc_equal_weights: 等金額配分の重み計算。
    - calc_score_weights: スコア加重配分（全銘柄スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中を抑制するための候補フィルタ（売却予定銘柄はエクスポージャー計算から除外、"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知のレジームは 1.0 でフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数算出、単元株丸め、per-position 上限・aggregate cap、cost_buffer を考慮したスケーリングと端数処理を実装。
- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計し、定めた閾値に基づく PASS/FAIL 判定を出力。
    - コマンドライン引数で期間指定（--from/--to）や DB パス指定（--db）をサポート。
- データサイエンス / リサーチ
  - research/factor_research.py（骨格実装）:
    - モメンタム、ボラティリティ、バリュー等のファクター計算を行うための設計・定数群と calc_momentum の骨格を追加（DuckDB を利用して prices_daily / raw_financials を参照する設計）。
- パッケージ化
  - src/kabusys/__init__.py にバージョン 0.1.0 を追加。

### Changed
- なし（初回リリースのため変更履歴なし）。

### Fixed
- .env パーサー:
  - クォート文字内のエスケープ処理や inline コメント処理を改善し、より堅牢に読み込めるようにした（config._parse_env_line）。
- MONITOR_POLL_INTERVAL の不正値検出時にデフォルトへフォールバックし、警告ログを出す実装を run_monitoring に追加。

### Security
- 環境変数取り扱いに関する注意を README/ウィザードのコメントで明記（.env を Git にコミットしない警告）。

### Notes / その他
- 監視・実行プロセスは停止フラグ（data/stop_requested.flag）や pid ファイルを利用して外部からの制御を想定しているため、運用スクリプトやシステム管理ツールと組み合わせた安全な運用設計が推奨されます。
- Paper Trading（ペーパートレード）は本番 DB と明確に分離されるよう設計されており、検証時に実環境へ影響を与えないよう配慮されています。
- 今後の拡張として、position_sizing の lot_size を銘柄別に対応する等の改善案がコード中にコメントとして残されています。

もし特定ファイル／機能ごとにより詳細なリリースノート（例: public API、CLI の使用例、環境変数一覧）を希望される場合は、その対象を指定してください。