# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従っています。

最新リリース
=============

Unreleased
----------

- （現在未リリースの変更はありません）

v0.1.0 - 2026-04-19
------------------

Added
- プロジェクト初期リリース。
- 基本アーキテクチャと CLI / ユーティリティ群を追加。
  - 実行スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて paper_trading 用 DB を分離して使用（Paper Trading 時は専用の Mock 処理を想定）。停止フラグ（data/stop_requested.flag）検出による安全停止や execution.pid 管理に対応。
    - run_monitoring.py: SystemMonitor を定期実行する監視ループ起動スクリプトを追加。環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する点に注意。
  - 設定関連
    - config.py: 環境変数の安全な読み込みと設定ラッパー（Settings クラス）を追加。自動的にプロジェクトルートの .env / .env.local を読み込む仕組みと、値の検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）を実装。
    - config_setup.py: .env を対話的に作成・更新するウィザード CLI を追加。既存値の読み込み、秘密値のマスク表示、選択肢サポートなど。
    - validate_config.py: .env と config/*.yaml の事前検証用 CLI を追加。必須環境変数のチェックや本番環境向け追加ガードを実装（--strict オプションで警告を FAIL として扱える）。
  - ログ・プロセス管理ユーティリティ
    - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。コンソール（stdout）と日次ローテートファイルハンドラ（logs/<app_name>.log）を構成。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - utils/process_priority.py: Windows/Linux/macOS でプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）と CPU affinity を設定するユーティリティを追加。権限不足等で設定できない場合は警告を出してスキップする安全設計。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py: 候補選定（スコア降順、signal_rank によるタイブレーク）、等金額配分、スコア加重配分を提供。スコアが全て 0 の場合は等配分へフォールバックして警告を出す。
    - portfolio/risk_adjustment.py: セクター集中上限チェック（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知のレジームや unknown セクターのフォールバック動作を明示。
    - portfolio/position_sizing.py: 各銘柄の発注株数を決定するロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。損切り・リスクベース算出、単元株（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer による保守的コスト推定など多数の実用上の考慮を取り入れた実装。
    - portfolio/__init__.py により、主要関数群をパッケージレベルで公開。
  - Paper Trading 検証ツール
    - tools/paper_verification_report.py: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から統計を抽出し、稼働率、注文成功率、送信率、レイテンシ（P95 など）、リスク却下数を計算してレポート出力。閾値による PASS/FAIL 判定を行う（稼働率 >= 99%、成立率 >= 90% など）。
  - 研究/ファクター計算（研究用モジュール）
    - research/factor_research.py: DuckDB 接続を受けて定量ファクター（Momentum, Value, Volatility, Liquidity 等）を計算するための骨組みを追加。モメンタム計算等の定数・設計方針を定義。
  - パッケージメタ
    - __init__.py によりパッケージバージョン __version__ = "0.1.0" を設定。

Changed
- n/a（初回リリースのため履歴なし）

Fixed
- n/a（初回リリースのため履歴なし）

Notes / 実装上の重要事項
- DB 分離:
  - run_execution.py は Paper Trading 運用時に settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用して発注履歴等を本番 DB と完全に分離する。
  - run_monitoring.py は設計上、監視テーブルは常に settings.sqlite_path（デフォルト data/monitoring.db）を使用する（KABUSYS_ENV に依存しない）。
- .env 読み込み:
  - config.py の自動読み込みはデフォルトで有効。テスト等で無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することでスキップ可能。
  - .env ローダは export プレフィックス、クォート、エスケープ、インラインコメント等の実用的なパターンに対応。
- ログ:
  - ログはデフォルトで logs/ 以下に出力（ファイル日次ローテーション、30 日分保持）。ログディレクトリ作成に失敗した場面でもコンソール出力は維持されるよう設計。
- プロセス優先度/affinity:
  - プラットフォーム差異を吸収する実装。権限不足や未対応 OS の場合は安全にスキップして警告ログを出力。
- 安全停止機構:
  - run_execution.py / run_monitoring.py はプロジェクトルートの data/stop_requested.flag を監視し、検出時に安全に停止する仕組みを実装。
- 入力値検証:
  - Settings クラスは環境変数の妥当性検証を行う（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。無効な値は ValueError を投げるため、起動前に validate_config を実行しておくことを推奨。

Deprecated / Removed / Security
- なし（初回リリース）

関連ファイル一覧（主要）
- src/kabusys/run_monitoring.py
- src/kabusys/run_execution.py
- src/kabusys/config.py
- src/kabusys/config_setup.py
- src/kabusys/validate_config.py
- src/kabusys/utils/logging_setup.py
- src/kabusys/utils/process_priority.py
- src/kabusys/portfolio/*.py
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/research/factor_research.py
- src/kabusys/__init__.py

---

フィードバックやバグ報告、機能要望は issue を作成してください。リリースノートは今後の変更に合わせて更新します。