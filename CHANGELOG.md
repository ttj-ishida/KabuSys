CHANGELOG
=========

すべての重要な変更はここに記録します。本ファイルは「Keep a Changelog」仕様に準拠しています。

フォーマット:
  - Added: 新規追加
  - Changed: 変更
  - Fixed: 修正
  - Removed: 削除
  - Security: セキュリティ関連

[0.1.0] - 2026-04-25
-------------------

Added
- プロジェクト初期リリース。
- 起動スクリプトを追加:
  - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV に応じて paper_trading 用の MockBrokerClient を使用し、paper_trading 環境では専用 SQLite（data/paper_trading.db）を使用する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクトルートの data/stop_requested.flag により制御。
- 環境/設定管理:
  - config.py: .env 自動読み込み（.env → .env.local の順、OS 環境変数を保護）と堅牢な .env パーサを実装。Settings クラスで各種環境変数の取得・バリデーションを提供（J-Quants / kabu API / DB パス / Paper Trading 関連など）。
  - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。出力テンプレートは .env を Git に含めないよう注意を促す。
  - validate_config.py: 起動前チェック用 CLI を追加。必須環境変数や YAML 設定ファイルの存在・パース、KABUSYS_ENV の検証、本番（live）時の追加ガードなどを行う。--strict により警告も失敗扱いにできる。
- 監視関連:
  - monitoring DB 初期化ユーティリティ（init_monitoring_db）を使用して監視用テーブルの存在を保証。
  - run_monitoring/run_execution で PID ファイル・停止フラグ・kill フラグ関連のパスを Settings 経由で統一。
- ロギング／プロセス制御ユーティリティ:
  - utils/logging_setup.py: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定する共通ユーティリティを追加。ログディレクトリ作成に失敗した場合はファイル出力をスキップして標準出力のみで継続。
  - utils/process_priority.py: Windows / POSIX の差分を吸収したプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティを追加。psutil が提供する例外をハンドリングしてフォールバック。
- ポートフォリオ構築モジュール:
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、タイブレーク）、等金額配分、スコア重み付け（全スコアが 0 の場合は等配分へフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた資金乗数（calc_regime_multiplier）を追加。unknown セクターの扱いやフォールバック挙動を定義。
  - portfolio/position_sizing.py: 株数決定ロジックを実装。risk_based / equal / score の配分方式をサポートし、単元（lot）丸め、1銘柄上限・aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリングロジックを実装。
- ツール／レポート:
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。期間指定 --from / --to、DB 指定 --db をサポート。稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）・リスク却下数などを集計し PASS/FAIL 判定を行う。
- リサーチ／ファクター計算（構造追加・ドキュメント化）:
  - research/factor_research.py: Momentum・Value・Volatility・Liquidity 等のファクター計算用モジュールの枠組みとモメンタム計算関数の実装方針を追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計）。（計算定数や設計方針をコード内に記載）

Changed
- データベースの分離: paper_trading 環境での発注/取引履歴は本番 monitoring DB と明確に分離（Settings.paper_sqlite_path / PAPER_TRADING_SQLITE_PATH）。
- ログハンドラとログレベルの解決優先度を統一（setup_logging）。
- .env 自動読み込みの挙動: OS 環境変数は保護され、.env.local は .env を上書きする（ただし OS 環境変数優先）。

Fixed
- .env ファイルパーサの堅牢化:
  - export KEY=val 形式のサポート、シングル／ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い（クォート有無での挙動差）などに対応。
- run_monitoring のポーリング間隔指定（MONITOR_POLL_INTERVAL）に対する入力検証を追加。0 以下や非数値はログ警告を出してデフォルト（60 秒）にフォールバック。
- process_priority / set_cpu_affinity は権限不足や未実装 API に対して警告ログを出してスキップするように改善。

Security
- config_setup にて .env を絶対に Git にコミットしない旨を明示して出力。
- validate_config で本番環境（KABUSYS_ENV=live）の場合に LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）の有無や KILL_FLAG_CLEAR_ON_START の危険設定を警告。

Notes / Implementation details
- ExecutionEngine の起動はスレッドで行い、stop フラグ検知で engine.stop() を呼ぶ設計（デーモンスレッドの利用と安全な終了処理を考慮）。
- RiskManager のデフォルト設定値を Execution 側で設定（例: max_position_pct=0.20, max_utilization=0.80, etc.）。initial_portfolio_value は broker.get_available_cash() から取得して初期化。
- Paper Trading の振る舞い（PAPER_FILL_MODE）を Settings で検証し、無効な値は ValueError を送出する。

Acknowledgements
- 本 CHANGELOG は提供されたソースコードを元に機能追加・設計意図を推測して作成しています。実際のリリース履歴やバージョン管理履歴と差異がある可能性があります。必要であれば、Git コミット履歴やリリースノートに合わせて調整してください。