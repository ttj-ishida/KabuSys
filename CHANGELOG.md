CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。
リリース日はコードベースから推測した日付を付与しています。

Unreleased
----------

- 開発中の変更やマイナー修正をここに記載します。

[0.1.0] - 2026-04-18
--------------------

Added
- 基本バージョン 0.1.0 を追加（パッケージ識別子: kabusys, __version__ = 0.1.0）。
- 環境/設定管理
  - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
  - 高度な .env パーサを実装: export 形式のサポート、シングル/ダブルクォート対応、バックスラッシュエスケープ、インラインコメント処理を考慮。
  - Settings クラスで環境変数をプロパティとして提供（J-Quants/Kabu API/DB/監視設定等）。値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。
  - config_setup CLI（対話型ウィザード）を追加し、.env の初期作成・更新を支援。シークレット項目のマスク表示、選択肢・デフォルト値、確認後の保存機能を備える。
  - validate_config CLI を追加し、起動前に必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML が利用可能な場合）などを検証。--strict モードで警告を FAIL 扱いにできる。
- 実行/監視起動スクリプト
  - run_execution: ExecutionEngine 起動用スクリプトを追加。KABUSYS_ENV に応じて paper_trading 用 DB を分離し、BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、デーモンスレッドでのセッション実行、停止フラグ（data/stop_requested.flag）・PID ファイル管理を実装。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は本番 sqlite_path を使用する設計。
- 監視・データベース初期化
  - init_monitoring_db 呼び出しにより監視テーブルが存在することを保証（冪等）。
  - duckdb と sqlite の両方を利用する設計（duckdb は分析/集計、sqlite は監視/トレードログ等）。
- ロギング・プロセス制御ユーティリティ
  - setup_logging: ルートロガーに stdout 出力の StreamHandler と日次ローテート（TimedRotatingFileHandler、30 日保持）を追加。LOG_DIR/LOG_LEVEL の優先解決、ログディレクトリ作成失敗時のフォールバックを実装。
  - process_priority: Windows / POSIX（Linux/Mac/FreeBSD）に対応したプロセス優先度設定（high/normal/low）と CPU affinity 設定関数を実装。権限不足や未対応環境では安全にスキップする挙動。
- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio.portfolio_builder: 候補選定（スコア降順・タイブレーク）、等金額配分、スコア加重配分（全スコア 0 の場合は等配分へフォールバック）を実装。
  - portfolio.risk_adjustment: セクター集中上限の適用（既存保有を考慮して新規候補を除外）、市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームはログ警告と 1.0 フォールバック。
  - portfolio.position_sizing: allocation_method（risk_based / equal / score）に基づく発注株数計算、単元株（lot_size）丸め、per-stock / aggregate 上限、コストバッファ考慮、available_cash に応じたスケーリングと残余配分ロジックを実装。
- Paper Trading 検証ツール
  - tools.paper_verification_report: paper_trading SQLite DB からシステム稼働率、注文成功率/送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計してレポート出力。閾値判定（稼働率>=99%、注文成功率>=90% 等）に基づく PASS/FAIL 判定を提供。日付フィルタと --db オプションをサポート。
- リサーチ（ファクター計算）基盤
  - research.factor_research: Momentum/Value/Volatility/Liquidity 等のファクター計算を行う設計。DuckDB 接続を受け prices_daily / raw_financials を参照して計算し、(date, code) キーの辞書リストを返す方針を採用。モメンタム計算関数（calc_momentum）の骨子を実装（ファイルの末尾は実装途中の断片あり）。

Changed
- なし（初期リリース相当の追加が主体）。

Fixed
- .env の読み込みとプロパティ取得における堅牢性向上:
  - .env の読み込みに失敗した場合に警告を出すが処理を継続する挙動。
  - Settings の各プロパティで未設定時に明確な例外を投げる（必須項目の検出を容易に）。

Security
- config_setup で生成される .env に関する注意を README 相当のヘッダに記載（.env を Git にコミットしないことを推奨）。

Notes / Migration
- KABUSYS_ENV による動作分岐:
  - paper_trading: ExecutionEngine は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番 SQLite DB とは分離。
  - live: 本番モードでは設定の慎重な確認を推奨（validate_config での追加チェックが有効）。
- ログの保存先やログレベルは環境変数（LOG_DIR / LOG_LEVEL）または各起動スクリプトから渡す引数で制御可能。
- プロセス優先度/CPU affinity の設定は権限に依存するため、権限不足時は警告を出してスキップします。

Acknowledgements / TODO
- research.factor_research の一部実装が途中（ファイル末尾が未完）。さらなるファクター計算や正規化ユーティリティ（data.stats 統合）などが予定される。
- position_sizing の lot_size は現状グローバル共通。将来的には銘柄別単元サイズをサポートする計画あり（コメント記載）。
- monitoring / execution の更なるエラーハンドリングやユニットテスト整備が推奨されます。

References
- 主要 CLI:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]