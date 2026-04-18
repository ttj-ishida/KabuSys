Keep a Changelog 準拠の CHANGELOG.md（日本語）を以下に作成しました。コードベースの内容から推測して記載しています。必要に応じて日付・表現の調整を行ってください。

---
Keep a Changelog
All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### Added
- 全体
  - 初期のアプリケーション構成と複数の起動スクリプト／ユーティリティを追加。
  - パッケージバージョンを `0.1.0` に設定（src/kabusys/__init__.py）。

- 設定管理
  - 環境変数／.env 自動読み込み機能を追加（src/kabusys/config.py）。
    - プロジェクトルート（.git または pyproject.toml）を自動検出して .env, .env.local を読み込む。
    - OS 環境変数を優先し、.env.local は .env をオーバーライド可能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - Settings クラスを追加し、各種設定値（DB パス、API トークン、監視値、環境種別など）をプロパティで提供。
    - PAPER_FILL_MODE（ペーパートレードの約定モード）に対するバリデーションを実装（instant/partial/never/reject）。
    - KABUSYS_ENV の有効値チェック（development/paper_trading/live）。
    - 各種デフォルトを明確化（例：DUCKDB_PATH= data/kabusys.duckdb, SQLITE_PATH= data/monitoring.db 等）。

- 起動スクリプト / 実行関連
  - 監視プロセス起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視データベースを扱う設計。
    - 停止フラグ（data/stop_requested.flag）検知による安全な終了処理。
    - 起動時にプロセス優先度を "high" に設定。
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード専用 DB（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - 設定に応じて BrokerClientFactory を用いてブローカークライアントを生成（MockBrokerClient を使った分離が可能）。
    - ExecutionEngine を別スレッドで実行し、停止フラグで安全停止。PID ファイル管理。
    - 起動時にプロセス優先度を "high" に設定。

- コンフィグ支援 CLI
  - 対話式 .env 作成・更新ウィザードを追加（src/kabusys/config_setup.py）。
    - 各種必須／任意項目を定義し、既存 .env の読み込み・マスク表示・保存をサポート。
    - 実行例: python -m kabusys.config_setup
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ確認、config/*.yaml の存在と（PyYAML があれば）パース検証を実施。
    - --strict オプションで警告も失敗扱いにできる。
    - 実行例: python -m kabusys.validate_config

- ロギング・プロセス管理ユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ローテーション保持日数は 30 日。
  - プロセス優先度／CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX を吸収して nice 値や Windows プロセス優先度を設定。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足等は警告でスキップ。

- ポートフォリオ構築ライブラリ
  - 銘柄選定・配分ロジックを追加（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates（スコアソート）、calc_equal_weights（等金額）、calc_score_weights（スコア正規化、全スコアが 0 の場合は等配分へフォールバック）。
  - セクター集中・レジーム調整ロジックを追加（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap（既存ポジションによりセクター上限を超える場合の候補除外。unknown セクターは除外しない）。
    - calc_regime_multiplier（"bull"/"neutral"/"bear" に対する乗数。未知レジームは 1.0 にフォールバック）。
  - 株数決定ロジックを追加（src/kabusys/portfolio/position_sizing.py）。
    - risk_based / equal / score の割当方式に対応。
    - 単元株（lot_size）で丸め、per-stock 上限・aggregate cap（available_cash）に基づくスケーリング、cost_buffer による保守的見積りを実装。
    - scale-down 時の端数補正ロジックを実装（remainder に基づく追加配分）。
  - ポートフォリオモジュールのエクスポートを追加（src/kabusys/portfolio/__init__.py）。

- リサーチ（ファクター）モジュール（骨組み）
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity の設計方針と定数群を追加。
    - calc_momentum の実装を開始（prices_daily テーブル参照）。（ファイル末尾が切れているため一部未完）

- ペーパートレード検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・P95 レイテンシ等を算出して PASS/FAIL 判定を出力。
    - デフォルト DB パスは data/paper_trading.db。--from/--to/--db オプション対応。
    - しきい値（稼働率 99%、成立率 90%、送信率 95%、P95 <= 200ms）を定義。

### Changed
- run_monitoring.py / run_execution.py
  - 起動時にプロセス優先度を最初に "high" に設定するように変更（安定稼働を優先）。
  - 監視用 DB 初期化（init_monitoring_db）を両スクリプトで呼び出して監視テーブルの存在を保証（冪等）。
  - run_execution は KABUSYS_ENV=paper_trading の場合に専用 sqlite ファイルを使用するよう明確化（本番 DB と完全分離）。

- config.py
  - .env のパース仕様を詳細化（export プレフィックス、クォート内バックスラッシュエスケープ、インラインコメントの扱いなど）。
  - 環境変数取得の失敗時に分かりやすいエラーメッセージを出すように統一（_require）。

- logging_setup.py
  - stdout を StreamHandler に使う設計へ明示（cron 等のリダイレクト運用を考慮）。
  - ファイルハンドラ作成失敗時もサービス継続できるよう堅牢化。

### Fixed
- run_monitoring.py
  - MONITOR_POLL_INTERVAL に対して不正な値（非数・0 以下）を指定した場合にログで警告しデフォルト（60 秒）へフォールバックするように修正。time.sleep へ不正値が渡らないように防御。

- process_priority.py
  - 未対応 OS や権限不足の場合に警告ログを出して設定をスキップすることで例外発生を防止。

- portfolio/position_sizing.py
  - 単元株丸めや aggregate cap スケーリング時の端数処理を改善し、再現性のある手順（fractional remainder による分配）を実装。

### Known issues / TODO
- research/factor_research.py の calc_momentum 実装が途中で終わっている（ソース末尾が切れている）。実装継続が必要。
- price の欠損（0.0）の扱いについては注釈あり（現状では過少評価される可能性があるため、将来的に前日終値等のフォールバックを検討）。
- 一部のファイルハンドリングでの例外細分化やユニットテストの整備が残っている。
- config/*.yaml の自動生成スクリプト（scripts/generate_config.py）を README に追記すると親切。

---

## [0.1.0] - 2026-04-18
初回リリース。本リリースでは上記の機能群（設定管理、起動スクリプト、ログ設定、プロセス管理、ポートフォリオ構築、ペーパートレード検証ツール、設定ウィザード・検証 CLI）を含む基本的な自動売買基盤の骨格を提供します。

- 重要機能
  - Settings ベースの設定管理、自動 .env ロード
  - 実行エンジン（ExecutionEngine）起動スクリプト（ペーパートレード用 DB 分離）
  - 監視プロセス（SystemMonitor）起動スクリプト（ポーリング間隔設定のサポート）
  - ログ統合（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - ポートフォリオ構築（候補選定、重み計算、株数決定、セクターキャップ、レジーム乗数）
  - Paper Trading 検証レポート生成ツール
  - 対話式 .env ウィザード、設定検証 CLI

---

補足:
- 上記はソースコードからの推測に基づく CHANGELOG です。実際のリリース日や追加・修正内容はプロジェクトの実際のコミット履歴に合わせて調整してください。必要であれば各ファイルを参照して、より細かい差分（関数名・引数の変更、内部挙動の詳細）まで反映した改訂版を作成します。