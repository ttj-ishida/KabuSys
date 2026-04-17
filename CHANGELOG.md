CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
言語: 日本語

フォーマット:
- Unreleased: 現在進行中の変更（まだリリースされていないもの）
- 変更履歴はセマンティックバージョニングに従います。

Unreleased
----------

- ドキュメント／小さな改善やバグ修正をここに記載します（現時点ではなし）。

0.1.0 - 2026-04-17
-----------------

Added
- 初回リリース: KabuSys 基本コンポーネント群を実装。
  - パッケージメタ情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。
- 環境設定・読み込み:
  - .env 自動読み込み機能を実装（プロジェクトルートの .env/.env.local を読み込む。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - 複雑な .env パースを実装（export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの取扱い等に対応）。
  - Settings クラスを実装してアプリケーション設定を提供（J-Quants、kabuAPI、LINE、DB パス、監視閾値、環境判定等）。
  - .env 作成支援の対話式ウィザードを実装（src/kabusys/config_setup.py）。既存値の読み込み、秘密値のマスク表示、ファイル出力機能あり。
  - 設定検証 CLI を実装（src/kabusys/validate_config.py）。必須環境変数・パス・YAML 構成ファイルの存在・本番時ガード等を検証。--strict オプションで警告を失敗扱いにできる。
- 実行管理スクリプト:
  - 実行エンジン起動スクリプトを実装（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は専用の paper DB を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカクライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動・停止処理を提供。
    - 停止フラグファイル (data/stop_requested.flag) による安全停止、実行 PID ファイルの指定。
  - 監視（モニタリング）ループ起動スクリプトを実装（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒、0 以下はデフォルトにフォールバック）。
    - 監視は環境に関係なく本番 sqlite_path を使う設計（監視 DB の一貫性維持）。
    - SystemMonitor の単回チェック check_once() をループで実行し、例外時はログに例外を出して次回ポーリングへ継続。
- モニタリング DB 初期化:
  - init_monitoring_db 関数経由で監視用テーブルの冪等な初期化を行う（run_execution/run_monitoring から呼び出し）。
- プロセス優先度 / CPU affinity:
  - psutil をラップしたユーティリティを実装（src/kabusys/utils/process_priority.py）。
    - クロスプラットフォーム対応（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
    - set_process_priority(level)、set_cpu_affinity(cpu_count) を提供。権限不足や未対応環境では警告を出してスキップ。
- ポートフォリオ構築モジュール:
  - 銘柄選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順 + タイブレークで上位 N を選択。
    - calc_equal_weights / calc_score_weights を提供。スコア合計が 0 の場合は等金額配分にフォールバック（警告ログ）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 同一セクターの既存保有比率が上限を超える場合、新規候補から除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market レジームに基づく乗数（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは 1.0 にフォールバック（警告）。
  - 株数算出・リスク制約・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に対応。リスク許容率、損切り率、単元（lot_size）考慮、単銘柄上限・総投下上限、cost_buffer（スリッページ/手数料見積もり）を考慮したスケーリングロジックを実装。残差配分ロジックにより lot 単位で追加配分を行う。
- リサーチ / ファクター計算:
  - DuckDB を用いたファクター計算モジュール（src/kabusys/research/factor_research.py）。
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20 等）、流動性指標等を計算する設計（prices_daily / raw_financials テーブルを前提）。
    - DuckDB SQL を用いてウィンドウ関数で効率的に計算。
- ツール:
  - Paper Trading 検証レポート生成スクリプトを実装（src/kabusys/tools/paper_verification_report.py）。
    - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）を算出して PASS/FAIL 判定を行う。閾値はソース中に定義（稼働率99%、成立率90%、送信率95%、P95レイテンシ200ms）。
- その他ユーティリティ:
  - path / ファイル存在チェック、フォールバック動作、詳細なログ出力を各所に実装。
  - CLI から実行しやすいエントリポイントを多数提供（config_setup, validate_config, tools.paper_verification_report 等）。

Changed
- （初回リリースのため特になし）

Fixed
- （初回リリースのため特になし）

Removed
- （初回リリースのため特になし）

注意事項 / マイグレーションガイド
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。未設定時に Settings 呼び出しで ValueError が発生します。
- 環境変数のデフォルト:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PID ファイルやフラグファイルは data/ 以下に配置される想定（プロジェクトルート検出ロジックに依存）。
- Paper Trading:
  - KABUSYS_ENV=paper_trading のとき、run_execution は paper_trading 専用 SQLite を使い、本番 DB と完全に分離されます。
- 監視:
  - run_monitoring は環境にかかわらず sqlite_path（本番監視 DB）を使用するよう設計されています。監視対象 DB を運用環境に応じて変更する場合はコードの挙動を確認してください。
- 外部依存:
  - psutil（プロセス優先度／CPU affinity）、duckdb、sqlite3、(オプションで) PyYAML が利用されます。validate_config は PyYAML がない場合 YAML 内容検証をスキップして警告を出します。
- 権限やプラットフォーム:
  - プロセス優先度／CPU affinity の設定は権限不足や未対応プラットフォームで失敗する可能性があり、その場合は警告が出て処理を継続します。

今後の予定（例）
- 詳細なユニットテストの追加（.env パーサ、position sizing／scaling ロジック、factor 計算の境界ケース等）。
- ポートフォリオ構築のさらなる拡張（銘柄別 lot_size, 手数料モデルの詳細化）。
- モニタリング・アラート（LINE 通知等）の実装強化。
- 実行エンジンのライフサイクル管理とより堅牢な再試行/フェイルオーバー機構。

お問い合わせ・貢献
- 質問や不具合報告、パッチの提案はリポジトリの issue / pull request をご利用ください。