CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。

フォーマットは "Keep a Changelog" に準拠しています。

リリース日付はコードベースから推測して設定しています。実際のリリース日が異なる場合は適宜修正してください。

[Unreleased]
------------

- 次回リリースに向けたメモ
  - research/factor_research.py の実装継続（モメンタム等のファクター計算が途中）
  - 単元株サイズの銘柄別対応（lot_map）や価格フォールバックの実装検討
  - その他テスト・ドキュメント整備

[0.1.0] - 2026-04-19
-------------------

Added
- パッケージの初期リリースを追加（__version__ = "0.1.0"）。
- 実行用スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイント。  
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（data/paper_trading.db など）を使用し、Mock ブローカーを利用して本番 DB と完全分離する。  
    - プロセス優先度を起動時に "high" に設定し、停止フラグ（data/stop_requested.flag）を監視して安全に停止する。
- 監視用スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。  
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。  
    - Monitoring は環境にかかわらず本番 sqlite_path を使用するよう設計。
- 環境設定関連ユーティリティ
  - config.py: .env 自動読み込み、環境変数のパース・検証、Settings クラス（各種設定プロパティ）を追加。  
    - .env の自動ロードはプロジェクトルート（.git or pyproject.toml）を基準に行う。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。  
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH、各種閾値などのプロパティを提供。
  - config_setup.py: 対話式ウィザードで .env を生成/更新する CLI を追加。必須/任意項目のプロンプト、既存 .env の読み込み、マスク表示などを実装。
  - validate_config.py: 起動前に .env や config/*.yaml を検証する CLI を追加。--strict モードで警告を FAIL 扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 共通ロギング設定ユーティリティを追加。  
    - コンソール（stdout）と TimedRotatingFileHandler（日次、30 日保持）をルートロガーに設定。LOG_DIR/LOG_LEVEL による上書き対応。既存ハンドラ再構成で二重設定を防止。
  - utils/process_priority.py: プロセス優先度と CPU affinity のユーティリティを追加。  
    - Windows / POSIX の差を吸収して set_process_priority(level) / set_cpu_affinity() を提供。アクセス権限不足時は警告でスキップ。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）および配分重み（calc_equal_weights, calc_score_weights）を実装。
  - portfolio/risk_adjustment.py: セクター集中上限の適用（apply_sector_cap）、市場レジームに応じた資金乗数（calc_regime_multiplier）を実装。レジームが未知の場合はフォールバックと警告出力。
  - portfolio/position_sizing.py: 銘柄ごとの発注株数計算を実装（allocation_method: "risk_based" / "equal" / "score"）。  
    - aggregate cap のスケールダウン処理、単元株（lot_size）丸め、手数料・スリッページ見積り用 cost_buffer を考慮。
    - 設定可能なリスク係数、stop_loss_pct、max_position_pct、max_utilization 等を受け取る。
  - portfolio/__init__.py で上記 API を公開。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード DB（PAPER_TRADING_SQLITE_PATH）から検証レポートを生成する CLI を追加。  
    - 指標: システム稼働率、注文成功率（fill rate）、送信率（send rate）、レイテンシ（avg/max/P95）などを集計。  
    - デフォルトの合格基準を導入（例: 稼働率 >= 99.0%、Fill >= 90%、Send >= 95%、P95 レイテンシ <= 200 ms）。
- research/factor_research.py（ファクター計算基盤）
  - DuckDB 接続を受けてファクター（Momentum, Value, Volatility, Liquidity）を計算する設計を追加。モメンタム計算（calc_momentum）の実装開始（途中まで）。

Changed
- なし（初期リリースのため新規追加中心）。

Fixed
- なし（初期リリース）。

Deprecated
- なし。

Removed
- なし。

Security
- なし。

Notes / Known issues / TODO
- research/factor_research.py は未完（ファイル末尾が途中で切れている/実装継続が必要）。ファクター計算の全面リリース前に追加実装およびテストが必要。
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）ある場合、エクスポージャーが過少見積りとなる可能性がある。コメントでフォールバック価格（前日終値や取得原価）の導入を検討する旨を記載。
- portfolio/position_sizing:
  - 将来的な拡張として各銘柄ごとの lot_size（lot_map）対応を予定（現在は全銘柄共通 lot_size）。コメントに TODO を残している。
- logging_setup:
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続する仕組みを採用（起動環境に依存する挙動）。
- run_monitoring:
  - 監視は環境にかかわらず本番 sqlite_path を使用するため、開発時の DB セパレーションに注意が必要。
- run_execution:
  - 起動前に停止フラグが立っている場合は起動をスキップする安全機構あり。
  - RiskManager の初期化時に broker.get_available_cash() を用いて初期ポートフォリオ値を取得しているため、MockBroker / 本番ブローカー双方の互換性が重要。
- .env パーサ:
  - クォート内のバックスラッシュエスケープやインラインコメントの扱い、export プレフィックスへの対応など、比較的堅牢なパースを実装しているが、特殊ケースは追加テスト推奨。

開発者向けメモ
- コマンドライン例:
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - 実行エンジン起動: python -m kabusys.run_execution
  - 監視起動: python -m kabusys.run_monitoring
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

以上。必要であれば各項目を英語版やリリースノート向けに整形します。