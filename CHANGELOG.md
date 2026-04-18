# Changelog

すべての重要な変更点をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従って管理されています。  

リリース日付はパッケージの初期公開時点を示します。

## [0.1.0] - 2026-04-18

### 追加
- 初期リリースとして以下の主要コンポーネントを実装・公開しました。
  - 実行系 / 監視系エントリポイント
    - run_execution.py: ExecutionEngine を起動する CLI スクリプト。KABUSYS_ENV に応じて paper_trading 用の専用 DB と MockBrokerClient を利用して本番 DB と分離。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。
  - 設定管理 / 検証 / ウィザード
    - config.py: 環境変数読み込み、自動 .env ロード、Settings クラスを提供（各種環境変数・デフォルトの集約）。
    - validate_config.py: .env と config/*.yaml を起動前に検証する CLI。--strict オプションで警告も失敗扱いに可能。
    - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - portfolio/portfolio_builder.py: シグナル選定（select_candidates）と等金額／スコア重み計算（calc_equal_weights, calc_score_weights）。
    - portfolio/risk_adjustment.py: セクター上限の適用（apply_sector_cap）、マーケットレジームに応じた投下資金乗数（calc_regime_multiplier）。
    - portfolio/position_sizing.py: 株数決定ロジック（calc_position_sizes） — risk_based / equal / score の allocation_method をサポート。lot_size、cost_buffer、aggregate cap の実装あり。
  - 解析・検証ツール
    - tools/paper_verification_report.py: Paper Trading 用 SQLite DB から稼働率・注文成功率・レイテンシ等を集計して PASS/FAIL 判定を行うレポート生成スクリプト。
  - ユーティリティ
    - utils/logging_setup.py: 全アプリケーションで統一して使用するログ設定ユーティリティ（コンソール stdout と日次ローテートファイル出力）。
    - utils/process_priority.py: Windows / POSIX の差分を吸収してプロセス優先度と CPU affinity を設定するユーティリティ。set_process_priority(), set_cpu_affinity() を提供。
  - 研究用モジュール（骨子）
    - research/factor_research.py: ファクター計算モジュールの骨組み（モメンタム等の計算を想定）。（実装の続きあり）

- 監視・実行の運用上の仕組みを整備
  - PID ファイル・停止フラグ（data/*.pid / data/stop_requested.flag）を用いたプロセス制御。
  - 監視テーブルの初期化関数 init_monitoring_db を呼び出して監視用テーブルの存在を保証。
  - run_execution は停止フラグ検知時にエンジン起動を拒否／実行中の停止を実行。

- 環境分離
  - paper_trading 環境判定（Settings.is_paper）に基づき、発注処理・DB を本番と分離してペーパートレードを安全に実行可能。

### 変更（設計・利便性）
- ロギング
  - 標準化されたログ設定関数を導入し、アプリケーション毎に同一フォーマット・ローテーションポリシー（30日保持）が適用されるようにした。
  - stdout に出力する StreamHandler を用い、cron/task scheduler からの起動時にログの取り回しがしやすい設計。

- 設定読み込みの挙動
  - 自動 .env ロードの仕組みを導入（プロジェクトルートが特定できる場合のみ、OS 環境 > .env.local > .env の順で読み込み）。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能（テスト用途など）。

- Execution のリスク管理設定
  - RiskManager の初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）をコード内で定義し、初期運用値を提供。

### 修正（バグ修正 / 安全対策）
- 設定検証ツール validate_config の強化
  - 必須環境変数の未設定検出やプレースホルダ値の警告、KABUSYS_ENV の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML 未インストール時はスキップ）を実装。
  - KABUSYS_ENV=live 時の注意喚起チェック（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START の危険設定など）。

- run_monitoring / run_execution における例外耐性
  - monitor.check_once() 内での例外を捕捉してログ出力し、次回のポーリングまで待機することでループ全体の停止を防止。

### 既知の制約・注意点
- 一部実装に TODO / 制限が残っています。
  - portfolio/risk_adjustment.apply_sector_cap: price_map に価格が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性あり。将来的に前日終値や取得原価でのフォールバックを検討予定。
  - position_sizing: 現状 lot_size はグローバルな単一値（デフォルト 100）を想定。将来的に銘柄別 lot_map への拡張を検討。
  - research/factor_research.py はファイルの末尾で中断（実装の続きあり）。

- 動作環境・依存
  - DuckDB, psutil, sqlite3 を利用。YAML の検証には PyYAML があるとより厳密に検査可能。
  - Windows と POSIX（Linux/Mac）でのプロセス優先度設定や CPU affinity は環境依存であり、権限不足等で設定に失敗する場合は警告を出してスキップします。

### セキュリティ
- .env ファイルは絶対にリポジトリにコミットしないでください（config_setup.py のヘッダに注意喚起あり）。
- 機密値（J-Quants リフレッシュトークン、KABU_API_PASSWORD 等）は .env または OS 環境変数で管理。config_setup は対話入力中にマスク表示しますが、標準入出力の保護は利用者の責任です。

---

今後の予定（短期）
- research/factor_research の完全実装（DuckDB SQL を使ったファクター計算）。
- position_sizing の銘柄別 lot_size 対応と価格欠測時のフォールバックロジック強化。
- テストカバレッジの拡充（ユニットテスト・統合テスト）。
- ドキュメント（運用手順、デプロイ手順、監視アラート設定など）の整備。

--- 

（翻訳注）本 CHANGELOG は現行コードベースの実装内容から推定して作成しています。実際のリリースノートとして使用する場合は、変更履歴やコミットログと突合して内容を確定してください。