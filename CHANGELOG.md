CHANGELOG
=========

すべての変更は「Keep a Changelog」規約に従って記載しています。  
セマンティックバージョニングを採用しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-21
------------------

Added
- 実行用スクリプトを追加
  - run_execution.py: ExecutionEngine 起動スクリプト。プロセス優先度の設定、PID ファイル管理、停止フラグによる安全停止、paper_trading 用に本番 DB と完全分離された SQLite パスの使用、バックグラウンドスレッドでのエンジン実行を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、停止フラグ検出でのループ終了を実装。

- 設定管理・セットアップ
  - config.py: .env 自動読み込み機能（プロジェクトルート検出：.git / pyproject.toml）、環境変数取得ユーティリティ、各種設定プロパティ（DB パス、Paper Trading 設定、監視しきい値、KABUSYS_ENV 検証等）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - config_setup.py: 対話式 .env ウィザードを実装。シークレットのマスキング表示、デフォルト値・選択肢の提示、.env ファイル書き込み機能を提供。
  - validate_config.py: 起動前の設定検証 CLI を実装。必須環境変数・KABUSYS_ENV・ログレベル・DB パス・config/*.yaml の存在とパース（PyYAML がある場合）・本番環境向けガード項目などを検査。--strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 全アプリケーション共通のロギング設定。stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler をルートロガーに設定。LOG_DIR / LOG_LEVEL / 引数での上書き対応。既存ハンドラのクリアで二重出力を防止。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定（Windows / POSIX 対応）と CPU affinity 設定ユーティリティ。psutil の制限や権限不足は警告ログでスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、タイブレークに signal_rank）と等重配分・スコア重み計算を実装。スコアが全て 0 の場合は等配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中上限（apply_sector_cap）および市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。unknown セクターはセクター上限を適用しない挙動。
  - portfolio/position_sizing.py: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算を実装。単元株（lot_size）丸め、1 銘柄上限 / 投下合計上限（aggregate cap）に基づくスケーリング、cost_buffer による保守的コスト見積り、残差配分ロジックを実装。

- ツール・レポート
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。システム稼働率・注文成功率・送信率・リスク却下数・レイテンシ（平均/最大/P95）を集計し、閾値に基づく PASS/FAIL 判定を出力。コマンドライン引数で期間・DB を指定可能。

- リサーチ（骨組み）
  - research/factor_research.py: ファクター計算モジュールの設計とモメンタム計算関数の実装開始（prices_daily テーブルを使った各種モメンタム、MA200 乖離、ATR, ボリューム指標等を想定）。DuckDB 接続を受け取りロジックを実行する方針。

- パッケージ情報
  - __init__.py にバージョン __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ に追加。

Changed
- DB/実行分離の明確化
  - 実行 (Execution) は KABUSYS_ENV=paper_trading の場合に paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と完全分離する設計を反映。
  - 監視用（monitoring）は環境にかかわらず本番の sqlite_path を使用する仕様を明示（監視は常に本番データを参照）。

- 環境変数読み込みの堅牢化
  - .env のパースで export プレフィックス対応、クォート文字列内のバックスラッシュエスケープ、インラインコメントの扱いを改善。_load_env_file において既存 OS 環境変数を保護する protected 機能を導入。

- ロギングの挙動改善
  - 標準出力 (stdout) を使用するように変更（cron 等で stdout/stderr を一本化しやすくするため）。ログディレクトリ作成に失敗した場合はファイル出力を無効化して stdout のみで継続。

Fixed
- 実行開始時の監視テーブル確保
  - run_execution にて init_monitoring_db を呼び出し、monitoring テーブルが存在することを冪等に保証（初回起動や空ディレクトリ環境での失敗回避）。

- 環境値の妥当性チェック
  - Settings.paper_fill_mode の入力値検証、Settings.env/ log_level の有効値チェックにより無効な環境変数設定での早期検出を追加。

Notes / Known issues
- portfolio/risk_adjustment.apply_sector_cap: price が 0.0（欠損）の場合にエクスポージャーが過少見積りされる懸念があり、前日終値等のフォールバック価格導入を TODO コメントで残しています。
- research/factor_research.calc_momentum は実装が途中でファイル末尾が切れている（骨組みと設計方針は含む）。今後の実装でファクター群の計算ロジックを完成させる予定。
- 一部モジュールは外部ライブラリ（psutil, duckdb, PyYAML）に依存しており、環境により機能制限（警告でスキップ）される箇所があります。validate_config は PyYAML 未インストール時に YAML 検証をスキップします。

Security
- （このリリースで特記すべきセキュリティ修正はありません）

---

今後の予定（例）
- factor_research の完全実装とユニットテスト追加
- Portfolio/Execution ロジックの統合テスト、ペーパートレードの検証強化
- より詳細なログ監視 (metrics/Prometheus 等) とアラート連携の強化

（本 CHANGELOG はソースコードの構成・コメントから推測して作成しています。実際のコミット履歴とは異なる場合があります。）