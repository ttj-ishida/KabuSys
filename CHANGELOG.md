# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-04-20

### 追加 (Added)
- 初回公開リリース。KabuSys 自動売買基盤の基本コンポーネントを実装。
- 起動スクリプト:
  - run_execution.py — ExecutionEngine を起動する CLI。KABUSYS_ENV=paper_trading 時は paper 用 DB を使用し MockBrokerClient 経由で動作（本番 DB と完全分離）。停止フラグ / PID ファイルの取り扱いを実装。
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ検知で安全にループ終了。
- 設定管理:
  - config.py — 環境変数 / .env 自動ロード機能（.env, .env.local の優先順位）と Settings クラスを提供。各種環境変数の検証（env 値、PAPER_FILL_MODE など）を実装。
  - config_setup.py — 対話式 .env 作成・更新ウィザードを実装。既存 .env 読み込み、秘密項目のマスク表示、保存機能を提供。
  - validate_config.py — 起動前検証 CLI。必須環境変数、KABUSYS_ENV の妥当性、パスや config/*.yaml の存在やパース検証（PyYAML 有無に応じて）をチェック。--strict モードをサポート。
- ポートフォリオ構築（純粋関数群、DB 参照なし）:
  - portfolio.portfolio_builder: 銘柄候補選定 select_candidates、等分配 calc_equal_weights、スコア加重 calc_score_weights を実装。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap、レジームに応じた乗数 calc_regime_multiplier を実装（未知レジームは警告してフォールバック）。
  - portfolio.position_sizing: position sizing のコアロジック calc_position_sizes を実装。allocation_method に "risk_based", "equal", "score" をサポートし、単元株丸め（lot_size）、aggregate cap（利用可能現金に基づくスケールダウン）、cost_buffer を考慮した安全なスケーリングを実装。
- ユーティリティ:
  - utils.logging_setup: stdout ストリームハンドラと日次ローテーションファイルハンドラをルートロガーに設定する共通セットアップ。LOG_DIR の作成失敗時にファイル出力をスキップしてフォールバック。
  - utils.process_priority: Windows / POSIX を吸収したプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティ。権限不足や未対応 OS は警告して安全にスキップ。
- 監視・分析:
  - monitoring 用 DB 初期化呼び出し（init_monitoring_db）を各起動スクリプトで保証（冪等）。
  - DuckDB 接続を用いた解析基盤を起動スクリプトで確保（duckdb_path）。
- ツール:
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを実装。期間指定（--from/--to）や DB パス指定（--db）に対応。稼働率 / 注文成功率 / 送信率 / レイテンシ（平均・最大・P95）を集計し PASS/FAIL判定（閾値はソース内定義）を出力。

### 変更 (Changed)
- なし（初回リリース）。

### 修正 (Fixed)
- ログ設定やプロセス設定の失敗時のフォールバックを強化：
  - ログディレクトリ作成失敗時にファイルハンドラを作らず stdout のみで継続。
  - プロセス優先度／CPU affinity の設定で AccessDenied などをキャッチして警告を出し処理を継続。
- 環境変数読み込みの堅牢化:
  - .env のパース処理で引用符やエスケープ、インラインコメント、export プレフィックスに対応し、実運用での .env 記述差分に耐性を持たせた。

### 既知の制限・ TODO (Known issues / TODO)
- portfolio.position_sizing の price フォールバック:
  - price が欠損（0.0）の場合、現状ではエクスポージャーが過少見積りされる可能性があり、将来的に前日終値や取得原価によるフォールバックを検討する旨の TODO が残っている。
- research.factor_research モジュールは部分的に実装（ソースが途中で切れている）ため、ファクター計算の完全実装は今後の課題。
- 一部の機能（BrokerClientFactory / ExecutionEngine / SystemMonitor 等の内部実装）はこの公開物とは別モジュール依存のため、本リポジトリ内のモック・外部実装に依存する点に注意。

### セキュリティ (Security)
- なし。

---
もし特定箇所の変更点や細かなリファクタリング記載を追加したい場合は、該当ファイルや差分情報を提供してください。