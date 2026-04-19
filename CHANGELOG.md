# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルはプロジェクトの主要な追加・変更点を人間向けにまとめたものです。

フォーマット:
- 変更はセクションごとに分類（Added / Changed / Fixed / Deprecated / Removed / Security）
- バージョンはセマンティックバージョニングを使用

## [Unreleased]

## [0.1.0] - 2026-04-19

### Added
- 初回リリース。以下の主要コンポーネントを追加。
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine の起動エントリポイントを提供。
    - KABUSYS_ENV により paper_trading モードでは MockBrokerClient を利用し、paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）に記録する仕組みをサポート。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ (data/stop_requested.flag) を監視し、フラグで安全に停止可能。
    - エンジンは別スレッドで実行され、スレッド監視により停止時に engine.stop() を呼び出す。
  - run_monitoring.py
    - SystemMonitor の起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。不正値はログ警告のうえデフォルトにフォールバック。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様。
    - 停止フラグ (data/stop_requested.flag) によりポーリングループを終了可能。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - config.py
    - .env 自動読み込み（.env → .env.local、OS 環境変数を保護）。
    - .env パースは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
    - Settings クラスを提供し、各種設定（J-Quants / kabu API / DB パス / paper trading 設定 / 監視しきい値 / 環境判定等）をプロパティ経由で取得可能。
    - 設定値検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）を実装。無効値時は例外を投げる設計。
    - settings インスタンスをモジュールレベルで提供。
  - config_setup.py
    - .env の対話式ウィザード（初期作成・更新）を追加。
    - 秘匿項目のマスク表示、選択肢サポート、既存 .env 読込・Enter で再利用等のユーザーフレンドリーな対話式 UI。
    - 最終確認後に .env をファイルへ書き出す機能。
  - validate_config.py
    - 起動前に .env と config/*.yaml の整合性・不足を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在チェック、YAML のパース（PyYAML 利用）等を実施。
    - --strict オプションで警告も失敗として扱うモードを提供。
- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - setup_logging 関数を実装。StreamHandler（stdout）と TimedRotatingFileHandler（デフォルト logs/<app_name>.log、日次ローテーション、30日保持）をルートロガーに設定。
    - 既存ハンドラをクリアして二重設定を防止。
    - LOG_LEVEL / LOG_DIR の環境変数や関数引数で挙動を変更可能。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしコンソール出力のみで継続。
  - utils/process_priority.py
    - set_process_priority(level) を実装。Windows / POSIX 系を吸収して nice 値や Windows 優先度クラスを設定。
    - set_cpu_affinity(cpu_count) を実装（指定が None の場合は変更なし）。権限不足などは警告でスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコアが全て 0 の場合は等金額配分にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装。既存保有を基にセクターごとの時価総額を計算し、上限を超えるセクターの新規候補を除外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をサポート、未知レジームは警告のうえ 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数を計算する calc_position_sizes を実装。
    - allocation_method: "risk_based", "equal", "score" をサポート。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超えた場合のスケールダウン）、cost_buffer（手数料・スリッページ見積り）等を考慮。
    - スケーリング後の残差配分を公平に行うロジックを備える。
- Paper Trading ツール
  - tools/paper_verification_report.py
    - ペーパートレーディング結果の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs テーブルから稼働率、注文成功率、送信率、レイテンシ等を算出。
    - P95 レイテンシ計算、閾値による PASS/FAIL 判定（デフォルト閾値をコード内で定義）。
    - コマンドライン引数 --from / --to / --db をサポート。環境変数 PAPER_TRADING_SQLITE_PATH も利用可能。
- 研究用モジュール（着手）
  - research/factor_research.py
    - モメンタム等のファクター計算モジュールを追加（DuckDB を用いた prices_daily / raw_financials 参照設計）。モジュールに定数と calc_momentum の骨組みを実装（以降の実装は継続予定）。
- パッケージ情報
  - __init__.py にて __version__ = "0.1.0" を設定。

### Changed
- n/a（初回リリースのため過去からの変更履歴は無し）

### Fixed
- n/a（初回リリース）

### Deprecated
- n/a

### Removed
- n/a

### Security
- n/a

---

注記:
- 本 CHANGELOG はソースコードの実装・コメントから推測して作成しています。実際の動作や外部依存（例: BrokerClientFactory の実装、SystemMonitor の詳細、DuckDB/SQLite のスキーマ等）は別途ドキュメントや実装仕様を参照してください。
- 将来的に各モジュール（特に research や execution 関連）の詳細な動作や API 仕様を CHANGELOG に追記していくことを推奨します。