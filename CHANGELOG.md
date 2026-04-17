# Changelog

すべての変更は Keep a Changelog 規約に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース。

### 追加
- パッケージ初期公開: KabuSys — 日本株自動売買システムの基本モジュール群を追加。
  - バージョンは src/kabusys/__init__.py にて 0.1.0 に設定。

- 設定・環境読み込み機能
  - Settings クラス（src/kabusys/config.py）を追加し、環境変数から各種設定を取得する統一インタフェースを提供。
  - .env 自動ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml ベース）。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
  - .env パースの強化: export 形式、クォート文字のエスケープ、インラインコメントの扱いなどに対応。
  - 設定値検証ユーティリティ (src/kabusys/validate_config.py) を追加。必須環境変数・KABUSYS_ENV・ログレベル・DB パス・config/*.yaml の存在/パースなどをチェックし、CLI (--strict) で警告を FAIL 扱いにできる。

- 環境設定ウィザード
  - 対話式 .env 作成/更新ツール (src/kabusys/config_setup.py) を追加。既存値の読み込み、シークレットのマスク表示、確認後の保存機能を提供。

- 実行エントリ / ランナー
  - 実行エンジン起動スクリプト run_execution (src/kabusys/run_execution.py) を追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db）に完全分離して記録。
    - ブローカーファクトリ、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組立ておよびスレッド実行制御を実装。
    - 停止フラグ（data/stop_requested.flag）と PID ファイルの扱いを実装。
    - デフォルトのリスク設定パラメータを設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, max_drawdown=0.20 など）。初期ポートフォリオ値は broker.get_available_cash() を参照して設定。

  - 監視ポーリング起動スクリプト run_monitoring (src/kabusys/run_monitoring.py) を追加。
    - SystemMonitor を初期化しポーリングループで監視を実行。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使う設計（監視データは本番 DB を参照する仕様）。
    - 停止フラグ検出、例外ハンドリング、SQLite / DuckDB 接続のクリーンアップを実装。

- モニタリング DB 初期化
  - init_monitoring_db（監視用テーブルの冪等初期化）呼び出しを導入（run_execution/run_monitoring）。存在確認や初回作成を保証。

- DuckDB / SQLite を利用した分析・永続化
  - DuckDB 接続を受ける設計を採用（分析用 duckdb ファイル: data/kabusys.duckdb デフォルト）。
  - SQLite を監視・注文履歴・ペーパートレード用に利用。

- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収して set_process_priority(level)（high/normal/low）を提供。権限不足や未対応 OS では警告を出してスキップ。
    - set_cpu_affinity(cpu_count) により最初の N コアにピン止め可能（未指定なら全コアを使用）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全てが 0 の場合は等金額配分へフォールバック（警告とともに）。

  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - セクター集中制限適用（apply_sector_cap）。既存保有のセクターエクスポージャを計算して上限超過セクターの候補を除外。
    - レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull=1.0, neutral=0.7, bear=0.3、未知レジームは 1.0 でフォールバック）。

  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - 発注株数算出ロジックを実装。allocation_method="risk_based" / "equal" / "score" をサポート。
    - lot_size（単元株）丸め、1銘柄上限、aggregate cap（available_cash との整合）を考慮したスケーリング・余剰配分アルゴリズムを実装。
    - cost_buffer（スリッページ/手数料見積り）を考慮して保守的にコストを見積もる。

- 研究・ファクター計算
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M、MA200乖離）、Volatility（20日 ATR 等）、流動性指標などを DuckDB の prices_daily テーブルから計算する関数を実装。
    - 欠損データ・ウィンドウ長不足時は None を返すように安全に設計。

- Paper Trading 検証ツール
  - tools/paper_verification_report（src/kabusys/tools/paper_verification_report.py）を追加。
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシなど）を集計してレポート出力。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。
    - 日付レンジ指定（--from, --to）や --db オプションに対応。DB ファイル存在チェックを実施。

- CLI / モジュール実行の利便性
  - 実行可能なスクリプト群は python -m kabusys.<module> で利用可能（config_setup、validate_config、tools.paper_verification_report など）。

### 変更
- なし（初回リリースのため新規追加が中心）。

### 修正
- なし（初回リリース）。

### 既知の注意点 / 実装上の考慮
- Settings.paper_fill_mode は "instant" / "partial" / "never" / "reject" のみ有効。無効値は ValueError を送出する。
- run_monitoring は説明どおり「監視は本番 sqlite_path を使用する」設計。意図的な分離が必要な場合は運用ルールで管理すること。
- process_priority や cpu_affinity の設定は権限やプラットフォームに依存するため失敗した場合は警告を出してスキップする。
- portfolio/risk_adjustment.apply_sector_cap は sector_map にコードがない場合を "unknown" 扱いとして上限判定を適用しない（意図的な動作）。price_map の欠損 (0.0) による過少見積りの注記あり。
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別対応を想定した TODO コメントあり）。

### セキュリティ
- .env ファイルは生成時に「絶対に Git にコミットしないこと」と明記。

---

今後のリリースでは次のような改善を検討しています:
- 銘柄ごとの lot_size サポート、価格フォールバック戦略（前日終値等）
- モニタリング・Execution 間の DB 分離やより細かな運用モード切替
- ファクター・指標の追加とテストカバレッジ拡充

（以上）