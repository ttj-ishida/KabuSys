CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。
リリース日が不明な箇所は推測に基づいています。

[Unreleased]
------------

- なし（初回公開リリース）

[0.1.0] - 2026-04-18
-------------------

Added
- 初回リリース。
- コア機能
  - run_execution.py / run_monitoring.py: 実行エンジンおよび監視ループのエントリスクリプトを追加。
    - run_monitoring:
      - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔指定（デフォルト 60 秒）。
      - 停止フラグ（data/stop_requested.flag）検知による安全停止処理。
      - Monitoring は環境にかかわらず本番 sqlite_path を使用。
      - sqlite3 / duckdb の接続管理と初期化処理（init_monitoring_db 呼び出し）。
    - run_execution:
      - KABUSYS_ENV=paper_trading 時にペーパートレード用 DB を分離（data/paper_trading.db デフォルト）。
      - BrokerClientFactory を介したブローカークライアント生成（Mock の利用を想定）。
      - ExecutionEngine を別スレッドで起動、停止フラグ検知でのグレースフルシャットダウン。
      - PID ファイル（data/execution.pid）管理。
- 設定・環境管理
  - config.py:
    - .env 自動読み込み（プロジェクトルートの検出：.git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順制御（OS 環境変数は保護され上書きされない）。
    - 複数の設定プロパティを提供（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 環境判定 等）。
    - PAPER_FILL_MODE の検証（有効値: instant, partial, never, reject）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
  - config_setup.py:
    - 対話式環境設定ウィザード（.env の生成・更新を支援）。
    - シークレットマスク表示・選択肢・デフォルト値のサポート。
  - validate_config.py:
    - 起動前の設定検証 CLI。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ確認、config/*.yaml の存在・パースチェック（PyYAML が存在する場合）。
    - --strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築（純粋関数群、DB 非依存）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順、同点の場合 signal_rank でタイブレーク。
    - calc_equal_weights, calc_score_weights: 等分配・スコア加重配分（全スコア0 の場合は等分配にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（sell_codes を除外可能、"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: レジーム毎の投下資金乗数（bull/neutral/bear）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数算出。
    - lot_size 単位丸め、max_position_pct / max_utilization による個別・総合上限、cost_buffer による保守的見積り、投下合計が available_cash を超えた場合のスケールダウンロジック（端数の再配分アルゴリズム含む）。
    - デフォルトパラメータ（例: risk_pct=0.005, stop_loss_pct=0.08, max_position_pct=0.10, max_utilization=0.70, lot_size=100）。
- ユーティリティ
  - utils.logging_setup:
    - 統一ロギング設定ユーティリティ。コンソール（stdout）と日次ローテーションファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順、ログディレクトリ作成失敗時のフォールバック（コンソール出力のみ）。
    - デフォルトログディレクトリ: logs/, バックアップ保持 30 日。
  - utils.process_priority:
    - set_process_priority, set_cpu_affinity: Windows/Linux/Mac の差分を吸収してプロセス優先度や CPU affinity を設定（psutil ベース）。
    - 無効な環境や権限不足時は警告を出してスキップ。
- 監視 / 実行に関する安全機構・運用支援
  - stop/kill フラグ、PID ファイル、KILL_FLAG_CLEAR_ON_START 設定等により運用上の Kill Switch をサポート。
  - monitoring_db 初期化をエンジンと監視で共通利用（冪等に DB 構造を保証）。
- リサーチ / ツール
  - research.factor_research（設計・一部実装）: DuckDB を用いたファクター計算の基礎を記述（Momentum 等の計算方針、パラメータ定義）。
  - tools.paper_verification_report:
    - Paper Trading 検証レポート生成スクリプト。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標算出と PASS/FAIL 判定基準を実装（閾値: 稼働率99%、成立率90% 等）。
    - P95 計算、日付フィルタ（ISO8601 UTC でクエリ）をサポート。
- パッケージ情報
  - __init__.py にてパッケージバージョン __version__ = "0.1.0" を追加。

Changed
- 初回リリースのため該当なし。

Fixed
- .env 読み込みにおける細かなパース処理を実装（export プレフィクス対応、クォート内エスケープ、インラインコメントの扱いなど）し、現実的な .env フォーマットへの耐性を向上。
- logging_setup: ログディレクトリ作成失敗時にファイルハンドラ作成をスキップしてコンソールのみで継続する安全策を導入。

Security
- config_setup.py にて .env を生成する際に明示的に「.env は絶対に Git にコミットしないこと」と警告を出力。
- 環境変数読み込み時に OS 環境変数を保護する仕組みを導入（.env.local でも OS 環境変数を上書きしない）。

Notes / Known limitations
- research.factor_research はファイル末尾で未完の実装が見られる（calc_momentum の途中実装など）。将来的に DuckDB の SQL クエリ実装を追加予定。
- 一部のプラットフォーム（psutil の一部定数や CPU affinity）では機能が制限される場合がある（権限や OS に依存）。その場合は警告を出して処理を継続する設計。
- position_sizing の価格欠損（0.0）の場合、現状は単純にスキップするためエクスポージャー推定が過少になる可能性がある（TODO コメントあり）。

Acknowledgements
- 本 CHANGELOG は提供されたコードベースの構造とコメントからの推測に基づいて作成しています。実際のコミット履歴やより細かな変更点は、バージョン管理履歴に基づいて追記してください。