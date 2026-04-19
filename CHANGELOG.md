# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
形式は「Keep a Changelog」に準拠し、セマンティック・バージョニングを意識しています。

## [0.1.0] - 2026-04-19
初回公開リリース。コードベースから推測される主要な機能追加・動作仕様をまとめます。

### 追加 (Added)
- 基本アプリケーションパッケージを追加
  - kabusys パッケージ初期化（__version__ = "0.1.0"）。
- 設定管理
  - Settings クラスを導入。環境変数から各種設定（J-Quants トークン、kabuAPI パスワード、DB パス、ログ設定、監視閾値など）を取得・検証するプロパティ群を提供。
  - 自動 .env ロード機能を追加（プロジェクトルートの探索: .git または pyproject.toml を基準）。.env と .env.local の読み込み順序を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env の行パーサを実装（export プレフィックス、引用符付き値、エスケープ、インラインコメントの扱いをサポート）。
- 環境設定ウィザード CLI
  - config_setup.py により対話式で .env を作成・更新するウィザードを追加。主要項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、ログ等）をサポート。
- 設定検証 CLI
  - validate_config.py により、.env や config/*.yaml の存在・基本妥当性をチェックする CLI を追加（--strict オプションあり）。
- 実行/監視エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading のときは paper_trading 専用 SQLite を使用し、MockBroker を適用（本番 DB と分離）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイルにより安全停止が可能。
- ロギングユーティリティ
  - utils/logging_setup.py を追加。ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定。ログディレクトリ作成失敗時はファイル出力をスキップして安全にフォールバック。
- プロセス優先度ユーティリティ
  - utils/process_priority.py を追加。Windows/Linux/macOS を抽象化してプロセス優先度（high/normal/low）を設定する set_process_priority、および CPU affinity を設定する set_cpu_affinity を提供。アクセス権限不足時は警告を出してスキップ。
- ポートフォリオ構築ライブラリ
  - portfolio モジュールを追加（純粋関数群）。
    - portfolio_builder: 候補選定（select_candidates）、等配分・スコア配分（calc_equal_weights, calc_score_weights）。
    - risk_adjustment: セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier（bull/neutral/bear をマップ）。
    - position_sizing: 株数決定ロジック calc_position_sizes（risk_based / equal / score をサポート、lot_size 単位丸め、aggregate cap、cost_buffer による保守的見積り、スケーリングと残差処理を実装）。
- ペーパートレード検証ツール
  - tools/paper_verification_report.py を追加。Paper Trading の SQLite を集計して稼働率、注文成功率、送信率、レイテンシ（P95 など）を算出し、PASS/FAIL 判定を行う。閾値はソース内定数で定義（稼働率 99% など）。
- リサーチ（ファクター計算）基盤
  - research/factor_research.py を追加（モメンタム等のファクター計算方針・定数を実装開始）。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計を採用。

### 変更 (Changed)
- DB 接続方針
  - 監視（run_monitoring）は KABUSYS_ENV に依らず本番 sqlite_path を使用する点を明記（監視は本番データを対象とする想定）。
  - 実行（run_execution）は paper_trading 環境であれば paper_sqlite_path（data/paper_trading.db デフォルト）を使用して本番 DB と分離。
- ロガー挙動
  - ログ出力は stdout を優先（stderr ではなく）し、cron / Task Scheduler 等でのリダイレクト運用を考慮。
- プロセス起動時の挙動
  - run_execution/run_monitoring 起動時に最初に set_process_priority("high") を呼び出してプロセス優先度を可能な限り高く設定する。
- .env ロードの優先度
  - OS 環境変数 > .env.local > .env の順でロード。既存の OS 環境変数は保護され、.env.local での上書きは OS 環境変数を侵さない。

### 修正 (Fixed)
- .env パーサの堅牢化
  - export プレフィックス、引用符付き値、バックスラッシュエスケープ、インラインコメントの扱いを正しく処理することで .env の柔軟な記述に対応。
- ログハンドラの重複防止
  - setup_logging() は既存ハンドラを flush/close してから再設定する実装により二重出力を回避。
- DB 初期化の冪等性
  - init_monitoring_db() を呼び出して監視テーブルが存在することを保証（複数回起動時にも安全）。
- 守りの例外処理
  - run_monitoring のポーリングループ内で monitor.check_once() の例外を捕捉し、ログ出力後に次ループへ継続するようにして監視停止を防止。
  - run_execution 内のスレッド監視ループは停止フラグ検知時に engine.stop() を呼び出し、安全停止を試みる。

### 既知の注意点 / 破壊的変更 (Breaking Changes)
- 監視プロセスは常に本番の sqlite_path を使用するため、開発環境で同プロセスを起動すると本番データを参照する恐れがあります。意図的な設計であるが、運用時は注意が必要です。
- PAPER_FILL_MODE の値は限定された文字列（instant/partial/never/reject）でないと例外を投げるため、環境変数設定ミスにより起動失敗する可能性があります。
- process_priority の設定はプラットフォームや権限に依存し、設定に失敗した場合は警告が出て処理は続行されます（例外は送出されません）。

### セキュリティ関連 (Security)
- 本リリースでは秘密情報（J-Quants トークン、kabu API パスワード等）を .env に保存する想定。.env は Git にコミットしないようウィザード注釈に明記。
- validate_config による本番環境（KABUSYS_ENV=live）時の注意喚起（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険設定）を追加。

---

今後のリリースでは以下を検討する予定（コード中の TODO 等から推測）
- position_sizing の銘柄別 lot_size サポート（stocks マスタに lot_size を追加）。
- price 欠損時のフォールバック（前日終値や取得原価）の実装。
- factor_research のファクター計算実装完了（Momentum, Value, Volatility, Liquidity の算出ロジック完全化）。
- 監視・実行周りのより柔軟な環境分離とテスト用フラグの追加。

（この CHANGELOG は提供されたコードベースから推測して作成しています。実際の変更履歴やコミット履歴と差異がある可能性があります。）