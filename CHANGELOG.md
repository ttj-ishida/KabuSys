CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠します。
リリースは逆時系列（新しいものが上）で並べています。

0.1.0 — 2026-04-18
-----------------

Added
- 初回公開（バージョン 0.1.0）。
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて本番/ペーパートレードを切り替え。
    - KABUSYS_ENV=paper_trading の場合は専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB との完全分離を実現。
    - ブローカークライアント生成（BrokerClientFactory）および OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行い、エンジンを別スレッドで実行。停止フラグ（data/stop_requested.flag）検知で安全に停止。
    - 実行用 PID ファイル（data/execution.pid）サポート。
- 監視用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視 DB は環境にかかわらず監視用 sqlite_path（デフォルト: data/monitoring.db）を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
- 設定・環境関連
  - config.py
    - Settings クラスを追加し、環境変数からアプリ設定を取得するユーティリティを提供。
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を起点）を実装（._env/.env.local の優先度を考慮）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパース仕様強化（export プレフィックス対応、クォート値でのバックスラッシュエスケープ対応、コメントの取り扱いなど）。
    - 各種デフォルトパスと環境変数・値検証（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL など）を提供。
- 設定操作 CLI
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。シークレット項目はマスク表示。生成される .env のテンプレートと保存機能を提供。
  - validate_config.py
    - .env や config/*.yaml の起動前検証 CLI を追加。必須環境変数チェック、パスの存在確認、YAML パース（PyYAML が存在する場合）や本番環境向けの追加ガードを実行。--strict オプションで警告を失敗扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。stdout（StreamHandler）と日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
    - ログレベル・ログディレクトリは引数、環境変数、デフォルト値の順に解決。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを追加。Windows と POSIX（Linux/Mac など）で差分を吸収し、権限不足等の例外は警告でフォールバック。
- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py
    - position sizing ロジック（risk_based / equal / score）、単元（lot_size）丸め、aggregate cap によるスケールダウン・端数処理を実装。
  - portfolio パッケージの __all__ エクスポートを整備。
- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用の検証レポート生成スクリプトを追加。システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計し PASS/FAIL 判定を出力する。閾値はソース内定数で定義（例: 稼働率 >= 99% など）。
    - コマンドライン引数で期間指定（--from, --to）や DB パス指定（--db）が可能。デフォルト DB は環境変数 PAPER_TRADING_SQLITE_PATH も参照。
- 研究モジュール（factor_research）
  - research/factor_research.py
    - DuckDB を用いたファクター計算（Momentum / Value / Volatility / Liquidity）用の基盤を追加。モメンタム計算等の設計仕様（期間やウィンドウ）を定義。関数インターフェースと定数が含まれる（実装はファイル内で進行中の箇所あり）。
- パッケージ管理
  - kabusys/__init__.py に __version__ = "0.1.0" を追加し、主要サブパッケージを __all__ で公開。

Changed
- なし（初回リリース）。

Fixed
- なし（初回リリース）。
  - ただし各モジュール内で安全なフォールバックや警告出力を多数実装（例: 無効な MONITOR_POLL_INTERVAL に対するデフォルトフォールバック、ログディレクトリ作成失敗時のファイルハンドラスキップ、プロセス優先度設定失敗時の警告処理など）。

Security
- なし（初回リリース）。
  - 注意: 生成される .env ファイルは機密情報を含むため、README 等で .env を Git にコミットしないことを強く推奨。

Notes / 既知事項
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。配布後やルートが検出できない環境では自動ロードをスキップします。
- KABUSYS_ENV の値は "development" / "paper_trading" / "live" に制限されます。不正値は起動時に ValueError を発生させます。
- PAPER_FILL_MODE は "instant" / "partial" / "never" / "reject" のいずれかでなければなりません。
- run_monitoring は監視 DB に対して常に sqlite_path（監視 DB）を使用します（KABUSYS_ENV に依存しない）。
- run_execution はペーパートレード時に paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。
- research/factor_research の一部関数は実装途中のコメント/設計が含まれます。今後のリリースで完成予定です。

Breaking Changes
- なし（初回リリース）。

今後の予定（例）
- factor_research の各ファクター計算の完成とユニットテスト追加。
- ExecutionEngine / SystemMonitor 周りの耐障害性向上とメトリクスの強化。
- 各モジュールの詳細ドキュメント（API docstring 充実、README 追加）。