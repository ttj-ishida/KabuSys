# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは Keep a Changelog に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース。

### Added
- プロジェクト初期構成のコア機能とユーティリティを追加しました。
  - パッケージエントリ情報
    - src/kabusys/__init__.py — バージョン情報 __version__ = "0.1.0" を追加。
  - 設定管理
    - src/kabusys/config.py
      - .env 自動読み込み機能（プロジェクトルートの検出: .git / pyproject.toml を基準）。
      - .env パース実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応）。
      - 環境変数の必須チェック用 _require() と Settings クラス（各種設定プロパティ、デフォルト値、バリデーションを提供）。
      - DB パス、PID/kill フラグ、監視閾値、paper_trading 用設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH など）。
  - 設定関連 CLI
    - src/kabusys/config_setup.py — 対話式ウィザードで .env を初期作成・更新するツールを追加。
      - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 設定等）。
      - 既存 .env 読み取り・上書き、保存確認フローを提供。
    - src/kabusys/validate_config.py — 起動前設定検証 CLI を追加。
      - 必須環境変数・KABUSYS_ENV 値・LOG_LEVEL・DB パス・config/*.yaml の存在・本番時のガード等を検証。
      - --strict オプションで警告を失敗扱いにできる。
  - 実行/監視エントリポイント
    - src/kabusys/run_execution.py
      - ExecutionEngine の起動スクリプト。プロセス優先度設定、paper_trading 時の専用 SQLite DB 分離（data/paper_trading.db がデフォルト）、BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、スレッド起動と停止フラグ監視を実装。
      - 停止フラグ (data/stop_requested.flag) の検出で安全に停止。
      - 実行用 PID ファイルの取り扱い（data/execution.pid デフォルト）。
    - src/kabusys/run_monitoring.py
      - SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境にかかわらず本番 sqlite_path を使用する設計になっている点に注意。
  - モニタリング DB 初期化（Monitoring 側と Execution 側で init_monitoring_db を呼び出し、監視用テーブル存在を保証）。
  - ツール
    - src/kabusys/tools/paper_verification_report.py — Paper Trading の検証レポート生成ツール。
      - 稼働率、注文成功率（fill rate）、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出し PASS/FAIL を判定。
      - 閾値定義（稼働率 >= 99.0%、fill >= 90%、send >= 95%、P95 <= 200ms）。
      - --from / --to / --db オプションをサポート。
  - ポートフォリオ構築関連（純粋関数群）
    - src/kabusys/portfolio/portfolio_builder.py
      - 銘柄候補選定 select_candidates（スコア降順・タイブレークロジック）、等金額配分 calc_equal_weights、スコア重み calc_score_weights（全スコア0 の場合は等金額にフォールバック）。
    - src/kabusys/portfolio/risk_adjustment.py
      - セクター集中上限 apply_sector_cap（既存保有比率が閾値を超えるセクターを新規候補から除外。unknown セクターは除外対象外）。
      - レジーム乗数 calc_regime_multiplier（bull/neutral/bear → 1.0/0.7/0.3、未知レジームは警告のうえフォールバック1.0）。
    - src/kabusys/portfolio/position_sizing.py
      - position sizing ロジック（allocation_method: risk_based / equal / score）。
      - リスクベースの株数算出、単元（lot_size）丸め、1銘柄上限・aggregate cap、cost_buffer を使った保守的見積り、利用可能現金に基づくスケーリングと端数配分アルゴリズムを実装。
    - src/kabusys/portfolio/__init__.py — 上記関数をパッケージエクスポート。
  - リサーチ（DuckDB を使用するファクター計算）
    - src/kabusys/research/factor_research.py
      - モメンタム calc_momentum（1M/3M/6M リターン、MA200 乖離）およびボラティリティ/流動性 calc_volatility（20日 ATR、相対ATR、平均売買代金、出来高比）を実装（prices_daily テーブル参照）。
      - DuckDB 接続を受け、SQL ウィンドウ関数で計算する設計。
  - プロセス制御ユーティリティ
    - src/kabusys/utils/process_priority.py
      - Windows / POSIX の差分を吸収してプロセス優先度設定（high/normal/low）を提供。psutil を使い、Permission エラー時はワーニングを出してスキップ。
      - CPU affinity 設定関数 set_cpu_affinity を追加（指定コア数にプロセスを固定、未サポート環境ではワーニング）。
  - その他ユーティリティ等
    - src/kabusys/tools/__init__.py、src/kabusys/utils/__init__.py（パッケージ初期化）。

### Changed
- N/A（初回リリースのため変更履歴はありません）。

### Fixed
- N/A

### Notes / 実装上の重要なポイント
- .env 自動ロード順:
  - OS 環境変数 > .env.local（上書き） > .env（既存の OS 環境変数は保護）。
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できる。
- .env パーサは export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いに対応しています。正しくない行は無視されます。
- run_monitoring は監視用に「環境にかかわらず本番 sqlite_path を使用」する設計になっています。paper_trading と監視 DB を明確に分離したい場合は設定を見直してください。
- run_execution は paper_trading 環境のときに PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番 DB とデータを分離します。
- process_priority と set_cpu_affinity は権限不足や未対応 OS の場合は警告を出して処理をスキップします（安全側フォールバック）。
- Paper Trading 検証レポートは P95 を簡易実装で算出しています（欠損値処理に注意）。

### CLI / 実行可能スクリプト
- python -m kabusys.config_setup — 対話式 .env ウィザード
- python -m kabusys.validate_config [--strict] — 設定検証
- python -m kabusys.run_execution — ExecutionEngine 起動スクリプト
- python -m kabusys.run_monitoring — SystemMonitor 起動スクリプト
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH] — Paper Trading レポート生成

### Known issues / 注意点
- 一部のモジュールは外部依存（psutil, duckdb, sqlite3, PyYAML（検証用）など）に依存します。validate_config は PyYAML 未インストール時に YAML の検証をスキップします。
- position_sizing, risk_adjustment 等は外部データ（価格、セクターマップ等）に依存します。価格が欠損（0 または None）の場合はスキップや過少見積りになる箇所があるため、運用時は入力データの完全性に注意してください。

<!--
  今後のリリースでは Unreleased セクションに変更を積み上げ、
  リリース時にバージョン別セクションへ移動してください。
-->