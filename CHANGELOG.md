CHANGELOG
=========

すべての注目すべき変更を記録します。これは Keep a Changelog の形式に準拠しています。

フォーマット方針:
- 重大な機能追加や仕様は「Added」
- 既存仕様の明確化や動作変更は「Changed」
- バグ修正や堅牢性向上は「Fixed」

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ初期リリース。
- 実行系 / 監視系エントリポイント
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV による paper_trading モードのサポート（MockBrokerClient を使用し、data/paper_trading.db に記録して本番 DB と分離）。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を呼び出し）。
    - 停止フラグ (data/stop_requested.flag) および実行 PID ファイル (data/execution.pid) の取り扱い。
    - RiskManager, OrderManager, Reconciler, ExecutionEngine の組み立て・実行ループを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する仕様。
    - 停止フラグの検知でループ終了、例外発生時にはログ出力して次回ポーリングへ継続。
- 設定管理・支援ツール
  - config.py: 環境変数/.env の自動読み込みと Settings クラスを提供。
    - プロジェクトルート自動検出（.git または pyproject.toml 基準）。
    - .env/.env.local のロード順序と OS 環境変数の保護機能を実装。
    - 各種設定プロパティ（DB パス、KABUSYS_ENV、PAPER_FILL_MODE 等）を提供し、妥当性チェックを行う。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。
    - 項目定義に基づく入力プロンプト、既存 .env の読み込み、.env ファイル書き出しをサポート。
  - validate_config.py: 起動前検証 CLI を追加。
    - 必須/オプション環境変数・ログレベル・DB パス・config/*.yaml の存在と簡易パース検証を実施。
    - --strict オプションで警告を FAIL 扱いにできる。
- 環境変数パーサ
  - .env ファイルのパース実装を追加（export プレフィックス、シングル/ダブルクォート、エスケープ、コメントの扱いに対応）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均 / 最大 / P95）を集計・判定。
    - 判定基準（閾値）をソースコード中で定義（稼働率 99%、成立率 90% 等）。
    - --from / --to / --db オプションをサポート。
- ポートフォリオ構築ライブラリ
  - portfolio.portfolio_builder: シグナル候補の選定(select_candidates)、等配分/スコア重み算出(calc_equal_weights, calc_score_weights)を追加。
  - portfolio.position_sizing: position size（発注株数）計算ロジックを追加。
    - allocation_method による分岐（risk_based, equal, score）。
    - lot_size（単元）丸め、max_position_pct、max_utilization、cost_buffer による aggregate キャップ処理。
    - 利用可能現金に対するスケーリングと残差のロット単位での再配分ロジックを実装。
  - portfolio.risk_adjustment: セクター集中上限の適用(apply_sector_cap) とマーケットレジームに応じた投下資金乗数(calc_regime_multiplier)を追加。
    - unknown セクターの扱い、セクター上限超過判定、ブロック除外ロジックを実装。
    - レジーム乗数は bull/neutral/bear に対するデフォルトを提供（未知はフォールバック）。
- 研究系
  - research.factor_research: DuckDB を用いたファクター計算モジュール（モメンタム、ボラティリティ等）の骨組みを追加。
    - calc_momentum、calc_volatility 等の実装（prices_daily テーブル参照）。P95 等の閾値・ウィンドウ定義を含む。
- ユーティリティ
  - utils/process_priority.py: プラットフォーム非依存のプロセス優先度・CPU affinity 設定ユーティリティを追加（Windows/Linux/macOS を考慮）。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。
    - psutil の権限エラーを安全に扱うログ出力を実装。
- パッケージ情報
  - __init__.py によるバージョン定義 (__version__ = "0.1.0") と公開 API 列挙。

### Changed
- （初期リリースのため大きな互換性変更はなし）ただし設計上の注意点・振る舞いを明記:
  - 監視（monitoring）は環境変数 KABUSYS_ENV にかかわらず本番用 sqlite_path を参照する（監視データは本番 DB を基本とする）。
  - .env の自動ロードはデフォルトで有効。自動ロードを無効にする環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - PAPER_FILL_MODE は有効値を限定（instant / partial / never / reject）し、不正値は ValueError を送出する。
  - config_setup にて .env は Git にコミットしないよう注記。

### Fixed
- 各種入力/外部依存の堅牢性向上:
  - .env 読み込みでファイルオープン失敗時に警告を出して継続するようにした（テスト環境での動作性向上）。
  - process_priority、CPU affinity の設定失敗時は例外を投げず警告にとどめる（権限不足や未サポート OS 対応）。
  - run_monitoring の MONITOR_POLL_INTERVAL の不正値（0 や非整数）を警告ログによりデフォルトにフォールバックするようにした。
  - run_execution/run_monitoring で各 DB 接続 (sqlite3/duckdb) を finally ブロックで確実にクローズする実装。

### Notes
- config/*.yaml の完全なパース検証は PyYAML インストール有無に依存（インストールされていない場合は YAML 検証をスキップして警告を出す）。
- 一部のモジュール（研究モジュールや ExecutionEngine 周り）は外部コンポーネント（BrokerClient 等）との連携前提であり、実行環境の設定（.env や DB）を整備する必要があります。
- 今後のリリースで以下を予定:
  - strategy / execution のより詳細なテストカバレッジ追加
  - stocks マスタに基づく個別 lot_size 対応
  - Monitoring / Reconciler の詳細ログ・メトリクス強化

以上。