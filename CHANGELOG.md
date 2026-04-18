# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
初期リリース相当の内容を、コードベースから推測して日本語でまとめています。

※ 日付はコード解析時点 (2026-04-18) を使用しています。

## [Unreleased]

### Added
- 起動スクリプトを追加 / 整備
  - run_execution.py: ExecutionEngine を起動する CLI。プロセス優先度設定、停止フラグ検知、スレッド実行、paper_trading の専用 DB (data/paper_trading.db) 利用などを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数による間隔上書き、停止フラグ検知、監視 DB 初期化を実装。

- 環境設定関連 CLI / ユーティリティ
  - config_setup.py: 対話式ウィザードで .env を初期作成 / 更新するツールを追加。シークレットマスクや選択肢、デフォルト値のサポート。
  - validate_config.py: .env および config/*.yaml を起動前に検証する CLI を追加。--strict モードで警告も失敗扱いに可能。
  - 環境管理モジュール (config.py): 
    - .env/.env.local 自動ロード（OS 環境変数を保護する protected 機構、.env.local による上書き）と KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化。
    - 高レベル Settings クラスを提供（J-Quants / kabuAPI / DB パス / paper_trading 分離 / 各種閾値など）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite DB から稼働率・注文成功率・レイテンシ等を集計してレポート（PASS/FAIL 判定）を出力するツールを追加。P95 計算や期間フィルタ、閾値が組み込まれている。

- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio.portfolio_builder: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。
  - portfolio.risk_adjustment: セクター集中度制限 (apply_sector_cap)、市場レジームに基づく乗数計算 (calc_regime_multiplier)。
  - portfolio.position_sizing: 発注株数算出（risk_based / equal / score）、単元株丸め、aggregate cap によるスケーリング、手数料/スリッページバッファ考慮。

- 共通ユーティリティ
  - utils/logging_setup.py: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定する統一ロギング設定を追加。既存ハンドラのクリア、LOG_DIR / LOG_LEVEL の解決、ログディレクトリ作成失敗時のフォールバックを実装。
  - utils/process_priority.py: Windows / POSIX の差分を吸収したプロセス優先度設定と CPU affinity 設定関数を追加（psutil 利用）。権限不足時は警告でスキップする安全設計。

- Execution モジュールとの連携点
  - BrokerClientFactory（実行時に環境に応じて MockBrokerClient を生成）や、ExecutionEngine/OrderManager/RiskManager/Reconciler/OrderRepository の組み立てを run_execution で行うようにし、paper_trading の場合は MockBroker + 専用 DB で本番 DB と完全分離する設計を採用。

- パッケージ初期バージョン情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

### Changed
- .env 読み込みの強化（config.py）
  - export KEY=val 形式をサポート。
  - クォートされた値のエスケープ処理に対応（バックスラッシュエスケープ、対応する閉じクォートまで読み取り、インラインコメントを無視）。
  - クォートなしの場合のコメント判定ルールを明確化（'#' の直前が空白/タブならコメント扱い）。
  - .env.local を .env より後に上書きする挙動、既存 OS 環境変数の保護（protected set）を実装。

- validate_config.py の挙動改善
  - PyYAML が未インストールの場合は YAML 検証をスキップして警告出力するように変更。
  - 本番環境向けのガードチェック（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険設定）を追加。

- logging_setup の挙動
  - 既存ハンドラを確実に flush/close してから削除することで二重登録を防止。
  - stdout を StreamHandler に使用（stderr ではない理由をコメントで明示）。

### Fixed
- run_monitoring.py のポーリング間隔取得ロジック強化
  - 環境変数 MONITOR_POLL_INTERVAL の不正値に対する警告とデフォルトフォールバック（負値/非数への対処）を追加。

- Execution 起動停止制御の堅牢化
  - 起動前に停止フラグをチェックして即時終了する処理、実行中の停止フラグ検出で engine.stop() を呼ぶ処理、スレッド終了待ちのタイムアウトなどを実装。

### Deprecated
- （なし・初期リリースのため該当なし）

### Removed
- （なし・初期リリースのため該当なし）

### Security
- .env ファイルに関して README 相当の注意を .env 作成ロジックに含め、.env を絶対に Git にコミットしない旨を強調。

---

## [0.1.0] - 2026-04-18

初期リリース相当。上記「Added / Changed / Fixed」の内容を含むリリース。

- 基本機能
  - 実行エンジン起動、監視ループ、環境設定ウィザード、設定検証ツール、Paper Trading 検証レポート、ポートフォリオ構築ロジック、ロギング / プロセス優先度ユーティリティなどを含む一式を公開。
- 設計方針
  - 本番 / ペーパートレード DB の分離、.env 自動ロード（必要に応じて無効化可能）、安全なデフォルト動作とエラー時のフォールバックを重視。

---

過去の変更履歴はこのファイルに追記していってください（Keep a Changelog の各セクションに従ってカテゴリ分けを行うことを推奨します）。