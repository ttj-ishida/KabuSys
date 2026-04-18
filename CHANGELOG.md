CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに従って記載しています。
セマンティックバージョニングを採用しています。

Unreleased
----------

- なし（初期リリース）

[0.1.0] - 2026-04-18
--------------------

Added
- プロジェクト初回リリース。
- 実行用エントリスクリプトを追加:
  - run_execution.py — ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は専用の paper_db（data/paper_trading.db）を使用する分離ロジックを実装。BrokerClientFactory を通じたブローカー抽象化、OrderRepository/OrderManager/RiskManager/Reconciler を組み合わせてエンジンを起動し、停止フラグ（data/stop_requested.flag）で安全に停止できる。
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。モニタリング DB は環境に依らず本番 sqlite_path を使用する設計。
- 設定管理モジュール:
  - config.py — .env 自動読み込み機能（.env → .env.local の順、OS 環境変数を保護）を実装。複雑な .env 行のパース（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント）に対応。Settings クラスで各種設定をプロパティとして提供（DB パス、Paper Trading の挙動、監視閾値など）。
  - config_setup.py — 対話式ウィザードで .env を生成/更新する CLI を実装（シークレット項目はマスク表示）。
  - validate_config.py — 起動前設定検証 CLI を実装。必須環境変数や config/*.yaml の存在・パース検証、KABUSYS_ENV の安全ガード等をチェック。--strict オプションで警告を失敗として扱う。
- ロギング・プロセスユーティリティ:
  - utils/logging_setup.py — stdout 出力の StreamHandler と 日次ローテーション（TimedRotatingFileHandler）を組み合わせた統一的ログ設定を実装。ログディレクトリ自動作成、環境変数 LOG_LEVEL / LOG_DIR の尊重、ファイルハンドラ作成失敗時のフォールバック処理を実装。
  - utils/process_priority.py — Windows/Linux/macOS を吸収するプロセス優先度設定と CPU affinity 設定を実装。psutil の例外・権限不足を安全に扱う。
- ポートフォリオ構築関連（純関数群）:
  - portfolio/portfolio_builder.py — 候補選定（スコア降順、タイブレーク）、等金額・スコア加重の重み計算を実装。スコア合計が 0 の場合は等金額にフォールバック。
  - portfolio/risk_adjustment.py — セクター集中制限（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を実装。unknown セクター扱い、レジーム未定義時のフォールバックを明示。
  - portfolio/position_sizing.py — risk_based / equal / score の割当方法をサポートする株数計算ロジックを実装。単元株（lot_size）丸め、1銘柄上限・集計上限（available_cash）でのスケーリング処理、cost_buffer を考慮した保守的見積り、端数の分配アルゴリズムを実装。
- 研究・解析:
  - research/factor_research.py — モメンタムや移動平均乖離率、ATR、流動性などのファクター計算モジュールを追加（DuckDB 経由で prices_daily / raw_financials を参照する設計）。モジュールは設計方針と定数を含めて作成済み（モメンタム計算の実装途中）。
- ツール:
  - tools/paper_verification_report.py — Paper Trading 用検証レポート生成スクリプトを実装。system_status / trade_logs / risk_logs を参照して稼働率・注文成功率・送信率・レイテンシ（平均、最大、P95）を算出し、閾値（稼働率 99% 等）に基づく PASS/FAIL 判定を表示。--from/--to/--db オプションをサポート。
- パッケージメタ:
  - __init__.py にバージョン定義 __version__ = "0.1.0" を追加。

Changed
- ログ出力はデフォルトで stdout を使用するように設計（cron 等からのリダイレクトを想定）。
- run_monitoring と run_execution は起動時にプロセス優先度を "high" に設定する処理を追加。

Fixed
- .env の複雑な記法（クォート付・エスケープ・export プレフィックス・インラインコメント）に対するパーサを改善し、誤った読み込みやコメントの誤解釈を低減。
- run_monitoring の MONITOR_POLL_INTERVAL に 0 以下や不正文字列が設定された場合にデフォルトにフォールバックし、警告ログを出すように変更（time.sleep に渡す不正値を回避）。

Security
- 機密情報（トークンやパスワード）を .env に保存するワークフローを明示し、config_setup の出力で .env を誤って Git にコミットしないよう注記。

Known issues / Notes
- research/factor_research.py の実装は途中（ファイル末尾が未完）であり、モメンタム計算の SQL/実行ロジックが完全ではありません。今後のリリースで完成予定。
- position_sizing の価格欠損時の挙動について TODO コメントあり（フォールバック価格の導入検討）。
- process_priority や cpu_affinity の設定は権限不足（非 root / 管理者）やプラットフォーム差分で失敗する場合があり、その場合は警告を出してスキップする設計。
- validate_config は PyYAML 未インストール時に YAML 検証をスキップするため、環境によっては config/*.yaml の内容チェックが省略されます。

Notes for operators
- 起動前に python -m kabusys.config_setup で .env を作成し、python -m kabusys.validate_config で検証してください。
- Paper Trading は本番 DB と完全分離されています。KABUSYS_ENV=paper_trading を指定すると paper_sqlite_path（既定 data/paper_trading.db）を使用します。
- 停止はプロジェクトルート/data/stop_requested.flag にファイルを作成することで行います（run_execution/run_monitoring がチェックして安全に停止します）。

Acknowledgements
- 初期設計はモジュール分割と純関数化（ポートフォリオ計算部）を重視しており、テスト可能性・運用性を意識した構成になっています。今後のリリースで research モジュールの完成、CI/テスト、ドキュメントの拡充を予定しています。