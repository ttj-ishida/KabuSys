# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠です。  

最新版: 0.1.0 (初回リリース)

## [Unreleased]
該当なし。

## [0.1.0] - 2026-04-18
初回公開リリース。自動売買システム KabuSys のコアユーティリティ、実行/監視ランチャー、設定管理、ポートフォリオ構築ロジック、検証・レポートツールなどを導入。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージメタ: __version__ = "0.1.0" を導入（src/kabusys/__init__.py）。

- 実行系 / 起動スクリプト
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper trading 用 SQLite (data/paper_trading.db デフォルト) を使用し、本番 DB と分離。
    - BrokerClientFactory を用いて環境に応じたブローカークライアントを作成。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立てて別スレッドで実行し、停止フラグ (data/stop_requested.flag) を監視して安全に停止可能。
    - PID ファイルを書き出す仕組み (data/execution.pid) をサポート。

  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用し、停止フラグでループ終了。
    - 例外はログに残して次のポーリングを継続。

- 設定管理・セットアップ
  - Settings クラス（src/kabusys/config.py）
    - .env の自動ロード機能（.env → .env.local の順にロード、既存 OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - 多数のプロパティを提供（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 環境判定等）。
    - PAPER_FILL_MODE の妥当性検査や環境値検証（KABUSYS_ENV, LOG_LEVEL など）。
  - config_setup: 対話式 .env 作成ウィザードを追加（src/kabusys/config_setup.py）。
    - J-Quants、kabuAPI、DB パス、ログレベル、Kill Switch 等の初期設定をガイド。既存 .env の読み込み・マスク表示・保存機能あり。
  - validate_config: 起動前の設定検証ツールを追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス親ディレクトリチェック、config/*.yaml の存在・パースチェック（PyYAML が利用可能な場合）。
    - --strict モードで警告を失敗扱いにできる。

- ポートフォリオ構築関連（純粋関数群: DB 非依存）
  - portfolio.portfolio_builder: 候補選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio.risk_adjustment: セクター上限適用、レジーム乗数算出（apply_sector_cap, calc_regime_multiplier）。
  - portfolio.position_sizing: 発注株数計算、リスクベース配分、等金額/スコア加重配分、aggregate cap スケーリング、単元株（lot_size）丸め（calc_position_sizes）。
  - これらは PortfolioConstruction.md / StrategyModel.md の設計方針に基づく実装として提供。

- ユーティリティ
  - logging_setup: 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout へ StreamHandler、日次ローテートの TimedRotatingFileHandler をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力を省略してコンソールのみ動作。
    - ログレベル・ログディレクトリの解決順を定義。
  - process_priority: クロスプラットフォームでのプロセス優先度設定、CPU affinity 設定を提供（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX (Linux, macOS, FreeBSD) に対応。権限不足や未実装 API に対しては警告を出してスキップ。

- 検証・レポートツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - システム稼働率、注文成功率（Filled）、送信率（Sent）、リスク却下数、レイテンシ (avg/max/P95) を算出し PASS/FAIL 判定を出力。
    - デフォルト DB は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db。

- リサーチ（因子研究）
  - research.factor_research: モメンタム等のファクター計算基盤を追加（src/kabusys/research/factor_research.py）。
    - Momentum、MA200 乖離、ATR、出来高系などを想定する設計で、DuckDB 接続経由により prices_daily テーブルを参照して計算する仕様（関数 calc_momentum 等を実装中）。

### 変更 (Changed)
- 監視/実行の DB 分離ポリシーを明確化
  - run_execution は paper_trading モードで paper_sqlite_path を使用して本番監視 DB と完全に分離するように実装（設定クラスで paper_sqlite_path を提供）。

- 環境変数の .env パーサを強化
  - クォート文字列内のバックスラッシュエスケープやコメント解釈に対応（src/kabusys/config.py の _parse_env_line）。
  - export KEY=val 形式に対応。

### 修正 (Fixed)
- 停止/終了処理の強化
  - run_execution と run_monitoring で data/stop_requested.flag による安全停止処理を実装。KeyboardInterrupt での graceful shutdown をサポート。

- ログハンドラ二重登録の回避
  - setup_logging で既存ハンドラを flush/close してから削除し、複数回初期化してもハンドラが二重にならないように実装。

### 既知の問題 (Known Issues)
- research.factor_research.calc_momentum 等の実装ファイル末尾が途中で切れている（未完）。
  - ファクター計算は設計方針が整っているが、一部の計算関数が未完・未テストの可能性あり。今後の実装・テストで補完予定。

- position_sizing の価格欠損時の扱い
  - price_map / open_prices に価格欠損（0.0）がある場合、現在は単にスキップしてしまいエクスポージャー/算出が過少見積もりになる可能性がある。TODO コメントで前日終値等のフォールバック導入が検討されている。

- ログディレクトリ作成失敗時はファイル出力が無効化されるが、その旨は stderr に直接出力する仕様になっているため、ログポリシーを運用ルールに合わせて調整することを推奨。

### セキュリティ (Security)
- 機密情報（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、LINE_CHANNEL_ACCESS_TOKEN 等）は .env に保存する設計。.env を絶対にリポジトリにコミットしないことを README/運用手順で徹底すること。

### マイグレーション注意事項 (Migration)
- 既存の運用環境から移行する際は以下を確認してください:
  - 本番用 SQLite/monitoring DB と paper_trading 用 DB は分離されているため、環境変数 KABUSYS_ENV を適切に設定してください。
  - .env の自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - ログディレクトリや DB ファイルの親ディレクトリが存在しない場合は起動スクリプトが警告を出します。必要に応じてディレクトリを事前に作成してください。

---

その他、細かい実装上の注釈や TODO は各ソースファイル内コメントを参照してください。今後のリリースではファクター計算の完成、テストカバレッジ拡充、運用向けの監視/アラート強化を予定しています。