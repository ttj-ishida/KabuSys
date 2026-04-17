# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
（この CHANGELOG は与えられたコードベースの内容から推測して作成しています。）

## [Unreleased]

## [0.1.0] - 2026-04-17

### Added
- 基本アプリケーションパッケージを実装（kabusys パッケージ、バージョン 0.1.0 を package 情報に設定）。（src/kabusys/__init__.py）
- 環境設定/読み込み・検証関連
  - 環境変数と .env の自動読込機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。OS 環境変数を保護するオプションあり。（src/kabusys/config.py）
  - .env ファイルのパースを強化：export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント判定等に対応。（src/kabusys/config.py）
  - Settings クラスを実装し、アプリケーションで利用する主要な設定プロパティを提供（J-Quants / kabu API / DB パス / 監視閾値 / 環境判定など）。（src/kabusys/config.py）
  - 対話式ウィザードで .env を生成・更新する CLI を追加（保存前確認あり）。デフォルト値や説明を含むプロンプトを提供。（src/kabusys/config_setup.py）
  - 起動前チェック用 CLI を追加（環境変数・config/*.yaml の存在と簡易パース検証、--strict オプションで警告を失敗扱いにできる）。本番時のガード（LINE トークンの未設定など）も実装。（src/kabusys/validate_config.py）
- 実行・監視エントリポイント
  - ExecutionEngine 起動スクリプトを追加。paper_trading 環境時は Mock 用 DB を分離して使用（data/paper_trading.db がデフォルト）。停止フラグ / PID 管理 / スレッドでの実行をサポート。（src/kabusys/run_execution.py）
    - Execution 起動時にプロセス優先度を "high" に設定するフローを追加。
    - BrokerClientFactory を利用してブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - RiskManager にデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を注入。
  - SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。（src/kabusys/run_monitoring.py）
    - 停止フラグファイル（data/stop_requested.flag）を検知してループ終了。
- 監視用 DB 初期化ユーティリティを利用する呼び出しを追加（init_monitoring_db の呼び出しにより監視テーブルが存在することを保証）。（run_execution/run_monitoring）
- DuckDB を分析用 DB として利用する接続を各所で確保（Settings.duckdb_path を使用）。（run_execution/run_monitoring, research モジュール）
- プロセス優先度 / CPU affinity ユーティリティを実装（psutil ベース、Windows と POSIX の差分吸収、権限不足時は警告でスキップ）。（src/kabusys/utils/process_priority.py）
  - set_process_priority(level: "high"|"normal"|"low")
  - set_cpu_affinity(cpu_count: Optional[int])
- ポートフォリオ構築関連（純粋関数、DB 非依存）
  - 候補選定と重み付け関数を追加（スコア順ソート、等金額配分、スコア加重配分）。スコアが全て 0 の場合は等配分にフォールバックして警告出力。（src/kabusys/portfolio/portfolio_builder.py）
  - セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。未知レジーム時のフォールバックと警告あり。（src/kabusys/portfolio/risk_adjustment.py）
  - 株数決定ロジック（calc_position_sizes）を実装。allocation_method（risk_based / equal / score）をサポートし、単元株丸め、per-stock 上限、aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer を用いた保守的見積り、lot 単位での残余割当てロジックを含む。（src/kabusys/portfolio/position_sizing.py）
  - portfolio パッケージのエクスポートを整理（select_candidates 等を __all__ で公開）。（src/kabusys/portfolio/__init__.py）
- リサーチ（ファクター計算）
  - DuckDB 接続を受け、prices_daily / raw_financials を基にモメンタム / ボラティリティ等の定量ファクターを算出する関数を追加（calc_momentum, calc_volatility 等の設計・初期実装）。ウィンドウ不足時は None を返す扱い、P95 等の指標を計算する補助ロジックを実装。（src/kabusys/research/factor_research.py）
- ツール
  - Paper Trading 向けの検証レポート生成スクリプトを追加（コマンドラインで期間指定可能）。稼働率・注文成功率・送信率・レイテンシ（avg/max/P95）・リスク却下数を集計し、閾値に基づく PASS/FAIL 判定を出力。デフォルト DB は data/paper_trading.db。（src/kabusys/tools/paper_verification_report.py）
    - 判定閾値（稼働率、成功率、送信率、P95 レイテンシ）を定義し、レポートのフォーマットを整備。
- その他の実装上の配慮
  - Execution / Monitoring の両エントリポイントで起動直後にプロセス優先度を "high" に設定するようにした（set_process_priority 呼出し）。
  - stop/kill フラグファイル、PID ファイル取り扱いを導入し起動/停止の安全性を確保。
  - SQLite/ DuckDB の接続を適切にクローズする finally ブロックを導入。

### Changed
- （初版のため該当なし）

### Fixed
- .env パースの堅牢化により、引用符・エスケープ・コメントによる誤解釈を防止。（src/kabusys/config.py）

### Security
- .env ファイル生成ウィザードで生成した .env の Git へのコミット禁止旨をファイルヘッダに明記。（src/kabusys/config_setup.py）

### Notes / Usage highlights
- MONITOR_POLL_INTERVAL 環境変数で監視ポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。0 以下は無効扱いでデフォルトにフォールバック。（src/kabusys/run_monitoring.py）
- PAPER_FILL_MODE（instant|partial|never|reject）や PAPER_TRADING_SQLITE_PATH による paper_trading の挙動分離をサポート。（src/kabusys/config.py, run_execution.py）
- validate_config CLI により起動前に必須環境変数や config/*.yaml の整合性チェックが可能。--strict を付けると警告も失敗扱いになる。（src/kabusys/validate_config.py）
- ExecutionEngine 起動時は paper_trading 環境なら paper 専用 SQLite を使用し本番 DB と分離する設計。（src/kabusys/run_execution.py）

---

その他、細かなログ出力やデバッグ情報を随所に追加しており、実運用を想定した安全弁（権限不足時の警告、ファイル存在チェック、DB 初期化の冪等性確保等）を盛り込んでいます。