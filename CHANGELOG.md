# CHANGELOG

すべての重要な変更はこのファイルに記載します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- バージョンごとに「Added / Changed / Fixed / Deprecated / Removed / Security」セクションで記載しています。
- 日付はリリース日を示します。

なお、以下の内容はソースコードから推測して作成した要約です（実装上の注意点や挙動の説明を含みます）。

## [Unreleased]

（現在未リリースの変更はありません）

---

## [0.1.0] - 2026-04-19

初回公開リリース。システムの実行スクリプト、設定管理、監視、ペーパートレード検証、ポートフォリオ構築ユーティリティ、ログ・プロセス制御ユーティリティ等を含む基本機能を実装しました。

### Added
- 基本パッケージ情報
  - kabusys パッケージを追加。バージョンは 0.1.0。

- 実行／監視エントリポイント
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成。
    - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag を監視して安全に停止可能。
    - 実行中の PID を data/execution.pid に書き込む（pid_file パス指定可）。
    - RiskManager のデフォルト設定を含めた依存コンポーネントの組み立てを実装。
  - run_monitoring.py
    - SystemMonitor（監視）起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用して監視データを記録。
    - 停止フラグ（data/stop_requested.flag）によりループを終了。

- 設定管理およびウィザード / 検証ツール
  - config.py
    - 環境変数/ .env 自動ロード機能を提供（.env / .env.local のロード順序・上書き制御）。
    - _find_project_root により .git または pyproject.toml を起点としてプロジェクトルートを探索（CWD 非依存）。
    - 複雑な .env 行パーサー実装（export 形式、クォート文字列、インラインコメント処理等）。
    - Settings クラスで各種設定プロパティを提供（検証付き: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途）。
  - config_setup.py
    - 対話式に .env を作成／更新するウィザードを実装。各設定項目の説明、デフォルト値、シークレットマスク表示、保存の確認機能を備える。
  - validate_config.py
    - 起動前に環境変数と config/*.yaml の基本的な検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスや config YAML の存在とパース検証、ライブ環境向けの追加注意喚起等を実施。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション）を設定する共通セットアップを追加。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続するフォールバック実装。
    - stdout を用いることで cron 等でのリダイレクト運用を考慮。
  - utils/process_priority.py
    - Windows/Linux/macOS 間の差を吸収するプロセス優先度設定ユーティリティを追加。
    - set_process_priority(level) で "high" / "normal" / "low" をサポート（Windows の優先度定数 / POSIX の nice 値を内部解決）。
    - set_cpu_affinity(cpu_count) でカレントプロセスの CPU affinity を設定（利用できない環境では警告を出してスキップ）。

- 監視・モニタリング基盤
  - monitoring モジュールと init_monitoring_db 呼び出しにより、監視用の SQLite テーブル初期化を起動スクリプト側で保証。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から指標を抽出し、期間フィルタ (--from / --to) に基づく検証レポートを標準出力に生成。
    - 指標: 稼働率（uptime）, 注文成功率（fill_rate）, 送信率（send_rate）, レイテンシ（avg / max / P95）等。
    - P95 計算ユーティリティ、日付フィルタの ISO8601 UTC 変換、欠損テーブルに対する柔軟なフォールバックを実装。
    - レポートに合否判定（PASS/FAIL）と閾値（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200ms）を組み込み。

- ポートフォリオ構築／リスク管理ライブラリ（pure functions）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順（同点は signal_rank 昇順）で候補選定。
    - calc_equal_weights, calc_score_weights: 重み計算（スコア合計が 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存ポジションのエクスポージャー計算、"unknown" セクターは上限除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear、未知は 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注株数計算。
    - lot_size 単位で丸め、per-position 上限・aggregate キャップ、コストバッファ反映、スケーリング時の端数処理（再現性考慮）を実装。

- 研究（research）モジュール（開始）
  - research/factor_research.py
    - DuckDB 経由でのファクター計算フレームワーク（Momentum / Value / Volatility / Liquidity）を導入する構成を追加（関数 docstring と定数を定義）。
    - モメンタム計算 calc_momentum の雛形を追加（未完の可能性あり：ソース末尾で切れている）。

- パッケージエクスポート
  - portfolio モジュールの公開 API (__all__) を設定。

### Changed
- ログ出力仕様
  - ロガーの設定で StreamHandler を stdout に固定し、cron 等との互換性を考慮した出力仕様になっています。

### Fixed
- .env 読み込みの堅牢化
  - export 構文やクォート内のエスケープ、インラインコメントの扱いなどを考慮したパーサー実装により、.env の読み込み誤動作を軽減。

### Notes / Behavioural details
- 設定の自動ロードはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できる。自動ロードはプロジェクトルートの検出に依存する（.git または pyproject.toml が存在しない場合はスキップ）。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値（0/負数/非整数）を検知するとデフォルトの 60 秒にフォールバックし、警告ログを出力する。
- process_priority / set_cpu_affinity は権限不足や未サポート OS の場合に警告を出して処理をスキップする設計。
- Paper Trading（ペーパートレード）は本番口座と完全に分離された SQLite を用いることで実運用の安全性を確保。
- 一部モジュール（例: research/factor_research.py）の関数実装が未完の可能性があるため、実運用前に追加の確認／テストが必要。

---

今後の予定（例）
- factor_research の完全実装とユニットテスト追加。
- ExecutionEngine / RiskManager / Broker クライアントの統合テスト拡充。
- config の型チェックとドキュメント強化。
- CLI ユーティリティのインストール時エントリポイント追加。

--- 

（追記: 本 CHANGELOG は提供されたソースコード内容から推測して作成しています。実際のリリースノートや内部用メモと差異がある場合は、必要に応じて修正してください。）