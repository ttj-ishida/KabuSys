CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠します。
※ 初回リリースはコードベースから推測して記載しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-17
--------------------

Added
- 基本アーキテクチャと運用用ユーティリティ群を実装
  - 実行スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用の paper DB を使用し MockBrokerClient を利用可能（本番 DB と分離）。起動時にプロセス優先度を High に設定し、停止フラグ（data/stop_requested.flag）を監視して安全に停止可能。エンジンはデーモンスレッドで実行され、PID ファイルを出力。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用する設計。
  - 設定管理
    - config.py: 環境変数と .env の自動読み込み機能を実装（読み込み順: OS 環境変数 > .env.local > .env）。プロジェクトルート探索は .git または pyproject.toml を基準。環境変数の必須チェック用ヘルパ (_require) や各種設定プロパティ（DB パス、KABUSYS_ENV 判定、paper_trading 用設定など）を提供。PAPER_FILL_MODE のバリデーション実装。
    - config_setup.py: .env 作成/更新の対話式ウィザードを実装。テンプレートを書き出す機能を備え、機密値はマスク表示。デフォルトや選択肢付き入力をサポート。
    - validate_config.py: 起動前の設定検証 CLI を実装。.env の必須キー確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml ファイルの存在確認と（PyYAML があれば）パース検証、本番環境向けの追加警告等を行う。--strict オプションで警告を失敗扱いにできる。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - select_candidates: スコア降順かつ tie-breaker に signal_rank を用いた候補選定。
      - calc_equal_weights: 等金額配分。
      - calc_score_weights: スコア比率に応じた重み計算。全銘柄スコアが 0 の場合は等金額配分にフォールバックし警告を出力。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中リスク制御。既存保有額を基にセクター上限(max_sector_pct)を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。sell_codes による当日売却予定の除外対応あり。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3、未知レジームは 1.0 にフォールバックし警告）。
    - portfolio/position_sizing.py
      - calc_position_sizes: risk_based / equal / score の配分方式に対応した発注株数計算。lot_size に基づく丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）によるスケーリング（cost_buffer を加味）、端数扱いの再配分ロジックを実装。
  - 研究・ファクター計算
    - research/factor_research.py: DuckDB 接続を受け取り prices_daily などのテーブルからファクターを計算する実装（Momentum: 1M/3M/6M リターン、MA200 乖離; Volatility: ATR、平均売買代金等）。データ不足時の None 扱い、P95 等の集計に対応。
  - ユーティリティ
    - utils/process_priority.py: Windows / POSIX を透過してプロセス優先度（high/normal/low）と CPU affinity 設定を行うユーティリティを追加。権限不足や未対応環境では安全に警告を出してスキップする。
  - ツール
    - tools/paper_verification_report.py: ペーパートレード用 SQLite (デフォルト data/paper_trading.db) から統計を抽出し検証レポートを標準出力に生成。稼働率、注文成功率、送信率、P95 レイテンシ等の指標算出と閾値判定（デフォルト閾値を定義）を実装。日付フィルタ、DB パス引数をサポート。
  - パッケージメタ
    - __init__.py にて __version__ = "0.1.0" を追加、主要モジュールを __all__ で公開。

Changed
- （初版リリースのため該当なし）

Fixed
- 環境変数パーサの堅牢化
  - config._parse_env_line がクォートを含む値、バックスラッシュエスケープ、export プレフィックス、インラインコメントを適切に扱うよう実装。存在しない .env ファイル読み込み時や IO エラー時に警告を出す。

Security
- .env の取り扱いに関する注意書きと、config_setup が生成する .env を Git にコミットしないよう明記。

Notes / 運用上の注意
- 監視 (run_monitoring.py) は「環境にかかわらず」本番 sqlite_path を使用する設計になっています。監視用 DB を分離したい場合は設定（SQLITE_PATH）を見直してください。
- 実行 (run_execution.py) は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を用いるため、ペーパートレードは本番 DB とは完全に分離されます。
- MONITOR_POLL_INTERVAL に 0 以下や不正な値を設定した場合はデフォルト 60 秒にフォールバックして警告を出力します。
- KILL_FLAG_CLEAR_ON_START の値が 1（自動クリア）は本番では危険な設定となるため validate_config で警告を出すようにしています。
- PyYAML がインストールされていない環境でも validate_config は実行可能であり、YAML の内容検証はスキップされます（警告発生）。
- process_priority / set_cpu_affinity は権限不足や未対応プラットフォームで失敗しても稼働に影響を与えないよう安全にフォールバックします。

今後の予定（推定）
- factor_research の追加ファクターや正規化ユーティリティの統合。
- 個別銘柄の lot_size をマスタ化し position_sizing を拡張。
- モニタリング・監視テーブルやログの拡張（アラート通知/LINE 連携など）。

--- 

（この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のリリースノートは開発履歴に基づき調整してください。）