# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
新しいバージョンはセマンティックバージョニングに準拠します。

<!--
Keep a Changelog — https://keepachangelog.com/ja/1.0.0/
-->

## [Unreleased]

## [0.1.0] - 2026-04-24

### Added
- 基本パッケージ初期実装を追加（KabuSys v0.1.0）。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用することで本番 DB と完全分離する設計。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の実行制御（スレッド起動、停止フラグ検出、PID ファイル管理）。
    - 設定に基づく RiskConfig（デフォルト値: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, 等）を適用。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境（KABUSYS_ENV）に関わらず本番用 sqlite_path を使用する挙動。
    - 停止フラグ（data/stop_requested.flag）の検出による安全終了。
- 設定管理
  - config.py
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 独自の .env パーサ実装（export プレフィックス、シングル／ダブルクォート、エスケープ、インラインコメント処理に対応）。
    - Settings クラスにより各種環境変数をプロパティとして提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KABUSYS_ENV 等）。
    - 環境検証（値のバリデーション）と boolean フラグ API（is_live / is_paper / is_dev）。
  - config_setup.py
    - 対話式ウィザードにより .env の初期作成・更新を支援。シークレット項目はマスク表示、既存値の読み込み・再利用に対応。
    - .env を安全に出力するユーティリティ（.env は Git にコミットしない旨のヘッダを付与）。
  - validate_config.py
    - 起動前に .env と config/*.yaml の検証を行う CLI。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードを実装。
    - --strict モード（警告も失敗扱い）に対応。
- ポートフォリオ構築（純粋関数群: DB 参照なし）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順＋タイブレークに基づく候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限（max_sector_pct に基づく新規候補除外）。"unknown" セクターは集中制限の対象外。
    - calc_regime_multiplier: market レジーム（bull / neutral / bear）に基づく投下資金乗数を返却。未知のレジームは 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数算出、単元株丸め（lot_size）や per-position / aggregate の上限処理、cost_buffer を用いた保守的コスト見積り、aggregate cap によるスケーリングと remainder による追加配分ロジックを実装。
- 解析・リサーチ
  - research/factor_research.py（モメンタム等ファクター計算の骨格実装）
    - DuckDB を利用した prices_daily/raw_financials 参照ベースのファクター計算設計（モメンタム、MA200乖離、ATR、出来高等）。（ファイル末尾は計算ロジックの続きあり）
- ユーティリティ
  - utils/logging_setup.py
    - 統一ロギング設定ユーティリティ。StreamHandler を stdout に出力し、TimedRotatingFileHandler で日次ローテーション（デフォルト logs/<app_name>.log、30 日保持）。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - Windows/Linux（POSIX）差分を吸収したプロセス優先度設定（high/normal/low）。
    - CPU affinity を設定する set_cpu_affinity ユーティリティを追加。
    - アクセス権等で失敗した場合は警告を出して安全にスキップ。
- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite から稼働率、注文成功率、送信率、レイテンシ指標（P95 等）を集計してレポート出力する CLI。
    - デフォルト閾値を設定（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）して PASS/FAIL 判定を行う。
    - --from / --to / --db オプションに対応。
- パッケージメタ
  - __init__.py にてバージョンを定義: __version__ = "0.1.0"。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （該当なし）

### Notes / Known issues / TODO
- config.py / .env パーサはかなり柔軟だが、極端に複雑な .env のケースで差異が出る可能性あり。
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に欠損（0.0）があるとエクスポージャーが過少見積りされ、期待するブロックが行われない可能性あり（TODO コメントあり）。将来的に前日終値や取得原価でのフォールバックを検討する必要がある。
- portfolio/position_sizing:
  - 単元株 (lot_size) は現状グローバル固定。将来的に銘柄別 lot_map をサポートする計画あり（TODO コメント）。
- utils/logging_setup:
  - ログディレクトリ作成に失敗した場合は stderr に警告を出し、ファイル出力を無効化する（設計上の意図）。CI / コンテナ環境での権限問題に注意。
- utils/process_priority:
  - プロセス優先度・CPU affinity の設定は権限不足やプラットフォーム差により失敗する可能性があり、その場合は警告をログに出して処理をスキップする。
- run_monitoring:
  - 監視は「環境にかかわらず本番 sqlite_path を使用する」仕様となっているため、ローカルテスト時に意図せず本番 DB を参照しないよう環境変数設定に注意。
- validate_config:
  - PyYAML が存在しない場合は config/*.yaml のパース検証をスキップする挙動（警告を出力）。
- research/factor_research.py:
  - ファイル末尾で計算ロジックが途中で切れている（snapshot の都合）。実装の続きを要確認。

---

この CHANGELOG はコードベース（src/ 以下）から推測して作成しています。実際のリリースノートとして公開する場合は、実際のコミット履歴やマージノートを参照して差分・日付・著者情報を補完してください。