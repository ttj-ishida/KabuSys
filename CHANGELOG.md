CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/

Unreleased
----------

（現時点の作業ツリー — 特に未リリースの変更はありません）

[0.1.0] - 2026-04-19
-------------------

Added
- 初期リリース: KabuSys 自動売買フレームワークの基本機能を追加。
  - ポートフォリオ構築モジュール（kabusys.portfolio）
    - 銘柄選定: select_candidates
    - 重み計算: calc_equal_weights, calc_score_weights
    - ポジションサイズ計算: calc_position_sizes（risk_based / equal / score 対応、lot_size・cost_buffer を考慮）
    - セクター集中制限とレジーム乗数: apply_sector_cap, calc_regime_multiplier
  - 実行系起動スクリプト（run_execution.py）
    - ExecutionEngine の起動フロー、スレッド駆動のセッション実行
    - Paper Trading と本番 DB の分離（KABUSYS_ENV=paper_trading 時は専用 SQLite を使用）
    - BrokerClientFactory を用いたブローカークライアント生成
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立て
    - エンジン停止用の stop フラグ（data/stop_requested.flag）と pid ファイル管理
  - 監視系起動スクリプト（run_monitoring.py）
    - SystemMonitor によるポーリング監視ループ
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）
    - 監視 DB 初期化（monitoring 用テーブルの冪等初期化）
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨の挙動
  - 設定管理（kabusys.config）
    - .env 自動読み込み（プロジェクトルートを特定して .env / .env.local を順にロード）
    - .env パーサの強化（export 形式、シングル／ダブルクォート内のエスケープ、インラインコメント処理）
    - OS 環境変数を保護する protected オプション（override 時の上書き制御）
    - Settings クラスによるプロパティベースの設定取得（デフォルト値、検証ロジックを含む）
  - 設定ウィザード CLI（kabusys.config_setup）
    - 対話式で .env を初期作成・更新するウィザードを提供
    - 秘匿項目のマスク表示、既存 .env の読み込み、保存確認
  - 設定検証 CLI（kabusys.validate_config）
    - .env / config/*.yaml の起動前検証
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスや YAML 構文チェック、live 環境向けガード等
    - --strict オプションで警告を失敗扱いにするモードを提供
  - ログ設定ユーティリティ（kabusys.utils.logging_setup）
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler をルートロガーに設定
    - ログディレクトリの解決と自動作成、失敗時はファイル出力をスキップ
    - ログレベル解決の優先度（引数 > 環境変数 > デフォルト）
  - プロセス優先度 / CPU affinity ユーティリティ（kabusys.utils.process_priority）
    - Windows / POSIX の差分を吸収してプロセス優先度を設定
    - CPU affinity 固定機能（最初の N コアにピン留め）
    - 権限不足や未対応 OS では安全にスキップするフォールバック処理
  - Paper Trading 検証レポート（kabusys.tools.paper_verification_report）
    - ペーパートレード用 SQLite から稼働率、注文成功率、送信率、レイテンシ等の指標を集計してレポートを生成
    - P95 レイテンシ計算、閾値による PASS/FAIL 判定、期間指定オプション（--from / --to / --db）
    - DB が存在しない場合やテーブルがない場合の耐障害性を確保（OperationalError を捕捉）
  - 研究用ファクター計算枠組み（kabusys.research.factor_research）
    - DuckDB を用いた定量ファクター計算（モメンタム / MA / ATR / 出来高等、prices_daily / raw_financials を参照）

Changed
- エントリポイントのログ出力とプロセス初期化順序を整理
  - setup_logging → set_process_priority の実行順で明示的に優先度を上げる処理を追加
- 設定読み込みの動作を安全化
  - プロジェクトルートが特定できない場合は自動ロードをスキップするようにした（配布後の環境での安全性向上）
  - .env の読み込みで OS 環境変数を保護する仕組み（protected set）を導入

Fixed
- .env パーサの堅牢化
  - export KEY=val 形式、クォート内のバックスラッシュエスケープ、インラインコメントの扱いを改善して誤読を防止
- run_monitoring のポーリング間隔取得で、0 以下や不正な値が指定された場合に time.sleep で ValueError になる問題を防止し、デフォルトにフォールバックして警告を出すように修正
- ログディレクトリ作成失敗時にファイルハンドラ作成でクラッシュする問題を回避。ファイル出力が利用できない場合はコンソール出力のみで継続
- process_priority の権限不足や環境差で例外が発生する場合に警告を出して安全にスキップするように修正
- Paper 検証レポートでテーブル未存在やデータ欠損時に例外で停止しないよう sqlite3.OperationalError を捕捉してフォールバックを行うようにした
- calc_score_weights: 全銘柄のスコアが 0.0 の場合に等金額配分へフォールバックし、警告ログを出力するようにした

Security
- .env の取り扱いに関する注意を README / .env ヘッダに記載（.env を絶対に Git にコミットしない旨を明示）

Internal
- コードベースのモジュール分割を整理（portfolio, execution, monitoring, utils, research, tools）
- 多数の関数に docstring と引数・戻り値の説明を追加し、可読性と保守性を向上
- 各所でのデフォルト値と閾値（例: ポーリング間隔 60 秒、ログローテート 30 日、Paper 検証の閾値）を定義して再利用

Notes
- 本リリースは「最小限の動作するプロトタイプ」を目標としており、生データや外部 API との連携部分（ブローカークライアントの具体実装、Strategy のシグナル生成等）は別モジュール／別 PR で追加・改善予定です。
- factor_research モジュールは実装途中（ファイル末尾が切れている／未完の関数が存在）であり、将来のリリースで完成予定です。

Acknowledgements
- このリリースは内部設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）に基づいて実装されています。

[0.1.0]: https://example.com/releases/0.1.0 (初期リリース)