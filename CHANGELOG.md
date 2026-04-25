# Changelog

すべての重要な変更はこのファイルに記録します。書式は「Keep a Changelog」に準拠します。  
リリース日付はコードベースから推測したものを使用しています。

全般的な注意
- この変更履歴は与えられたコードの内容から推測して作成しています。実際のコミット履歴やリリースノートと異なる可能性があります。
- 初期リリース（0.1.0）として主要機能・ユーティリティ・CLI をまとめています。

Unreleased
- （次回リリース向けの変更点をここに追記してください）

[0.1.0] - 2026-04-25
Added
- 基本パッケージ初期実装
  - パッケージ情報を定義（kabusys.__version__ = 0.1.0）。
- 設定管理
  - 環境変数／.env の自動読み込み機能を実装（プロジェクトルート自動検出: .git / pyproject.toml を基準）。
  - .env ファイルのパース機能を実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント対応）。
  - Settings クラスを提供し、各種設定値（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 / 実行環境など）をプロパティとして安全に取得可能に。
  - PAPER_FILL_MODE の妥当性チェックや KABUSYS_ENV / LOG_LEVEL の検証を実装。
- 環境設定ウィザード
  - 対話式 CLI（python -m kabusys.config_setup）を追加。.env の初期作成・更新を支援し、既存値の再利用やシークレット入力を考慮。
- 設定検証ツール
  - validate_config CLI（python -m kabusys.validate_config）を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の有無／パース検証、ライブ環境の警告を行う。--strict オプションで警告を失敗扱いにできる。
- ログ設定ユーティリティ
  - setup_logging を実装。ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。LOG_DIR 生成失敗時のフォールバック（コンソールのみ）やログレベル解決ルールを提供。
- プロセス優先度 / CPU affinity ユーティリティ
  - set_process_priority: Windows / POSIX を吸収してプロセス優先度設定を行う。権限不足や未対応環境では警告でスキップ。
  - set_cpu_affinity: 指定コア数へプロセス固定（権限不足時は警告でスキップ）。
- 実行エンジン起動スクリプト
  - run_execution.py を追加。ExecutionEngine の起動フローを実装:
    - プロセス優先度設定、Settings 読み込み、SQLite/duckdb 接続。
    - Paper Trading（KABUSYS_ENV=paper_trading）時は MockBrokerClient を使用し、paper 用 DB（デフォルト data/paper_trading.db）で本番 DB と分離。
    - BrokerClientFactory、OrderRepository、OrderManager、RiskManager（デフォルト設定あり）、Reconciler、ExecutionEngine を組み立てて実行。
    - data/stop_requested.flag による安全な停止、実行 PID ファイル管理、デーモン化されたスレッドでセッションを実行。
- 監視ループ起動スクリプト
  - run_monitoring.py を追加。SystemMonitor のポーリングループを実行:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。無効値はデフォルトにフォールバック。
    - 監視は設定にかかわらず本番用 sqlite_path を使用（設計方針に基づく）。
    - stop flag による停止検知、例外発生時のログ出力、リソースクローズを保証。
- モニタリング DB 初期化フック
  - init_monitoring_db を使用して監視テーブルの存在を保証（冪等）。
- DuckDB 統合
  - DuckDB コネクションを各種コンポーネントで使用するための接続処理を導入（分析用データ格納／参照を想定）。
- Paper Trading 検証レポート
  - tools/paper_verification_report.py を追加。paper_trading の SQLite（デフォルト data/paper_trading.db）を読み取り、稼働率/注文成功率/送信率/レイテンシ等を集計してレポート出力。
  - P95 計算、各種閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。
  - コマンドライン引数で期間指定（--from / --to）や DB パス指定 (--db) に対応。
- ポートフォリオ構築ライブラリ
  - portfolio モジュールを実装（純粋関数群、DB 参照なし）:
    - portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）。
    - risk_adjustment: apply_sector_cap（セクター集中上限の適用）、calc_regime_multiplier（レジームに応じた投下資金乗数。'bull'/'neutral'/'bear' をサポート。未知レジームは 1.0 でフォールバック）。
    - position_sizing: calc_position_sizes（allocation_method に応じた株数決定。lot_size による丸め、リスクベース / equal / score の各方式、コストバッファの考慮、aggregate cap によるスケーリングと残余分配ロジック）。
- research/factor_research（ファクター計算の雛形）
  - DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計のファクター計算モジュールを追加（モメンタム系ファクターの計算ロジック雛形を含む。将来的な拡張を想定）。
- パッケージ初期エクスポート
  - portfolio パッケージの __all__ を整備し、主要関数をトップレベルからインポートできるように。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Notes / 重要な設計・運用上の注意
- .env の自動読み込みはデフォルトで有効。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env ファイルは絶対に VCS にコミットしないでください（config_setup.py のヘッダにも注意喚起あり）。
- Paper Trading と本番 DB は分離設計:
  - モニタリングは常に sqlite_path（監視用本番 DB）を使用する設計になっているため、運用時は意図した DB パスの確認が必要です。
  - 実行エンジンは settings.is_paper に応じて paper_sqlite_path を使用し、本番 DB（monitoring.db）と分離する。
- KILL / STOP フラグ:
  - 停止は data/stop_requested.flag を置くことで行う。実行エンジン・監視ループはこのフラグを監視して安全停止する。
  - 本番環境で KILL_FLAG_CLEAR_ON_START=1 を設定するのは危険（validate_config で警告）。
- プロセス優先度や CPU affinity 設定は OS 権限に依存します。権限がない場合は警告が出てスキップされます。
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力を無効化してコンソール出力のみで継続します。ログディレクトリのパーミッション等を事前に確認してください。
- いくつかのモジュール（例: factor_research の一部、SystemMonitor の実装等）は本稿で示されたファイル群に依存していますが、現状では別ファイルに分かれているか実装が継続中の可能性があります。実運用前に統合テストを推奨します。

今後の TODO（コードから推測）
- factor_research の完全実装（全ファクター、Zスコア正規化など）。
- broker クライアント抽象化のテストと MockBroker の拡充（paper_trading の振る舞い検証）。
- 単元株（lot_size）を銘柄別に管理するための拡張（将来的な stocks マスタ導入）。
- 監視および実行のユニット/統合テストの充実化。
- 実行ログ・監視データの DuckDB を用いた分析パイプライン強化。

--- 
この CHANGELOG はコードの現状（推測）に基づいています。実際のリリースノートやコミット履歴に合わせて適宜修正してください。