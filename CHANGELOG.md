# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。

## [0.1.0] - 2026-04-19

初回リリース。日本株自動売買システム「KabuSys」のコアユーティリティ、CLI、ポートフォリオ構築ロジック、および検証ツールを追加します。

### 追加 (Added)
- 実行スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）検知でループを終了。
    - 監視は KABUSYS_ENV に関係なく本番用 `sqlite_path` を使用。
    - 関連ファイル: src/kabusys/run_monitoring.py
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient と専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - 停止フラグ / PID ファイル管理（data/stop_requested.flag, data/execution.pid）。
    - スレッドで ExecutionEngine をバックグラウンド実行し、停止フラグで安全停止。
    - 関連ファイル: src/kabusys/run_execution.py

- 設定・環境管理
  - Settings クラスを追加。環境変数から各種設定を取得（DB パス、各種閾値、API トークン等）。
    - `PAPER_FILL_MODE`（instant/partial/never/reject）の検証を実施。
    - `is_live`, `is_paper`, `is_dev` の判定プロパティを提供。
    - 関連ファイル: src/kabusys/config.py
  - 自動 .env ロード機能
    - プロジェクトルート（.git または pyproject.toml）を基に `.env` / `.env.local` を自動読み込み（OS 環境変数優先、上書き保護あり）。
    - `.env` パーサは export プレフィックス、クォート文字列、インラインコメントなどを考慮して読み込み。
    - 関連ファイル: src/kabusys/config.py

- 設定支援・検証 CLI
  - config_setup: 対話式ウィザードで `.env` を生成・更新する CLI を追加。
    - 必須項目やデフォルト値、シークレットマスク表示等に対応。
    - 関連ファイル: src/kabusys/config_setup.py
  - validate_config: 起動前に .env と config/*.yaml の基本的な検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML がある場合）。
    - `--strict` オプションで警告を失敗扱いにできる。
    - 関連ファイル: src/kabusys/validate_config.py

- ロギング / プロセス管理ユーティリティ
  - logging_setup: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定するユーティリティを追加。
    - LOG_DIR 環境変数や引数でログ保存先を変更可能。ディレクトリ作成失敗時はファイル出力をフォールバックで無効化。
    - 関連ファイル: src/kabusys/utils/logging_setup.py
  - process_priority: Windows / POSIX の差を吸収してプロセス優先度設定（high/normal/low）と CPU affinity 固定を提供。
    - 権限不足や未対応 OS の場合は安全にスキップして警告出力。
    - 関連ファイル: src/kabusys/utils/process_priority.py

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio_builder:
    - select_candidates: スコア降順で候補選択（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）。
    - 関連ファイル: src/kabusys/portfolio/portfolio_builder.py
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存ポジションのセクター露出を基に候補を除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear, 未知はフォールバック）。
    - 関連ファイル: src/kabusys/portfolio/risk_adjustment.py
  - position_sizing:
    - calc_position_sizes: allocation_method (= risk_based / equal / score) に基づく発注株数計算、lot_size 丸め、コストバッファ考慮、aggregate cap によるスケールダウンと端数処理ロジック。
    - 関連ファイル: src/kabusys/portfolio/position_sizing.py
  - 上記をエクスポートするパッケージ初期化を追加。
    - 関連ファイル: src/kabusys/portfolio/__init__.py

- リサーチ（未完の一部を含む）
  - factor_research: DuckDB 接続を利用したモメンタム等のファクター計算モジュールを追加（設計と一部実装）。
    - 関連ファイル: src/kabusys/research/factor_research.py

- ツール
  - paper_verification_report: Paper Trading 用 SQLite DB を読み取り、稼働率・注文成功率・送信率・レイテンシ（P95 など）を集計してレポートを生成する CLI を追加。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。
    - Pass/Fail しきい値や P95 算出ロジックを実装。
    - 関連ファイル: src/kabusys/tools/paper_verification_report.py

- パッケージメタ
  - パッケージバージョンを 0.1.0 に設定。
    - 関連ファイル: src/kabusys/__init__.py

### 変更 (Changed)
- ログ出力の標準化：
  - すべての起動スクリプトとユーティリティは setup_logging() を利用して統一的にログを設定するように構成。
  - コンソール出力は stdout を使用（cron 等でのリダイレクト運用を想定）。
  - 関連ファイル: src/kabusys/utils/logging_setup.py, 各起動スクリプト

### 修正 (Fixed)
- 環境ファイル読み込みの堅牢化：
  - .env のクォートやエスケープ、コメントの扱いを改善。`export` プレフィックス対応。
  - `.env.local` を優先的に上書きするロード順を採用し、OS 環境変数は保護されるように修正。
  - 関連ファイル: src/kabusys/config.py

### 既知の制限 (Known issues)
- factor_research モジュールは設計に基づく実装が一部存在しますが、完全なテスト・最適化は今後の作業予定です（prices_daily / raw_financials テーブルに依存）。
- position_sizing の価格欠損時のフォールバック（price = 0.0 の取り扱い）については TODO コメントが残っており、将来的に前日終値等のフォールバックロジックを追加予定。
- 一部の機能は psutil（プロセス優先度 / CPU affinity）や PyYAML（validate_config の YAML 検証）に依存します。これらが利用できない環境では機能の一部が警告を出してフォールバックします。

---

今後の予定
- factor_research の完全実装とユニットテスト整備
- ExecutionEngine / BrokerClient のインターフェース拡充とモック実装のドキュメント化
- 監視・アラート（LINE）連携の強化と本番運用用の運用ドキュメント整備

--- 

（注）実際の変更詳細は各ソースファイルのドキュメント文字列とコメントを参照してください。