Keep a Changelog
=================

すべての変更はセマンティックバージョニングに従います。  
このファイルはコードベースから推測して作成した変更履歴です（実際のコミット履歴ではなく実装内容に基づく推測記述）。

Unreleased
----------

- 進行中 / 要対応
  - research/factor_research.py の実装途中（calc_momentum の実装が途中で終わっている箇所あり）。ファクター計算モジュールの追加・完成が必要。
  - テスト、ベンチマーク、ドキュメント（特に PortfolioConstruction.md / StrategyModel.md 参照箇所）の追加検討。
  - 将来的な拡張案（銘柄ごとの lot_size 管理、価格フォールバックロジックなど）がソース中に TODO として記載されているため対応予定。

[0.1.0] - 2026-04-18
--------------------

Added
- 基本アプリケーション情報
  - パッケージメタ情報を追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。
- 設定・起動関連
  - 環境変数・設定管理モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルート自動検出（.git / pyproject.toml）による .env 自動読み込みを実装。
    - .env ファイルの行パースを強化（export プレフィックス対応、クォート文字列のエスケープ処理、インラインコメント処理）。
    - 設定値取得のための Settings クラスを提供（DB パス、ログレベル、環境種別、Paper Trading 用設定など）。
  - 環境設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話式に .env を生成・更新するウィザード。既存値の読み込み・シークレットマスク表示・保存機能あり。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスと config/*.yaml の存在・パースチェック、ライブ環境向けガードなど。
    - --strict オプションで警告も失敗扱いにできる。
- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - プロセス優先度を高優先で設定、KABUSYS_ENV に応じて paper_trading 用 DB を分離（data/paper_trading.db デフォルト）。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組立てとデーモンスレッド実行。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理（data/execution.pid）。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor によるポーリングループ。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能（デフォルト 60 秒）。
    - 監視は常に（環境にかかわらず）本番 sqlite_path を使用する設計。
- データベース / モニタリング
  - 監視用 DB 初期化呼び出し（init_monitoring_db を起動スクリプトから実行）を組み込み、監視テーブルの存在を保証（冪等）。
  - duckdb を分析用に併用（duckdb.Path を設定から取得して接続）。
- ログ・プロセスユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。
    - 既存ハンドラのクリア処理、LOG_LEVEL / LOG_DIR の解決順を明記。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux/Mac/FreeBSD）差異を吸収して set_process_priority/set_cpu_affinity を提供。
    - psutil の権限エラー等をハンドリングしてフォールバックする実装。
- ポートフォリオ構築（純関数群）
  - ポートフォリオ候補選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、signal_rank によるタイブレーク）
    - calc_equal_weights（等分配）
    - calc_score_weights（スコア正規化、全スコア 0 の場合は等分配へフォールバック）
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有を考慮したセクター集中上限チェック、"unknown" セクターは除外対象外）
    - calc_regime_multiplier（bull/neutral/bear に応じた乗数、未知レジームは警告の上 1.0 フォールバック）
  - 株数決定（src/kabusys/portfolio/position_sizing.py）
    - allocation_method による株数計算（risk_based / equal / score）
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）に基づくスケールダウン（端数の再配分ロジック含む）
    - cost_buffer（手数料・スリッページ見積り）を考慮した保守的見積り
  - これらをまとめて公開（src/kabusys/portfolio/__init__.py）。
- ツール
  - Paper Trading の検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）などを集計してレポート出力。
    - パス/閾値判定による PASS/FAIL 表示。期間指定（--from / --to）と DB パス（--db / 環境変数）対応。
- 研究（Research）
  - factor_research.py の骨格を追加（ファクター計算の定義、定数群、calc_momentum の開始実装）。
    - Momentum / Value / Volatility / Liquidity 等の計算方針をドキュメント化。

Changed
- 既存挙動の安全化（新規開発に伴う改善）
  - .env 読み込みの既定挙動: OS 環境変数が優先され、.env.local は .env を上書き可能にした（ただし OS 環境変数は保護）。
  - run_monitoring/run_execution 起動時にプロセス優先度を最初に設定するよう変更（パフォーマンス優先の初期化順序）。
  - run_execution は paper_trading モード時に専用 SQLite を使用することで本番 DB と分離。

Fixed
- 環境変数パースや運用上の堅牢化
  - MONITOR_POLL_INTERVAL の不正値（非数値や 0 以下）を検出してデフォルトにフォールバックし、警告を出力する処理を実装（run_monitoring.py）。
  - .env のパースロジック強化により、クォート内のエスケープやインラインコメント処理に正しく対応（config.py）。
  - ログハンドラの二重登録を防止するため、setup_logging で既存ハンドラの flush/close と削除を行うようにした。
  - プロセス優先度／CPU affinity 設定で権限不足や未対応 OS の場合に警告を出して安全にスキップするようにした（utils/process_priority.py）。
  - DB 初期化（init_monitoring_db）呼び出しを起動スクリプトで行い、監視テーブルがない場合でも起動が続行できる冪等性を確保。

Security
- 特にセキュリティ脆弱性の修正は含まれないが、以下の安全ガードを導入：
  - validate_config による本番（live）環境向けチェックを追加（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性などを警告）。

Deprecated
- なし

Removed
- なし

Notes / 運用上の注意
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全分離され、デフォルトで data/paper_trading.db を使用します。運用時に環境変数 PAPER_TRADING_SQLITE_PATH でパスを明示してください。
- 本番運用では KILL_FLAG_CLEAR_ON_START は "0"（自動クリアしない）を推奨します。validate_config が警告を出します。
- ログディレクトリ作成に失敗した場合はファイル出力が無効化され、コンソール出力のみとなります。監視下での運用時はログディレクトリの書き込み権限を確認してください。
- research/factor_research.py は現状一部実装が途中のため、ファクター計算・DuckDB クエリ部分は完成させる必要があります。

Authors
-------
- （この CHANGELOG はコードベースの解析から生成されています。実際の著者・コミット情報はリポジトリの履歴を参照してください。）