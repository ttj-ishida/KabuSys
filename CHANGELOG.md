# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
バージョン番号はパッケージ内の __version__（0.1.0）に基づきます。

## [0.1.0] - 2026-04-18

### Added
- 全体
  - 初期リリース。日本株自動売買システム「KabuSys」のコアユーティリティ、起動スクリプト、ポートフォリオ構築・サイズ決定ロジック、検証ツール類を導入。

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV が `paper_trading` の場合、Paper Trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - ブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、および ExecutionEngine の起動（デーモンスレッド）を実装。
    - 停止フラグ (data/stop_requested.flag) 検出時の安全停止処理、実行中 PID ファイル出力（data/execution.pid）に対応。
    - プロセス優先度を"high"に設定する処理を導入。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path（data/monitoring.db）を使用する設計。
    - 停止フラグ検知、例外発生時のロギング、KeyboardInterrupt のハンドリングを実装。

- 設定関連
  - config.py: 環境変数・設定管理モジュールを追加。  
    - プロジェクトルート自動検出（.git または pyproject.toml）により .env 自動読み込み機能を提供（.env, .env.local の順／OS 環境変数を保護）。
    - 複雑な .env パース機能を実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い）。
    - 必須キーの検査（_require）、各種設定プロパティ（DB パス、PID パス、監視閾値、PAPER_FILL_MODE バリデーション等）を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。  
    - よく使う環境変数項目の入力支援（秘密値マスク表示、選択肢、デフォルト値）。
    - .env の読み書きロジックを実装（テンプレートを出力）。
  - validate_config.py: 起動前の設定検証 CLI を追加。  
    - 必須環境変数の未設定検出、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML がある場合）を実行。
    - --strict モードで警告もエラー扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装（スコア全ゼロ時は等分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限を適用する関数を実装（当日売却予定銘柄を除外可能、unknown セクターは上限除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知のレジームは警告後 1.0 にフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method (`risk_based`, `equal`, `score`) に基づく発注株数決定ロジックを実装。
      - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、投下資金上限（max_utilization）、手数料・スリッページ見積り（cost_buffer）を考慮した aggregate cap スケーリング。
      - risk_based モードでの損切り率 stop_loss_pct を考慮したリスク許容株数計算を実装。

- 研究 / ファクター計算
  - research/factor_research.py: DuckDB を用いたモメンタム・バリュー・ボラティリティ等のファクター計算モジュールの骨格を追加（prices_daily / raw_financials テーブル参照設計）。（実装は継続）

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。  
    - システム稼働率、注文成功率（Fill）、送信率（Sent）、リスク却下数、API レイテンシ（平均/最大/P95）を算出し PASS/FAIL を判定する閾値を実装（稼働率 99%、Fill 90%、Send 95%、P95 レイテンシ 200 ms）。
    - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数）に対応。

- ユーティリティ
  - utils/logging_setup.py:
    - 共通ロギング設定ユーティリティを追加。stdout 出力（StreamHandler）および日次ローテーションのファイル出力（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py:
    - プラットフォームを透過したプロセス優先度設定（Windows の priority class / POSIX の nice 値）と CPU affinity 設定機能を追加。権限不足時は警告を出してスキップ。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

---

注記 / 既知の制限・TODO
- research/factor_research.py はファクター計算の骨組みを含むが、ファイル末尾で実装途上（コメント・未完部分）が見られます。今後の実装継続が必要です。
- position_sizing の価格フォールバックや lot_size の銘柄別対応は TODO コメントあり。将来的に stocks マスタの導入で拡張予定。
- .env パースは多数のケースに対応しているが、極端なエッジケースがある可能性があるため運用環境での検証を推奨。
- ログディレクトリ作成やプロセス優先度設定は権限や OS に依存するため、失敗時は警告を出して安全にフォールバックする設計としています。

開発者向けヒント
- 自動 .env 読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 設定検証は `python -m kabusys.validate_config` で実行できます。警告をエラー扱いにするには `--strict` を付けてください。
- Paper Trading 環境では `KABUSYS_ENV=paper_trading` を設定すると execution は paper_trading 用 DB を使用します。