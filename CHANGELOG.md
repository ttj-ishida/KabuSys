CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

0.1.0 - 2026-04-19
------------------

Added
- 基本アプリケーション構成とバージョン情報を追加
  - pkg: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 起動スクリプト / 実行コンポーネント
  - run_monitoring: 監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ (data/stop_requested.flag) を検知して安全にループ終了。
    - SystemMonitor の初期化と定期実行（SQLite / DuckDB 接続を使用）。
    - プロセス優先度設定 (set_process_priority) と統一ログ設定 (setup_logging) を導入。
  - run_execution: ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 専用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler 等を組み立てて ExecutionEngine を実行。
    - 停止フラグ (data/stop_requested.flag) と PID 管理 (data/execution.pid) に対応。
    - プロセス優先度を High に設定。

- 設定・検証・ウィザード
  - Settings クラス（src/kabusys/config.py）を追加:
    - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
    - 必須値取得ヘルパー _require, 各種パス / フラグ /閾値プロパティを提供（DB パス、PID パス、paper_trading 用パス、閾値等）。
    - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の検証ロジックを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - 設定検証 CLI（src/kabusys/validate_config.py）を追加:
    - .env の必須変数チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パス・config/*.yaml の存在とパース検証（PyYAML がない場合はスキップ）を実行。
    - --strict オプションで警告を FAIL 扱いにできる。
  - 設定ウィザード（src/kabusys/config_setup.py）を追加:
    - 対話的に .env を生成・更新するウィザード。
    - 既存 .env の読み込み・編集、シークレットマスキング、確認後ファイル書き込み機能を提供。

- ユーティリティ
  - ロギング初期化ユーティリティ（src/kabusys/utils/logging_setup.py）を追加:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション）を設定。
    - ログディレクトリ自動作成、環境変数/引数によるログレベル・ログディレクトリ解決。
    - 既存ハンドラをクリアして二重設定を防止。
  - プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）を追加:
    - Windows / POSIX の差分を吸収し、set_process_priority("high" | "normal" | "low")、set_cpu_affinity(n) を提供。
    - 権限不足等のエラーは警告にフォールバック。
  - .env パーサーの堅牢化:
    - export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理に対応。
    - _load_env_file で OS 環境変数を保護する protected 機能を実装（.env.local 上書き時に OS 環境を壊さない）。

- ポートフォリオ構築（純関数群）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）:
    - 候補選定 select_candidates（スコア降順 + タイブレーク）、等重み calc_equal_weights、スコア加重 calc_score_weights を追加。
    - スコアが全て 0 の場合は等分配へフォールバック。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）:
    - セクター集中制限 apply_sector_cap を実装（売却予定銘柄を除外、"unknown" セクターを無視）。
    - レジーム乗数 calc_regime_multiplier を実装（bull/neutral/bear マップ、未知は 1.0 でフォールバック）。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）:
    - allocation_method による株数計算を実装（"risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金に合わせてスケールダウン）、
      cost_buffer を考慮した保守的推定、端数処理（fractional remainder に基づく追加配分）を実装。
  - portfolio パッケージの __init__ を整備して上記関数をエクスポート。

- Research / 分析
  - factor_research（src/kabusys/research/factor_research.py）を追加:
    - StrategyModel に基づくモメンタム / Value / Volatility / Liquidity の方針と定数を定義。
    - calc_momentum の骨格を追加（DuckDB 接続を受け取り prices_daily を参照して計算する設計）。※実装は継続の余地あり。

- Paper Trading 検証ツール
  - tools.paper_verification_report（src/kabusys/tools/paper_verification_report.py）を追加:
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）からシステム稼働率、注文成功率、送信率、レイテンシ等を集計してレポート出力。
    - P95 計算、閾値に基づく PASS/FAIL 判定、日付フィルタ機能（--from/--to）、DB パスの指定（--db / 環境変数）に対応。

Changed
- ログ出力の標準化:
  - 全起動スクリプトは setup_logging を先頭で呼び出すことを期待（統一ログフォーマット / 日次ローテーションの導入）。
  - StreamHandler は stdout に出力するように変更（stderr を避ける設計）。

Fixed
- .env 読み込みでの上書き制御を追加:
  - .env.local の override を許可しつつ OS 環境変数は保護するよう挙動を明確化。これにより CI / システム環境変数を誤って上書きするリスクを低減。

Notes / Implementation details
- ファイルベースのフラグ / PID 管理:
  - 停止フラグや PID ファイル (/data/*.pid, stop_requested.flag) を用いたプロセス制御・安全停止に対応。
- DB 取り扱い:
  - monitoring 用 SQLite（settings.sqlite_path）と分析用 DuckDB（settings.duckdb_path）を明確に分離。
  - run_execution は paper_trading 環境時に専用 paper_sqlite_path を使用することで本番 DB とデータ分離を実現。
- セキュリティ注意:
  - .env ファイルは生成時にコメントで "絶対に Git にコミットしないこと" を明示。
  - config_setup ではシークレット値はマスクして表示する。

Deprecated / Removed / Security
- なし（初回リリースとして現時点で該当なし）。

今後の予定（想定）
- factor_research 内の各ファクター計算の完全実装と単体テストの追加。
- ExecutionEngine / BrokerClient 周りの詳細実装と統合テスト（モックブローカーの充実）。
- config/*.yaml の生成スクリプトとデフォルトテンプレートの提供強化。
- 単体テスト・CI 設定の追加、型アノテーションの強化。

---
注: ここに記載した変更はソースコードの内容から推測してまとめたものです。実際のコミット履歴やリリースノートと差分がある場合があります。必要であれば特定のファイルや機能についてさらに詳細な説明・分割されたリリースノートを作成します。