# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
このプロジェクトの初回リリースを 0.1.0 として記録します。

## [0.1.0] - 2026-04-25

### 追加
- 基本アプリケーションパッケージを追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)

- 実行・監視用起動スクリプト
  - run_execution: ExecutionEngine 起動ルーチンを提供。プロセス優先度設定、DB 接続（paper_trading 時は専用 DB を使用）、Broker クライアント生成、OrderManager／RiskManager／Reconciler の組み立て、スレッドでのセッション実行・停止監視を実装（src/kabusys/run_execution.py）。
  - run_monitoring: SystemMonitor のポーリングループを提供。MONITOR_POLL_INTERVAL によるポーリング間隔上書き、停止フラグ検知、例外ハンドリングを実装（src/kabusys/run_monitoring.py）。

- 環境設定関連 CLI / ユーティリティ
  - config_setup: 対話式ウィザードで .env の初期作成／更新をサポート（src/kabusys/config_setup.py）。
  - validate_config: .env および config/*.yaml の起動前検証ツール（--strict オプションあり）。YAML 未インストール時はパース検証をスキップして警告を出力（src/kabusys/validate_config.py）。
  - Settings クラス（src/kabusys/config.py）: 環境変数読み込みラッパー、.env 自動ロード（.env / .env.local、OS 環境変数保護）、各種設定プロパティ（DB パス、PID パス、閾値、paper_trading 用設定等）を提供。

- ログ・プロセス制御ユーティリティ
  - logging_setup: stdout への StreamHandler と 日次ローテートの TimedRotatingFileHandler をルートロガーに統一的に設定。既存ハンドラの二重設定防止、LOG_DIR の作成失敗に対するフォールバックを実装（src/kabusys/utils/logging_setup.py）。
  - process_priority: psutil を用いたクロスプラットフォームのプロセス優先度設定（Windows/Linux/Mac 等対応）と CPU affinity 設定ユーティリティを提供（src/kabusys/utils/process_priority.py）。

- ポートフォリオ構築（純粋関数群、DB 非依存）
  - portfolio_builder: シグナル選定・重み計算（等金額、スコア加重）を実装（src/kabusys/portfolio/portfolio_builder.py）。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームによる投下資金乗数（calc_regime_multiplier）を実装（src/kabusys/portfolio/risk_adjustment.py）。
  - position_sizing: 発注株数計算（risk_based / equal / score）、単元株丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した配分ロジックを実装（src/kabusys/portfolio/position_sizing.py）。
  - portfolio パッケージのエクスポートを整備（src/kabusys/portfolio/__init__.py）。

- 研究用ファクター計算（初期骨組み）
  - research/factor_research: DuckDB を用いたファクター計算モジュール（モメンタム・MA・ATR 等を想定した設計文書に基づく実装方針の骨組みを含む）。（src/kabusys/research/factor_research.py）
    - （注）ファイルは実装途中の部分があるため、今後の拡張を想定。

- ペーパートレード検証ツール
  - tools/paper_verification_report: Paper Trading の検証レポート生成スクリプト。システム稼働率、注文成功率、送信率、レイテンシ指標(P95 等) を算出し PASS/FAIL 判定を出力（src/kabusys/tools/paper_verification_report.py）。
    - 日付フィルタ、P95 計算、DB 存在チェック、テーブル欠損時のフォールバックを実装。

- 監視 DB 初期化ユーティリティ呼び出しポイントの用意
  - run系スクリプトから init_monitoring_db を呼び、監視テーブルの存在を保証（冪等）。

### 変更（設計・挙動）
- .env 読み込み挙動の改善（src/kabusys/config.py）
  - プロジェクトルートの自動検出を __file__ ベースで行い、CWD に依存しないように。
  - .env のパースを堅牢化（export ワード対応、クォート内のバックスラッシュエスケープ対応、インラインコメント処理、空行・コメント行の無視）。
  - 自動ロードの保護: OS 環境変数は protected として .env.local の上書きを防止できる（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化も可能）。

- run_monitoring の監視ループ
  - MONITOR_POLL_INTERVAL 環境変数からポーリング間隔を取得。無効値や 0 以下の場合はデフォルト 60 秒にフォールバックして警告を出力（src/kabusys/run_monitoring.py）。
  - 監視では KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨の挙動を明記。

- run_execution の DB 接続
  - KABUSYS_ENV=paper_trading の場合、paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用して本番データと完全分離するよう実装。

- logging_setup の仕様
  - 出力先ストリームに stdout を採用（cron 等で stdout/stderr を一本化する運用に配慮）。
  - 既存ハンドラを閉じてから再設定することで二重ログ出力を防止。
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。

- process_priority の堅牢化
  - プラットフォームごとの実装差異を吸収（Windows 用定数を getattr でフェールバック、POSIX の nice 値を利用）。
  - 設定失敗時は警告ログを出してスキップする。

- position_sizing の投資スケール処理
  - aggregate cap（利用可能現金を超えた場合）のためのスケーリングと残差処理（lot_size 単位での再配分）を追加。cost_buffer を導入して手数料/スリッページを保守的に見積もる。

### 修正（バグ修正・安定化）
- run_execution / run_monitoring の停止制御
  - プロジェクト内 data/stop_requested.flag による外部停止フラグ検出を実装し、安全にループ／スレッドを終了する処理を追加（両ファイル）。

- validate_config の出力改善
  - 必須環境変数の未設定/プレースホルダ値チェック、パスの親ディレクトリ存在チェック、KABUSYS_ENV=live 時の追加ガード（LINE 送信設定や Kill フラグの設定）などを追加して起動前検証を強化。

- paper_verification_report の堅牢化
  - テーブルが存在しない場合でも sqlite3.OperationalError をキャッチしてレポートを生成できるようにし、データ欠落時は N/A 表示するよう調整。

### ドキュメント/注意事項
- .env ファイルは絶対に Git にコミットしない旨を config_setup の生成コメントに明記。
- config_setup ではシークレット項目を表示時にマスクし、既存値の再利用をサポート。
- Settings のいくつかのプロパティ（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）は不正値を弾くバリデーションを導入。

### 今後の予定 / 既知の制約
- research/factor_research はファクター計算ロジックの実装が途中の箇所があり、完成・テストを継続予定。
- position_sizing の価格欠損（price=0.0）の取り扱いに関して TODO コメントあり。前日終値等でのフォールバックを将来的に検討。
- 一部モジュールは外部依存（psutil、duckdb、PyYAML）が必要。依存がない環境では機能制限や警告が発生する旨を注意。

---

初回リリース: 基本的な自動売買システムの骨組み（実行／監視／設定／ポートフォリオ構築／検証ツール／ユーティリティ）を実装しました。今後は各コンポーネントの詳細実装・単体テスト・統合テストおよびドキュメントの充実を進めます。