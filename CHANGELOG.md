CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。
リリース日: 2026-04-19

[Unreleased]: https://example.com/kabusys/compare/HEAD...HEAD

0.1.0 - 2026-04-19
-----------------

Added
- 基本リリース: パッケージ初回公開相当の機能群を追加。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト直下の data/stop_requested.flag ファイルで検知。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する実装。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使い MockBrokerClient を利用する分離設計。
    - エンジン用の PID ファイル管理、停止フラグ検知、スレッドでの実行制御を実装。
    - 起動時にプロセス優先度を High にセット。

- 設定管理
  - config.py:
    - .env ファイル自動ロード機能を実装（.env / .env.local、OS 環境変数を保護）。
    - export KEY=val 形式やクォート、インラインコメント、エスケープ等に対応したパーサを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
    - Settings クラスを導入し、環境変数の型変換・バリデーションを提供（env, log_level, 各種パス, paper_fill_mode など）。
    - paper_trading 用 DB パス、各種閾値・フラグをプロパティとして定義。

- 設定ユーティリティ / CLI
  - config_setup.py: .env の初期作成・更新を対話式に支援するウィザードを追加。
    - シークレット項目はマスク表示。既存 .env の読み込み・再利用が可能。
  - validate_config.py: 起動前に .env および config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリチェック、YAML パース（PyYAML があれば実施）、本番環境用の追加ガード、--strict オプションを提供。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定するユーティリティを追加。
    - LOG_LEVEL / LOG_DIR の解決順を実装し、ファイル作成失敗時はコンソールのみで動作するフォールバックを実装。
  - utils/process_priority.py:
    - psutil を用いて Windows / POSIX の差を吸収するプロセス優先度設定を実装（high/normal/low）。
    - CPU affinity 設定用の set_cpu_affinity を追加。権限や未サポート環境では警告を出してスキップ。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py:
    - シグナル選定（select_candidates）と配分重み算出（calc_equal_weights, calc_score_weights）を実装。
    - calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックして警告を出す。
  - portfolio/risk_adjustment.py:
    - セクター集中制限を行う apply_sector_cap を追加（現ポジション・価格情報・売却予定除外考慮）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear のマッピング）。
  - portfolio/position_sizing.py:
    - 株数決定ロジック calc_position_sizes を実装（risk_based / equal / score をサポート）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash 超過時のスケーリング）、cost_buffer による保守的見積りを実装。
    - 価格欠損時のスキップやスケーリング時の残余配分ロジックを含む。

- 分析 / ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成スクリプトを追加（期間指定可能）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し基準値と比較して PASS/FAIL を判定する。
    - デフォルト DB パスは data/paper_trading.db。P95 計算や各テーブル存在チェックに耐性あり。

- 研究用モジュール（部分実装）
  - research/factor_research.py:
    - モメンタム等のファクター計算基盤を追加（DuckDB の prices_daily, raw_financials を参照する設計）。
    - 設計に関するドキュメントコメントを含む（1M/3M/6M リターン、MA200 乖離、ATR、流動性指標等）。

Changed
- ロギングのデフォルトを stdout に統一（cron / Scheduler 環境を考慮）。
- .env のパース仕様を強化（エクスポート形式、クォート、エスケープ、インラインコメントの扱い）。
- 設定ロードの優先度を OS 環境 > .env.local > .env に明確化。OS 環境変数は保護され自動上書きされない。
- ExecutionEngine の DB 接続は KABUSYS_ENV=paper_trading の際に paper_trading 用 DB を使用するように分離。

Fixed
- （初回リリースのため該当項目なし）

Deprecated
- （初回リリースのため該当項目なし）

Security
- （初回リリースのため該当項目なし）

注記 / 既知の制限
- research/factor_research.py は設計と一部実装を含みますが、ファイル末尾が途中で切れているため完全実装が必要です（今後の追加実装対象）。
- position_sizing や apply_sector_cap の価格欠損時の処理については将来的にフォールバック価格（前日終値や取得原価）を導入して改善することが検討されています（コード内 TODO）。
- process_priority / set_cpu_affinity は権限不足やプラットフォーム非対応時に警告を出して処理をスキップします。運用環境での挙動は事前に検証してください。

--- 
この CHANGELOG はコードベースから推測して作成したものであり、実際のコミット履歴に基づくものではありません。必要に応じて日付や項目の微調整を行ってください。