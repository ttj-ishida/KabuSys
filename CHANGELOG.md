# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。

## [0.1.0] - 2026-04-21

### Added
- 起動スクリプトを追加
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）検出による安全停止処理を実装。
    - Monitoring は KABUSYS_ENV に関わらず本番用の `sqlite_path` を使用する挙動を明示。
    - 例外発生時はログに例外を残して次のポーリングまで待機する耐障害性を追加。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード用の MockBrokerClient を利用し、Paper Trading 用 DB（`data/paper_trading.db` をデフォルト）で本番 DB と完全分離して動作。
    - ストップフラグ（data/stop_requested.flag）検出でエンジンを安全に停止する仕組みを実装。
    - 実行時 PID ファイル管理（data/execution.pid）に対応。
    - 起動直後にプロセス優先度を "high" に設定。

- 設定関連ユーティリティと CLI を追加
  - config.py
    - .env 自動ロード機能を追加（プロジェクトルートの `.env` と `.env.local` を読み込み）。
    - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - `.env` パース機能を強化（`export` プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなど）。
    - Settings クラスを導入し、アプリケーション設定（DB パス、KABUSYS_ENV の検証、PAPER_FILL_MODE の妥当性確認 等）を型付きプロパティで提供。
    - `settings` のインスタンスを公開。
  - config_setup.py
    - 対話式ウィザードで `.env` を作成/更新する CLI を追加（シークレット入力のマスク表示、選択肢/デフォルトのサポート、保存確認）。
  - validate_config.py
    - `.env` や config/*.yaml の事前検証ツールを追加。
    - 必須環境変数未設定、KABUSYS_ENV/LOG_LEVEL の不正値検出、DB パスの親ディレクトリ確認、YAML パース（PyYAML がある場合）などをチェック。
    - `--strict` オプションで警告を失敗扱いにできる。

- ログ・プロセス管理ユーティリティを追加
  - utils/logging_setup.py
    - ルートロガーに対する一元的なログ設定ユーティリティを追加。
    - StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler をセットする。
    - 環境変数または引数からログレベル/ログディレクトリを解決。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - マルチプラットフォーム（Windows/Linux/macOS 等）でプロセス優先度（`set_process_priority`）と CPU affinity（`set_cpu_affinity`）を設定するユーティリティを追加。
    - psutil を使い、権限不足などで失敗した場合は警告ログを出してフォールバック。

- ポートフォリオ構築関連の純粋関数群を追加（DB 非依存）
  - portfolio/portfolio_builder.py
    - シグナル選定 `select_candidates`、等分配 `calc_equal_weights`、スコア加重 `calc_score_weights` を実装。
    - スコア全体が 0 の場合は等分配にフォールバックする挙動。
  - portfolio/risk_adjustment.py
    - セクター集中の上限を適用する `apply_sector_cap` を実装（当日売却予定銘柄の除外対応、"unknown" セクターは上限適用外）。
    - 市場レジームに応じた投下資金乗数を返す `calc_regime_multiplier` を実装（bull/neutral/bear に対応、未知レジームはフォールバックして警告）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数を計算する `calc_position_sizes` を実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1銘柄上限・総投下上限（aggregate cap）・コストバッファを考慮したスケーリングロジックを実装。
    - 現在保有との比較により追加発注分のみを算出。

- Paper Trading 検証ツールを追加
  - tools/paper_verification_report.py
    - Paper Trading の SQLite DB から稼働率、注文成功率、送信率、P95 レイテンシ等の指標を集計して人間向けレポートを出力する CLI を追加。
    - 日付範囲フィルタ（--from / --to）と DB パス指定（--db または環境変数 PAPER_TRADING_SQLITE_PATH）に対応。
    - 既定の合格基準値を定義（稼働率 99% / 成立率 90% / 送信率 95% / P95 レイテンシ 200ms）。

- research/factor_research.py（ファクター計算モジュール）を追加（実装の一部を含む）
  - DuckDB 接続を受け、価格テーブル等からモメンタム等のファクターを計算する設計。calc_momentum の実装開始（定数・方針定義を含む）。

### Changed
- パッケージ初期化
  - src/kabusys/__init__.py にバージョン情報 `__version__ = "0.1.0"` を追加し、主要サブパッケージを `__all__` に列挙。

- ログ出力の標準化
  - 全起動スクリプトから `utils.logging_setup.setup_logging` を呼ぶことでログ設定を統一。

### Fixed
- .env パースの堅牢化
  - `_parse_env_line` の実装で、クォート内のバックスラッシュエスケープやインラインコメントの扱いを改善し、より多くの `.env` 形式に正しく対応。

### Notes / Breaking changes / Behavior to be aware of
- run_monitoring は常に Settings.sqlite_path（本番向けの default path）を使用し、KABUSYS_ENV に依存しません。テストや開発環境で監視用 DB を分離したい場合は環境変数 `SQLITE_PATH` を明示的に設定してください。
- .env 自動ロードが導入されました。自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で有用です）。
- process_priority / CPU affinity の設定は OS や実行権限に依存します。権限不足や未対応プラットフォームでは警告を出してスキップされます。
- Paper Trading の検証レポートは DB のスキーマ（trade_logs, system_status, risk_logs 等）に依存します。スキーマがない場合は該当指標を N/A として扱います。

### Removed
- （初期リリースのため該当なし）

### Security
- （本リリースで明示的なセキュリティ修正はなし）

---

開発・運用に関する補足や既知の改善点はドキュメントや TODO コメント内に記載しています。必要があれば項目ごとにリリースノートを詳細化します。