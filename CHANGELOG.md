KEEP A CHANGELOG
=================

すべての重要な変更点をこのファイルで記録します。  
フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

- なし

[0.1.0] - 2026-04-17
--------------------

Added
- 基本 CLI / ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を用い、本番 DB と分離して data/paper_trading.db を使用する挙動を実装。
  - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
  - 停止連携: プロジェクト直下の data/stop_requested.flag を用いた停止フラグ検知による優雅な終了処理を実装。実行用に data/execution.pid を出力する仕組みをサポート。

- 設定周り
  - config.py: 環境変数・設定管理を実装。プロジェクトルート自動検出 (.git or pyproject.toml) に基づく .env / .env.local の自動読み込み（OS 環境変数を保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加。
  - Settings クラスに各種プロパティを実装（J-Quants / kabu API / LINE / DB パス / 監視しきい値 / 実行環境等）。PAPER_FILL_MODE の検証ロジックを実装（instant/partial/never/reject）。
  - config_setup.py: 対話式ウィザードにより .env を初期作成・更新できる CLI を追加（秘密値マスク／選択肢／デフォルト値の提示、.env 上書き保存機能）。

- 設定検証ツール
  - validate_config.py: .env と config/*.yaml の起動前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、config YAML の存在と PyYAML によるパース検証、KABUSYS_ENV=live 時の追加警告等を行う。--strict による警告の FAIL 扱いをサポート。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio.portfolio_builder: シグナル選定 (select_candidates) と配分（等分配 calc_equal_weights、スコア加重 calc_score_weights）を実装。スコア全ゼロ時のフォールバック挙動を備える。
  - portfolio.risk_adjustment: セクター集中抑制 apply_sector_cap、マーケットレジームに基づく乗数 calc_regime_multiplier を実装（未知レジーム時は警告して 1.0 にフォールバック）。
  - portfolio.position_sizing: position サイズ決定ロジック calc_position_sizes を実装。allocation_method に "risk_based" / "equal" / "score" をサポート、ロット（lot_size）丸め、単銘柄上限・総投下キャップ (max_utilization)・コストバッファを考慮したスケーリング（端数処理と残余配分）を実装。

- 研究用モジュール
  - research.factor_research: DuckDB 接続を受け取り prices_daily / raw_financials を元にモメンタム（1M/3M/6M、MA200乖離）やボラティリティ（ATR20 等）、流動性指標を算出する関数群を追加。SQL / ウィンドウ関数を用いた計算を実装。

- ユーティリティ
  - utils.process_priority: クロスプラットフォームでのプロセス優先度設定および CPU affinity 設定ユーティリティを追加。Windows/Linux/macOS を吸収し、権限不足時や未対応 OS の際は安全にスキップして警告を出す。

- 監視・検証ツール
  - monitoring.monitoring_db の初期化呼び出しをランナーに統合し、監視テーブルの冪等な作成を保証。
  - tools.paper_verification_report.py: ペーパートレード用検証レポート生成ツールを追加。期間指定や DB パス指定 (--db) に対応し、稼働率・注文成功率・送信率・レイテンシ (avg/max/P95)・リスク却下数などを算出して PASS/FAIL を判定する閾値を設定（P95 計算、N/A 表示に対応）。

Changed
- 起動時のプロセス優先度設定を各ランナー（run_execution, run_monitoring）の最初に行うように変更し、負荷の高い処理での優先制御を試みる挙動を一貫化。
- run_execution: paper_trading 環境の DB は paper_sqlite_path を優先するように明確化（本番 DB と完全分離）。
- run_monitoring: MONITOR_POLL_INTERVAL の取得を関数化し、無効値（0 以下や非整数）を検出した場合はログ警告を出して既定値にフォールバックするように変更。
- .env パーサーの堅牢化（config._parse_env_line）
  - export KEY=... 形式のサポート
  - シングル/ダブルクォート内でのバックスラッシュエスケープ処理
  - クォートなし値のインラインコメント取り扱い（直前が空白/タブのみコメントとみなす）
  - 無効行の無害なスキップ
- validate_config: PyYAML 未導入時に YAML 検証をスキップするが警告を出すように変更。config/*.yaml のパースエラーはエラー扱いに。

Fixed
- position_sizing のスケーリングロジックで端数処理の取り扱いを安定化（lot_size 単位の丸めと残余キャッシュを順序付き残差で配分）。
- process_priority でプラットフォーム固有の定数が未定義の場合にもモジュールロードが失敗しないよう getattr によるフォールバックを導入。
- paper_verification_report:
  - P95 計算関数 _p95 を導入して空集合・サンプル数に依存する正しい P95 を算出。
  - 日付フィルタを ISO8601 形式（UTC）で扱い、範囲指定のエッジケースを明確化。

Security
- .env に機密情報が含まれる点に鑑み、config_setup に .env を生成する際の注意書きを追加（.env を絶対に Git にコミットしないことを明示）。

Notes / Other
- パッケージバージョンを __init__.py にて 0.1.0 に設定。
- いくつかの TODO コメントを残し、将来的な拡張点（銘柄別 lot_size 対応、価格フォールバック戦略など）を示唆。

Acknowledgements
- 初期リリース。今後のリリースではテストカバレッジ、ドキュメント、例外処理の強化、より詳細な監視メトリクスの追加を予定しています。