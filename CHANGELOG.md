# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。  

- リリース日付は ISO 8601 (YYYY-MM-DD) 形式を使用します。  
- 本ファイルは、コードベースから推測可能な機能追加・設計方針・振る舞いをもとに作成しています。

## [Unreleased]

- 現在未リリースの変更はありません（初回リリースに向けての実装済み機能を記載済み）。

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 全体
  - プロジェクト初期実装をリリース。自動売買システム「KabuSys」のコアユーティリティ・CLI・ライブラリ群を収録。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト / 実行
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を利用して paper_trading 用 DB（デフォルト: data/paper_trading.db）へ記録する仕組みをサポート。
    - プロセス優先度を起動直後に "high" に設定。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理を実装。
    - スレッドで ExecutionEngine.run_session を実行し、停止フラグ検出時に安全停止するループを実装。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境に関わらず本番 sqlite_path を使用する仕様。
    - DB 初期化（監視テーブル）および DuckDB 接続を確立し SystemMonitor.check_once() を定期実行。
    - 停止フラグ検知による安全終了、KeyboardInterrupt ハンドリングを実装。

- 設定管理 / CLI
  - config.py: 環境変数・設定管理モジュールを追加。
    - .env 自動ロード機能（プロジェクトルート判定: .git または pyproject.toml を検索）。
    - ロード順: OS 環境変数 > .env.local > .env。OS 環境変数の保護（上書き防止）を実装。
    - 複数の設定プロパティを提供（J-Quants, kabuAPI, LINE, DB パス、監視閾値、KABUSYS_ENV 等）。
    - PAPER_FILL_MODE の検証、env 値検証（KABUSYS_ENV や LOG_LEVEL のバリデーション）。
  - config_setup.py: インタラクティブな .env 設定ウィザードを追加。
    - 各種設定項目の対話的入力、既存 .env の読み込み・マスク表示、保存機能を提供。
    - 保存テンプレートは .env に書き込まれるが、Git にコミットしない旨の注意書きを含む。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース検査（PyYAML 未インストール時はスキップ）を実装。
    - --strict オプションで警告を FAILURE 扱いにする機能。
    - 本番環境（KABUSYS_ENV=live）に対する追加の注意喚起（LINE 設定や Kill Switch の確認）。

- ログ / プロセスユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
    - LOG_DIR・LOG_LEVEL の解決順、ログディレクトリ作成失敗時のフォールバック（ファイル出力無効化）に対応。
  - utils/process_priority.py: プロセス優先度および CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX の差分を吸収して set_process_priority(level) を提供（"high"/"normal"/"low"）。
    - set_cpu_affinity(cpu_count) によるコアピン留め機能を提供。権限不足や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定と重み計算（等金額・スコア加重）を追加。
    - select_candidates: スコア降順で上位 N 件を選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights を提供。スコア合計が 0 の場合は等金額へフォールバックして警告を出力。
  - portfolio/risk_adjustment.py: セクター上限適用とレジーム乗数を追加。
    - apply_sector_cap: 既存保有をもとにセクター別エクスポージャーを計算し、最大セクター比率を超える場合は新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を提供（bull/neutral/bear = 1.0/0.7/0.3）。未知レジームは 1.0 にフォールバックして警告。
  - portfolio/position_sizing.py: 発注株数計算ロジックを追加。
    - allocation_method に応じた株数決定: "risk_based"（リスクベース）および "equal"/"score" をサポート。
    - lot_size（単元）丸め、1 銘柄上限（max_position_pct）、投下資金上限（max_utilization）、手数料/スリッページを考慮した cost_buffer を導入。
    - aggregate cap 超過時のスケールダウンアルゴリズムを実装し、端数は lot_size 単位で再配分。
    - 価格未取得時はスキップしてログを出力。

- 解析 / レポート / ツール
  - research/factor_research.py（部分実装、モメンタム等のファクター計算設計を含む）
    - DuckDB から prices_daily / raw_financials を参照してモメンタム・MA・ATR 等を計算する方針を実装（関数群の設計と定数が定義されているが一部実装は継続中）。
  - tools/paper_verification_report.py: Paper Trading 検証レポートジェネレータを追加。
    - DB（デフォルト: data/paper_trading.db）から統計を集計して稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を出力。
    - P95 計算、日付フィルタ（--from/--to）、閾値を超えていれば FAIL 判定を出力する仕組みを提供。
    - 閾値: 稼働率 99.0%、注文成功率 90.0%、送信率 95.0%、P95 レイテンシ 200ms（デフォルト）。

### 変更 (Changed)
- 設定の自動読み込みポリシーを定義
  - OS 環境変数保護機構を導入し、.env ファイル読み込み時に OS の既存値を上書きしない（.env.local は上書き可能だが OS 環境は保護）。
- ロギングの振る舞い
  - 起動スクリプトはまず logging_setup.setup_logging() を呼び出し、以降のログは設定済みハンドラに依存して出力される。
  - コンソール出力は stdout を使用（cron/Task Scheduler におけるリダイレクト対策）。

### 修正 (Fixed)
- .env パーサーの堅牢性向上
  - _parse_env_line にてシングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、`export KEY=...` 形式への対応を実装。
  - コメント判定ロジックを改善し、クォートなしの値に対して `#` 前に空白がある場合のみコメントとして扱う仕様を導入。
- DB 初期化の冪等性
  - 起動時に monitoring DB の初期化（init_monitoring_db）を必ず呼び出すことでテーブル未作成時の起動失敗を防ぐ。

### 注記 (Notes)
- 一部ファイル（例: research/factor_research.py）は設計と定数が中心で、計算ロジックの全実装は継続中。将来的に DuckDB を用いた完全なファクター計算が実装される予定。
- position_sizing の price フォールバック（前日終値や取得原価）に関する TODO コメントあり。価格欠損時の挙動に注意。
- process_priority の機能は権限やプラットフォームに依存し、失敗時は警告を出して安全にスキップする設計。

### セキュリティ (Security)
- 環境変数の取り扱いは .env に秘密値（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を保存する想定だが、.env を絶対にバージョン管理にコミットしない旨をドキュメント化。
- config_setup の対話ではシークレット項目をマスク表示。

---

将来的なリリースでは以下の点を改善・追加予定:
- research/factor_research.py の完全実装（DuckDB SQL + Python によるファクター算出）。
- 発注関連（ExecutionEngine / BrokerClient）の単体テスト拡充とモックの強化。
- 銘柄ごとの lot_size や価格フォールバックロジックの導入。
- モニタリング・アラートの LINE 通知統合（LINE 設定がある場合）。
- 監視・実行の Docker / systemd ユニット向けの起動例と運用ドキュメントの整備。

※ 本 CHANGELOG は、与えられたコードベースの実装内容から推測して作成しています。実際のコミット履歴や開発ノートと差分がある場合は、適宜修正してください。