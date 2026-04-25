CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-25
--------------------

Added
- 初回リリースを公開。
- 実行エントリポイントを追加:
  - run_execution.py — ExecutionEngine 起動スクリプト。KABUSYS_ENV に応じて本番 / ペーパートレード用の DB・ブローカークライアントを切替え、デーモンスレッドでエンジンを実行。停止フラグ（data/stop_requested.flag）および PID ファイルの取り扱いを実装。
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視用 DB 初期化と DuckDB 接続を行い、停止フラグで安全終了。
- 設定/環境変数管理:
  - config.py — .env 自動読み込み（.env, .env.local）、プロジェクトルート検出（.git / pyproject.toml 基準）、.env 行パーサ（export プレフィックス、引用符付き値、インラインコメントの扱い等）、Settings クラス（J-Quants / kabuAPI / DB パス / 監視閾値 / 環境判定などのプロパティ）を実装。
- 対話式設定ウィザード:
  - config_setup.py — .env の初期作成・更新を支援する CLI ウィザードを追加。既存値読み取り、シークレットマスク表示、保存テンプレート出力を実装。
- 設定検証 CLI:
  - validate_config.py — .env と config/*.yaml の事前検証ツールを追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パス・YAML ファイル存在とパース（PyYAML 無しでも graceful）や本番環境向けガード（LINE 通知設定や Kill Switch 設定の警告）を実装。--strict オプションで警告を失敗扱いに可能。
- ロギングユーティリティ:
  - utils/logging_setup.py — 統一ログ設定関数 setup_logging を追加。コンソール（stdout）出力と日次ローテートのファイル出力（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時にはファイル出力をスキップしてコンソールのみで継続。
- プロセス優先度・CPU affinity ユーティリティ:
  - utils/process_priority.py — set_process_priority（Windows / POSIX の差分を吸収）、set_cpu_affinity（最初の N コアに固定）を追加。権限不足や未対応 OS では警告を出してスキップ。
- ポートフォリオ構築関連（純粋関数群）:
  - portfolio/portfolio_builder.py — 候補選定（select_candidates）・等分配（calc_equal_weights）・スコア重み（calc_score_weights）を実装。スコアが全て0の際は等分配にフォールバック。
  - portfolio/risk_adjustment.py — セクター集中制限 apply_sector_cap（unknown セクターは上限適用除外）、市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear）を実装。
  - portfolio/position_sizing.py — allocation_method（"risk_based" / "equal" / "score"）対応の株数計算を実装。単元株（lot_size）丸め、1 銘柄上限・総投下資金上限（aggregate cap）に基づくスケーリング、cost_buffer を考慮した保守的見積り、残差処理による追加配分などをサポート。
  - portfolio/__init__.py でエクスポートをまとめた。
- Paper Trading 検証ツール:
  - tools/paper_verification_report.py — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から各種指標（稼働率、注文成功率/送信率、リスク却下数、レイテンシ統計、P95 等）を集計してレポート出力する CLI を追加。閾値による PASS/FAIL 判定を実装。
- モニタリング DB 初期化支援:
  - monitoring.monitoring_db.init_monitoring_db を適所で呼び出して監視用テーブルの存在を保証（冪等）。
- DuckDB を分析用 DB として統合: 各種コンポーネントで duckdb 接続を利用。
- パッケージメタ:
  - __init__.py に __version__ = "0.1.0" を追加。

Changed
- （初回リリースのため該当なし）

Fixed
- 環境変数パース時の堅牢性向上:
  - MONITOR_POLL_INTERVAL の文字列→整数変換に失敗した場合や 0 以下の値が指定された場合にデフォルト (60秒) にフォールバックして警告を出す実装を追加。
  - .env 読み込みは OS 環境変数を保護するための protected セットを導入し、.env.local での上書き挙動を明確化。
- ログ設定でログディレクトリ作成失敗時にプロセスが中断しないようフォールバック（コンソール出力のみ）を実装。
- プロセス優先度設定で権限不足や未対応環境を graceful に扱うように変更（警告ログを出してスキップ）。

Security
- .env ファイルは暗黙的に秘密情報を含むため、config_setup の出力テンプレートに「絶対に Git にコミットしないこと」を注記。

Notes / Known limitations
- research/factor_research.py（ファクター計算モジュール）は設計方針と定数、calc_momentum の冒頭が実装されているが、ファイル末尾が途中で切れている（実装の続きが必要）。本リリースでは分析基盤の骨組みを追加した形。
- ExecutionEngine 側で使用する BrokerClientFactory、ExecutionEngine、OrderManager などは起動フローと依存関係の組み立てを実装済みだが、外部ブローカー API の挙動や MockBroker の詳細は別モジュールに依存する。ペーパートレード用 DB と本番 DB は分離されるが、実運用前に validate_config と追加テストで設定を必ず確認してください。
- Kill Switch / stop flag の運用に注意。validate_config にて KILL_FLAG_CLEAR_ON_START の設定が本番で危険となる場合は警告を出すようにしている。

Breaking Changes
- （初回リリースのため該当なし）