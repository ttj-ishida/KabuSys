# Changelog

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-24
初回公開リリース

### Added
- 全体
  - パッケージ初期バージョンを追加（kabusys v0.1.0）。
  - DuckDB / SQLite を利用したデータ処理基盤を統合。
  - プロジェクトルート自動検出ロジックを追加（.git または pyproject.toml を基準）。
  - 自動 .env ロード機能を追加（.env / .env.local を環境変数と衝突しない形で読み込み）。
  - 環境変数自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。

- 設定・設定管理
  - Settings クラスを実装し、環境変数からアプリケーション設定を一元取得できるようにした。
    - J-Quants / kabuステーション / LINE / DB パス / 監視・閾値等をプロパティで提供。
    - KABUSYS_ENV, LOG_LEVEL 等の値検証を実装。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）を追加。
    - paper_trading 用の専用 SQLite パス (PAPER_TRADING_SQLITE_PATH) をサポート。
  - config_setup CLI を追加し、対話式で .env を作成・更新するウィザードを提供。
    - シークレット値マスク、選択肢、デフォルト値のサポート。
    - 書き込み時に注意メッセージを付与（.env をコミットしないなど）。

- 検証
  - validate_config CLI を追加し、起動前に環境変数や config/*.yaml の整合性をチェック可能にした。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在チェックを実装。
    - PyYAML が存在する場合は config/*.yaml のパース検証を実行。
    - KABUSYS_ENV=live に対する追加のガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を追加。
    - --strict オプションで警告を失敗扱いにできる。

- 実行スクリプト
  - run_execution.py を追加（ExecutionEngine 起動スクリプト）。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading DB に記録して本番 DB と分離。
    - プロセス優先度を高（High）に設定して起動する処理を追加。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）に対応し、フラグ検知で安全に停止可能。
    - ExecutionEngine をバックグラウンドスレッドで実行し、停止フラグでエンジンを停止する制御を実装。
  - run_monitoring.py を追加（SystemMonitor ポーリングループ起動スクリプト）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用の sqlite_path を使用（環境に依存せず監視 DB を一本化）。
    - 停止フラグ検知でループを終了。KeyboardInterrupt にも対応。
    - check_once() 呼び出しで例外が発生してもログを残して次回ポーリングに継続する耐障害設計。

- ロギング / 運用
  - utils.logging_setup.setup_logging を提供。
    - コンソール出力（stdout）と日次ローテートファイル出力 (TimedRotatingFileHandler) をルートロガーに設定。
    - ログレベルとログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップし、コンソール出力のみで継続するフェールバックを実装。
  - utils.process_priority によりプラットフォーム差分を吸収してプロセス優先度（high/normal/low）と CPU affinity を設定する機能を追加。
    - Windows / POSIX(nice) の両対応。権限不足等の失敗は警告でスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates（スコア降順ソート＋タイブレークロジック）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア正規化。全スコアが0の場合は等金額にフォールバック）
  - portfolio.risk_adjustment:
    - apply_sector_cap（セクター集中制限。既存保有と当日売却予定を考慮）
    - calc_regime_multiplier（市場レジームに基づく投下資金乗数: bull/neutral/bear + 未知レジームフォールバック）
  - portfolio.position_sizing:
    - calc_position_sizes（risk_based / equal / score の割当方式対応、lot_size 単位丸め、aggregate cap によるスケーリングと残差処理）

- 研究 / 分析
  - research.factor_research モジュールを追加（ファクター計算の骨格）。
    - Momentum / Value / Volatility / Liquidity 等の計算を行う設計（DuckDB 接続を受ける）。
    - モメンタム計算等の定数定義と I/O 方針を実装（実装途中の関数あり、将来的な拡張想定）。

- ツール
  - tools.paper_verification_report を追加。
    - ペーパートレード用 SQLite から集計して報告書を生成（期間指定可）。
    - 指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、P95 レイテンシ等。
    - デフォルト閾値を定義し、PASS/FAIL を判定してコンソール出力する。

- DB/監視
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視用テーブルの存在を保証（冪等性）。
  - 実行・監視双方で DuckDB 接続を初期化して分析用 DB に書き出し可能。

### Changed
- 初期設計フェーズでのアーキテクチャ決定:
  - Paper Trading と Live を明確に分離（DB・ブローカークライアント）。
  - ログは stdout を優先して出力（cron / Task Scheduler に対する考慮）。
  - .env パースの挙動を詳細に制御（クォート・エスケープ、インラインコメント扱いの改善）。

### Fixed
- n/a（初回リリースのため既知のバグ修正は無し）。

### Deprecated
- n/a

### Removed
- n/a

### Security
- 必須環境変数が未設定の場合は validate_config でエラーを出力し、Settings._require は未設定時に ValueError を送出することで起動前に明示的に検出可能。
- .env は明示的にコミットしないよう config_setup の README コメントで注意喚起。

---

開発者向け補足:
- 一部のモジュール（例: research.factor_research）は関数実装の途中で切れている箇所があります。将来的にファクター計算ロジックの完全実装を予定しています。
- run_execution と run_monitoring は停止制御にファイルベースのフラグを使用します（data/stop_requested.flag 等）。運用環境でのフラグ管理に注意してください。