# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このファイルでは、コードベースから推測できる機能追加・改善点・修正点をまとめています。

フォーマット: [Unreleased] → 今後の変更 / 開発中、
各リリースはバージョンタグと日付（YYYY-MM-DD）を付記しています。

なお、内容はソースコードから推測したものであり、実際のコミット履歴とは異なる場合があります。

## [Unreleased]

- ドキュメント化・テスト用の小改善やログ出力の微調整などの軽微な更新を想定。

---

## [0.1.0] - 2026-04-18

### 追加
- 基本アプリケーションパッケージを追加（kabusys v0.1.0）。
  - ファイル: src/kabusys/__init__.py
  - バージョン: __version__ = "0.1.0"

- 環境設定管理を実装
  - .env 自動読み込み機能（プロジェクトルート検出：.git または pyproject.toml を基準）。
  - .env パーサ（シングル／ダブルクォート、エスケープ、`export KEY=...`、インラインコメントの扱いに対応）。
  - 環境変数読み込みの優先順位制御（OS 環境変数 > .env.local > .env）。
  - 必須環境変数取得ユーティリティ（未設定時に ValueError を送出）。
  - ファイル: src/kabusys/config.py

- 対話式環境設定ウィザードを追加
  - .env の初期作成／更新を支援する CLI ウィザード（秘匿値マスク、選択肢提示、保存確認）。
  - ファイル: src/kabusys/config_setup.py

- 設定検証 CLI を追加
  - 必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在と YAML パース（PyYAML が存在する場合）を検証。
  - `--strict` オプションで警告を失敗扱いにできる。
  - ファイル: src/kabusys/validate_config.py

- 実行エンジン起動スクリプトを追加
  - ExecutionEngine 起動用スクリプト（プロセス優先度設定、DB 接続、Paper Trading 用 DB 分離、BrokerFactory 経由のブローカー選択、デーモンスレッドでのセッション実行、停止フラグ監視）。
  - Paper Trading モードでは MockBroker を用い、本番 DB と完全に分離して data/paper_trading.db を使用可能。
  - ファイル: src/kabusys/run_execution.py

- 監視（Monitoring）起動スクリプトを追加
  - SystemMonitor のポーリングループ。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は環境にかかわらず本番 sqlite_path を使用する旨の挙動を明記。
  - 停止フラグ（data/stop_requested.flag）検知でループを安全に終了。
  - ファイル: src/kabusys/run_monitoring.py

- ロギングユーティリティを追加
  - 統一的なログ設定関数 setup_logging(app_name, log_dir, level) を提供。
  - stdout への StreamHandler（stdout を使用）、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30日保持）。
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
  - ファイル: src/kabusys/utils/logging_setup.py

- プロセス優先度・CPU affinity ユーティリティを追加
  - Windows / POSIX（Linux, macOS 等）を吸収する set_process_priority(level) 実装（"high"/"normal"/"low"）。
  - CPU Affinity 設定用 set_cpu_affinity(cpu_count) を実装。権限不足や未対応環境では警告を出してスキップ。
  - ファイル: src/kabusys/utils/process_priority.py

- ポートフォリオ構築関連の純粋関数群を追加
  - 候補選定(select_candidates)、等金額配分(calc_equal_weights)、スコア配分(calc_score_weights)。
  - セクター集中制限適用(apply_sector_cap)、レジーム乗数(calc_regime_multiplier)。
  - ポジションサイズ計算(calc_position_sizes)（risk_based / equal / score、lot 単位丸め、aggregate cap スケールダウン、コストバッファ対応）。
  - ファイル: src/kabusys/portfolio/*

- Paper Trading 検証レポートツールを追加
  - SQLite（paper_trading DB）から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を集計してレポート出力。
  - Pass/Fail 判定の閾値（稼働率、成功率、送信率、P95 レイテンシ）を定義。
  - コマンドライン引数で期間指定（--from / --to）や DB パス指定（--db）。
  - ファイル: src/kabusys/tools/paper_verification_report.py

- DuckDB を利用するリサーチ基盤の骨格を追加
  - factor_research モジュールの骨格（モメンタム等の指標算出方針・定数を定義）。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。
  - ファイル: src/kabusys/research/factor_research.py（実装の一部が含まれる）

- 監視テーブル初期化ユーティリティ参照
  - run_* スクリプトで init_monitoring_db を呼び、監視テーブルの存在を保証するフローを追加（冪等に対応）。
  - ファイル参照: kabusys.monitoring.monitoring_db（呼び出し箇所: run_monitoring.py, run_execution.py）

### 変更・改善
- 各起動スクリプトで起動直後にプロセス優先度を "high" にセットするよう統一。
  - run_monitoring.py, run_execution.py

- Logging の設計方針
  - 標準出力は stdout を使用（stderr ではなく）。cron や Task Scheduler からの扱いを意識。
  - 既存ハンドラは上書き（flush/close → 削除）して二重登録を防止。

- .env 読み込みの細部改善
  - override と protected（OS 環境変数の保護）機構を導入し、.env.local の上書き挙動を明確化。

### 修正（バグ修正に該当する想定）
- 環境変数パースの堅牢化：引用符内エスケープ、インラインコメント処理、`export` プレフィックス対応により .env の誤読を回避。
- ポジションサイズ計算で合計投下額が利用可能現金を超えた場合のスケーリングロジックを実装（小数端数処理と lot 単位での再配分）。

### 既知の注意点 / 制限
- run_monitoring は「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」との記述があり、開発環境での注意が必要。
- portfolio.risk_adjustment.apply_sector_cap は price が欠損 (0.0) の場合にエクスポージャーがおかしくなる旨の TODO コメントあり（将来的にフォールバック価格の導入を検討）。
- factor_research モジュールは設計方針と定数はあるが、計算ルーチンの途中で切れている（未完成箇所あり）。

### 依存
- psutil（プロセス優先度 / cpu_affinity）
- duckdb（分析用 DB 接続）
- sqlite3（監視・paper_trading DB 操作）
- （任意）PyYAML がインストールされていると config/*.yaml の検証を行う

---

今後のリリースで期待する改善案（例）
- factor_research の完全実装（Momentum / Value / Volatility / Liquidity の算出）とユニットテスト。
- monitoring_db 初期化やテーブルスキーマに関するドキュメントの追加。
- 単体テストと CI の導入（設定検証やポートフォリオロジックの回帰防止）。
- エラーレポート通知（LINE 通知の実装と運用上のガード強化）。