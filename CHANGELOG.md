# Changelog

すべての notable な変更点はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

注: コードベースから推測して記載しています（実際のコミット履歴ではありません）。

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 初回リリース相当の主要コンポーネントを追加。
  - 実行/監視ランナー
    - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（data/paper_trading.db）を使用し、MockBrokerClient を利用する設計に対応。スレッド実行・停止フラグ（data/stop_requested.flag）・PID 書き出し（data/execution.pid）に対応。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB 初期化を行い、停止フラグでループを終了する。
  - 設定管理
    - config.py: .env 自動読み込み（.env / .env.local）、環境変数パース機能（クォート・エスケープ・インラインコメント対応）、Settings クラス（各種設定値の取得とバリデーション）を追加。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
    - config_setup.py: 対話式ウィザードで .env を生成/更新する CLI を追加（各種設定項目、シークレット入力、保存確認付き）。
    - validate_config.py: 起動前の設定検証 CLI を追加（必須環境変数、KABUSYS_ENV, LOG_LEVEL, DB パス、config/*.yaml の存在とパース、live ガード等）。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py: 候補選定（スコアソート）、等金額・スコア重みの計算を実装。スコア全0 の場合は等金額にフォールバック（warning）。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）およびレジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームはフォールバック1.0。
    - portfolio/position_sizing.py: 発注株数算出ロジックを実装（allocation_method: "risk_based" / "equal" / "score" サポート）、単元株（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer を考慮したスケーリングと remainder による再配分を実装。
  - ユーティリティ
    - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。stdout 出力（StreamHandler）と日次ローテーションのファイル出力（TimedRotatingFileHandler）を設定。ログディレクトリ自動作成・失敗時のフォールバック動作を提供。
    - utils/process_priority.py: プラットフォーム差を吸収したプロセス優先度設定（Windows / POSIX）、および CPU affinity 設定ユーティリティを追加。権限不足時は警告を出してスキップ。
  - 監視/実行の共通化
    - monitoring.monitoring_db の初期化呼び出しが各起動スクリプトで行われ、監視テーブルの存在を保証（冪等）。
  - ツール
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。指定期間（--from/--to）や DB 指定（--db）に対応し、稼働率、注文成功率、送信率、P95 レイテンシ等を出力して PASS/FAIL 判定を行う。デフォルト DB は data/paper_trading.db。
  - 研究モジュール（初期）
    - research/factor_research.py: ファクター計算の骨組みを追加（Momentum/Value/Volatility/Liquidity を想定）。DuckDB 接続に基づく設計。モメンタム計算関数の実装開始（ファイル末尾付近は未完の可能性あり）。

### 変更 (Changed)
- なし（初回リリースのため、新規追加中心）。

### 修正 (Fixed)
- なし（初回リリースのため、バグ修正履歴なし）。

### 内部（備考）
- .env パーサは以下の挙動をサポート:
  - export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（クォート無し時は直前が空白/タブでコメント判定）。
  - .env/.env.local の読み込み順序（OS 環境変数 > .env.local > .env）、.env.local はオーバーライド可能。
- Settings クラスは多くの環境変数に対してバリデーションとデフォルトを提供（PAPER_FILL_MODE の有効値チェック、KABUSYS_ENV の有効値チェックなど）。
- Execution/Risk 設定では、RiskManager の初期パラメータ（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）に安全側のデフォルトが設定されている点に留意。
- run_monitoring は「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」という動作になっている（意図的な設計上の仕様）。
- ロギング設定はログディレクトリ作成に失敗しても標準出力は確保するようフェイルセーフになっている。

### 既知の未完/注意点
- research/factor_research.py の末尾が途中（"start_da" で終了）しており、モメンタム計算の実装が未完の可能性あり（追加の実装・ユニットテストが必要）。
- 一部 TODO コメント（price 欠損時のフォールバック価格など）が残っている（将来的な拡張予定）。
- 実行時にプロセス優先度や CPU affinity の設定は権限により失敗する可能性があり、その場合は警告を出してスキップする設計。

### セキュリティ (Security)
- なし（特定のセキュリティフィックスは含まれていません）。環境変数やシークレットの扱いに注意のこと（.env を絶対にリポジトリにコミットしない旨の注記あり）。

---

（この CHANGELOG はコードベースの内容を解析して作成しています。リリース時には実際のコミット・差分に基づいて適宜修正してください。）