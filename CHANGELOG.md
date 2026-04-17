# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
リリース日はコードベースの作成・更新内容から推測して記載しています。

## [Unreleased]
（現時点で未リリースの差分はありません）

## [0.1.0] - 2026-04-17
初期リリース。KabuSys のコア機能群を実装しました。本バージョンでは環境設定、実行・監視エントリポイント、ポートフォリオ構築ロジック、実行系の補助、レポートツール、リサーチ用ファクター計算、ユーティリティ等を提供します。

### Added
- 基本構成
  - パッケージ初期化: kabusys.__version__ = "0.1.0" を設定。
  - Settings クラス（kabusys.config）: 環境変数経由の設定取得をプロパティで提供（J-Quants、kabu API、DB パス、監視閾値、実行環境判定など）。
  - .env 自動読み込み機能:
    - プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動的に読み込み。
    - OS 環境変数を保護しつつ .env.local で上書きする挙動を採用。
- 環境設定関連 CLI
  - config_setup（kabusys.config_setup）: 対話式ウィザードで .env を初期作成／更新する機能を追加。出力テンプレートは機密情報の扱いに注意する旨のコメント付きで保存。
  - validate_config（kabusys.validate_config）: .env と config/*.yaml を起動前に検証する CLI を実装。--strict オプションで警告を失敗扱いにできる。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ確認、YAML ファイルの存在および（PyYAML があれば）パース検証、本番向けガードなどを実装。
- 実行・監視エントリポイント
  - run_execution（kabusys.run_execution）:
    - 実行エンジンの起動スクリプト。プロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全に分離。
    - BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと実行ループを提供。停止フラグ (data/stop_requested.flag) と PID ファイル制御を実装。
    - RiskManager の既定設定（max_position_pct 等）と initial_portfolio_value を broker.get_available_cash() から取得して初期化。
  - run_monitoring（kabusys.run_monitoring）:
    - システム監視ループの起動スクリプト。プロセス優先度を "high" に設定。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視は本番用 sqlite_path を参照（KABUSYS_ENV に関わらず本番の monitoring DB を使用する設計）。
    - 停止フラグ検知でループを終了。SQLite / DuckDB 接続の適切なクローズを保証。
- 監視 DB 初期化ユーティリティ
  - init_monitoring_db を呼び出して監視用テーブルの存在を保証（冪等な初期化）。
- ユーティリティ
  - process_priority（kabusys.utils.process_priority）:
    - プロセス優先度設定（high/normal/low）を Windows / POSIX(Linux/Mac/FreeBSD) に対応して実装。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応 OS では安全にフォールバックして警告を出力。
- ポートフォリオ構築（pure functions）
  - portfolio_builder:
    - select_candidates: スコア降順・タイブレークロジックで候補選定。
    - calc_equal_weights, calc_score_weights: 等分配・スコア正規化配分。スコア合計が 0 の場合は等分配にフォールバックして警告。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限（既存保有を考慮し、売却予定銘柄は除外）。"unknown" セクターは制限対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（デフォルトで未知レジームは 1.0 にフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数計算。単元（lot_size）丸め、per-stock 上限、aggregate cap（available_cash によるスケーリング）、cost_buffer を考慮したスケーリング／端数配分ロジックを実装。
- リサーチ / ファクター計算
  - research.factor_research:
    - calc_momentum: mom_1m/3m/6m、ma200 乖離を DuckDB 上で計算（window 関数利用）。データ不足時は None を返す。
    - calc_volatility: ATR、相対 ATR、20日平均売買代金、出来高比率等を計算（実装済みの一部を含む）。
    - DuckDB 接続を想定し prices_daily / raw_financials テーブルのみ参照する純粋関数群。
- ツール
  - tools.paper_verification_report:
    - Paper Trading 用検証レポート生成スクリプト。期間指定（--from / --to）と DB 指定（--db）をサポート。
    - システム稼働率、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計し、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）に基づき PASS/FAIL を判定。
    - 日付フィルタ、NULL 考慮、P95 計算ユーティリティ等を実装。

### Changed
- （初期リリースのため変更履歴なし）

### Fixed
- .env パーサー（kabusys.config._parse_env_line）
  - export プレフィックス対応、クォート文字（シングル/ダブル）のエスケープ対応、インラインコメント処理の改善を実装。より堅牢な .env パースを実現。
  - _load_env_file は読み込み失敗時に警告を発するようにし、OS 環境変数の保護を考慮した上で override 処理を行う。
- validate_config:
  - PyYAML がインストールされていない場合は YAML 検証をスキップして警告を出す（パーサ不在の graceful fallback）。
- run_monitoring / MONITOR_POLL_INTERVAL:
  - 環境変数が不正（0 以下や非整数）の場合に警告を出してデフォルト値にフォールバックする安全化を実装。

### Security
- .env 出力（config_setup の _write_env）に「.env を Git にコミットしない」旨の明確な注意コメントを含めるなど、機密情報取り扱いに関する注意を同梱。

### Notes / Misc
- 各モジュールは「DB 参照なし」で動作する純粋関数群（ポートフォリオ関連）と、DuckDB/SQLite を用いる分析・監視・実行周りで分離された設計を採用しています。
- 実運用での本番ガード（KABUSYS_ENV=live の警告や kill flag の扱い等）を組み込み、開発・ペーパートレード・本番を意識した挙動になっています。
- 今後の改善候補として、position_sizing の銘柄別 lot_size サポート、price のフォールバックロジック、monitoring の詳細メトリクス強化などがコメントとして残されています。

---

（補記）この CHANGELOG は提供されたコードベースの実装内容から推測してまとめたもので、コミット履歴や実際のリリースノートがある場合はそちらを優先してください。