# Changelog

すべての重要な変更履歴をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティック・バージョニングを想定します。

## [0.1.0] - 2026-04-18

初回リリース。本リポジトリは日本株自動売買システム「KabuSys」のコアユーティリティ、実行・監視ランナー、ポートフォリオ構築ロジック、検証ツール類を含みます。

### Added
- 基本情報
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を追加。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するためのエントリポイントを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレーディング SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を経由してブローカークライアントを作成。
    - エンジン実行はデーモンスレッドで行い、 data/stop_requested.flag による外部停止をサポート。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority）。
    - 実行時 PID ファイル（data/execution.pid）をサポート。

  - run_monitoring.py
    - SystemMonitor を定期実行するポーリングループのエントリポイントを追加。
    - MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を設定可能（デフォルト: 60）。
    - 監視は環境に関わらず本番 sqlite_path を使用して監視テーブルを初期化。
    - data/stop_requested.flag による停止をサポート。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理 / セットアップ / 検証
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検知）。
    - .env のパースはシングル/ダブルクォートやエスケープ、"export KEY=val" 形式、コメントを考慮した堅牢な実装。
    - Settings クラスを提供し、各種環境変数の取得と妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を行うユーティリティを追加。
    - Paper Trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）、PID/kill flag のパス等のプロパティを提供。

  - config_setup.py
    - .env 初期作成／更新の対話式ウィザードを追加。
    - J-Quants / kabu API トークン等の秘密値をマスク表示で入力可能。
    - 生成される .env のテンプレートと書き込み機能を提供。

  - validate_config.py
    - .env と config/*.yaml（存在する場合）の起動前検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML パース（PyYAML がインストールされている場合）を行う。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。
    - スコア合計が 0 の場合のフォールバックを実装（等配分 + ログ警告）。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存ポジションのセクター・エクスポージャーに基づく除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull"/"neutral"/"bear" のマッピング、未知レジームはフォールバック）。

  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算 calc_position_sizes を実装。
    - allocation_method = "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮した上で aggregate cap（利用可能現金に応じたスケーリング）を実装。
    - 小数端数処理や端数の再配分ロジックを実装（lot_size 単位での調整）。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）によるファイル出力（logs/<app_name>.log）を設定。
    - ログディレクトリ作成失敗時はファイル出力を無効化してコンソールのみ継続。
    - LOG_LEVEL / LOG_DIR / app_name を考慮した解決順を実装。

  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定のユーティリティを追加（set_process_priority, set_cpu_affinity）。
    - psutil を使用し、アクセス権限不足等は警告ログでフォールバック。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレードの検証レポート生成スクリプトを追加。
    - system_status, trade_logs, risk_logs などを集計し、稼働率／注文成功率／送信率／レイテンシ（P95）を算出。
    - デフォルト基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定。
    - CLI 引数 --from/--to/--db をサポート。

- 研究用モジュール（着手）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity に関する設計方針と一部定数・関数スケルトンを追加（DuckDB を用いた計算想定）。※実装は継続中

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Migration
- 環境変数読み込み
  - OS 環境変数 > .env.local > .env の優先順で自動読み込みされます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading
  - paper_trading 環境では SQLite DB が明確に分離されます（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db を使用）。本番 DB への誤発注を防ぐために設計されています。
- モニタリング / 実行の停止
  - 停止制御はプロジェクトルート data/stop_requested.flag（および実行用 PID ファイル）で行います。運用時はこのフラグの扱いを運用手順に従ってください。
- 環境値の妥当性
  - Settings.paper_fill_mode は "instant" / "partial" / "never" / "reject" のいずれかでなければ例外となります。
  - KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかである必要があります。

### CLI / 実行例
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

## Unreleased
- なし

---

参照: 本ファイルはコードベースから推測して作成しています。実際のリリースノートとして公開する際は、実装責任者による確認・追記（バグ修正・既知の制限・互換性情報など）を推奨します。