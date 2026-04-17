CHANGELOG
=========

このファイルは Keep a Changelog のスタイルに準拠しています。  
コードベースの差分はソースから推測して記載しています（実装ファイル名を参照）。

フォーマット:
- Unreleased: 今後の変更（空の場合は削除）
- 各リリース: リリース日と変更点（Added / Changed / Fixed / Removed / Security）

Unreleased
----------
- なし（現時点では直近リリース 0.1.0 の内容を記載しています）

0.1.0 - 2026-04-17
------------------

Added
- 基本機能と CLI を追加
  - 実行エントリ:
    - run_execution.py: ExecutionEngine を起動するスクリプトを追加。スレッドで実行を回し、data/execution.pid を用いる。停止は data/stop_requested.flag によって行う。（ファイル: src/kabusys/run_execution.py）
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検知で安全に終了する。（ファイル: src/kabusys/run_monitoring.py）
  - 設定関連 CLI:
    - config_setup.py: 対話式ウィザードで .env を生成・更新するツールを追加。デフォルト値やシークレット入力、保存確認を実装。（ファイル: src/kabusys/config_setup.py）
    - validate_config.py: .env と config/*.yaml の事前検証ツールを追加。必須環境変数チェック、ログレベル、DB パス、YAML パース、KABUSYS_ENV=live 時の追加ガードなどを実行。--strict オプションあり。（ファイル: src/kabusys/validate_config.py）
  - レポート・ツール:
    - tools/paper_verification_report.py: ペーパートレード用 SQLite DB を解析して稼働率・注文成功率・送信率・API レイテンシ等を集計・評価するレポートを追加。閾値による PASS/FAIL 判定を行う。（ファイル: src/kabusys/tools/paper_verification_report.py）
  - ポートフォリオ構築ライブラリ:
    - portfolio_builder.py: シグナル選定(select_candidates)、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights) を追加。（ファイル: src/kabusys/portfolio/portfolio_builder.py）
    - risk_adjustment.py: セクター集中制限 apply_sector_cap と市場レジームに基づく資金乗数 calc_regime_multiplier を追加。（ファイル: src/kabusys/portfolio/risk_adjustment.py）
    - position_sizing.py: 発注株数計算（risk_based / equal / score）、単元株丸め、aggregate cap によるスケールダウンロジックを実装。（ファイル: src/kabusys/portfolio/position_sizing.py）
    - portfolio パッケージによる公開エントリポイントを追加。（ファイル: src/kabusys/portfolio/__init__.py）
  - 設定読み込み・管理:
    - config.py: .env の自動読み込み（プロジェクトルート検出機構 .git / pyproject.toml 基準）を実装。OS 環境変数を保護する override/protected 機構、値検証付き Settings クラスを提供（env, is_live/is_paper 等）。自動ロード無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1。（ファイル: src/kabusys/config.py）
  - プロセス制御ユーティリティ:
    - utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度設定 set_process_priority と CPU affinity 設定 set_cpu_affinity を提供。権限不足や未対応 OS を考慮してワーニングでフォールバック。（ファイル: src/kabusys/utils/process_priority.py）
  - リサーチ／ファクター計算:
    - research/factor_research.py: DuckDB を用いたモメンタム・ボラティリティ等のファクター計算モジュールを追加（prices_daily / raw_financials テーブル参照、P95 等の統計処理含む）。（ファイル: src/kabusys/research/factor_research.py）
  - パッケージ初期化:
    - __init__.py にバージョン __version__ = "0.1.0" を追加。（ファイル: src/kabusys/__init__.py）

Changed
- DB 周りの分離と挙動の明確化
  - run_execution: KABUSYS_ENV=paper_trading の場合は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 SQLite DB と完全に分離。（ファイル: src/kabusys/run_execution.py）
  - run_monitoring: 監視（Monitoring）は環境にかかわらず production の sqlite_path（settings.sqlite_path）を使用する設計で明記。（ファイル: src/kabusys/run_monitoring.py）
- process priority を起動直後に設定するよう変更（run_execution / run_monitoring）。権限不足時は警告でスキップ。（ファイル: src/kabusys/run_execution.py, src/kabusys/run_monitoring.py）
- .env 読み込みの優先順位を明記:
  - 優先度: OS 環境 > .env.local > .env
  - OS 環境の既存キーは保護され、.env.local は上書き可能（ただし protected のキーは除く）。（ファイル: src/kabusys/config.py）

Fixed
- 環境変数パースの堅牢化
  - _parse_env_line においてシングル/ダブルクォート内のバックスラッシュエスケープとコメント処理を正しくハンドルするロジックを実装。export KEY=val 形式やインラインコメントの扱いを改善。（ファイル: src/kabusys/config.py）
- run_monitoring のポーリング間隔設定で 0 以下の値を誤設定した場合にフォールバックして安全に動作するよう修正（MONITOR_POLL_INTERVAL の検証と警告）。（ファイル: src/kabusys/run_monitoring.py）
- 各種 DB 初期化を冪等に実行するため init_monitoring_db 呼び出しを追加（監視テーブルの存在保証）。（ファイル: src/kabusys/run_monitoring.py, src/kabusys/run_execution.py）

Security
- .env の取り扱いに関する注意喚起を追加（config_setup.py に「.env を絶対に Git にコミットしないこと」を明記）。（ファイル: src/kabusys/config_setup.py）

Documentation / UX
- config_setup.py に対話ガイダンス、現在値/デフォルトの表示、シークレットのマスク表示、保存確認を実装。保存後に validate_config 実行を促すメッセージを追加。（ファイル: src/kabusys/config_setup.py）
- validate_config.py の出力を INFO/WARNING/ERROR に分けて見やすく表示、--strict オプションで警告も失敗扱いにできる仕様を提供。（ファイル: src/kabusys/validate_config.py）
- paper_verification_report での P95 計算、各種フォーマット関数、閾値（稼働率・成功率・送信率・P95 レイテンシ）を実装して明確な Pass/Fail 出力を行えるようにした。（ファイル: src/kabusys/tools/paper_verification_report.py）

Notes / Breaking Changes / 注意事項
- 監視プロセス（run_monitoring）は「環境に関わらず」settings.sqlite_path（本番監視 DB）を使用する設計になっています。開発・検証で監視 DB を分離したい場合は sqlite_path を明示的に変更してください。
- ペーパートレードは run_execution で専用 DB (PAPER_TRADING_SQLITE_PATH / settings.paper_sqlite_path) に記録され、本番データと分離されます。設定忘れによる混同に注意してください。
- .env の自動読み込みはデフォルトで有効です。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PAPER_FILL_MODE の有効値は "instant" | "partial" | "never" | "reject" です。無効値を設定すると ValueError が発生します。（ファイル: src/kabusys/config.py）
- process priority / CPU affinity の設定は OS 権限やプラットフォーム依存です。設定失敗時はワーニングでスキップされます。
- run_execution / run_monitoring は停止制御にプロジェクトルート/data/stop_requested.flag を使用します。運用時の停止フローとファイルパスに注意してください。

開発者向けメモ（推測）
- DuckDB を分析向けに採用しており、prices_daily / raw_financials テーブルを前提としたファクター計算が組み込まれているため、データ投入パイプラインの整備が必要です。（ファイル: src/kabusys/research/factor_research.py）
- position_sizing の lot_size は現状グローバル固定（デフォルト 100）。将来的に銘柄別単元対応が想定される（TODO コメントあり）。（ファイル: src/kabusys/portfolio/position_sizing.py）

今後の提案（参考）
- テスト用の SQLite / DuckDB サンプルデータとユニットテストを追加して、ファクター計算・ポジション算出・シミュレーションの再現性を担保する。
- run_monitoring/run_execution のログレベル・出力先設定を Settings.log_level を使って制御する（現在は basicConfig(level=INFO) 固定）。
- position_sizing の銘柄別 lot_size 対応、price フォールバック（前日終値や取得原価）を実装し、エッジケースの堅牢性を向上する。

---  
（以上）