# Changelog

すべての注目すべき変更はここに記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

※ バージョン番号はパッケージ内の __version__ に合わせています。

[0.1.0] - 2026-04-17
--------------------

Added
- 基本アプリケーションとモジュール群を初回リリースとして追加。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）へ完全分離して記録。  
    - ブローカーファクトリ、OrderRepository、OrderManager、RiskManager、Reconciler を組み立て、バックグラウンドスレッドでセッションを実行。停止フラグ検知と安全なシャットダウンをサポート。  
    - ExecutionEngine に対するデフォルト RiskConfig を定義（max_position_pct、max_utilization、rate_limit_per_sec 等）。初期ポートフォリオ値は broker.get_available_cash() から取得。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。  
    - 停止フラグファイル (data/stop_requested.flag) の存在でループを終了。監視は環境にかかわらず本番 sqlite_path を使用するように設計。
- 設定管理
  - config.py: Settings クラスを追加。環境変数・.env ファイルの自動読み込み（.env, .env.local の優先度）、必須値チェック用の _require、各種パス・フラグ・閾値のプロパティを提供。  
    - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject"）や KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。  
    - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。プロジェクトルートは .git / pyproject.toml を探索して検出。
  - config_setup.py: .env の対話式ウィザードを追加。既存 .env の読み込み・表示、シークレットマスキング、書き込みテンプレート（.env に保存する際の注意コメント含む）を提供。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数、KABUSYS_ENV 値、DB パスの親ディレクトリ、config/*.yaml の存在と YAML パース（PyYAML があれば詳細検証）をチェック。--strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定と重み計算を実装。select_candidates（スコア降順 + tie-breaker）、calc_equal_weights、calc_score_weights（全スコア0の場合は等配分へフォールバック）を提供。
  - portfolio/position_sizing.py: 発注株数算出ロジックを実装。  
    - allocation_method: "risk_based"（リスクベース）および "equal"/"score" をサポート。  
    - lot_size（単元株）で丸め、per-stock 上限（max_position_pct）や aggregate cap（available_cash）を考慮したスケーリング、cost_buffer を用いた保守的コスト見積り、端数再配分ロジックを実装。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap（売却予定銘柄を除外して既存セクター暴露を算出、上限超過セクターの候補除外）と市場レジーム倍率 calc_regime_multiplier（bull/neutral/bear）を実装。未知レジームは警告を出して 1.0 でフォールバック。
  - portfolio/__init__.py: 上記機能をパッケージエクスポート。
- リサーチ / ファクター計算
  - research/factor_research.py: DuckDB 接続を用いるファクター計算モジュールを追加。  
    - Momentum: mom_1m/3m/6m、ma200_dev（200 日移動平均乖離）を計算。データ不足時は None を返す仕様。  
    - Volatility 等（ATR, avg_turnover, volume_ratio 等）の実装方針とスキャンウィンドウを定義（DuckDB SQL を用いた効率的集計）。
- ユーティリティ
  - utils/process_priority.py: プロセス優先度（Windows と POSIX の差分を吸収）と CPU affinity の設定機能を追加。set_process_priority("high"|"normal"|"low") と set_cpu_affinity(n) を提供。権限不足や未対応環境では警告を出して安全にスキップ。
- 監視 DB 初期化
  - monitoring/monitoring_db.py（呼び出しを想定）との連携により、起動時に監視テーブルの存在を保証する init_monitoring_db を呼ぶフローを run_monitoring と run_execution に組み込み（冪等動作を想定）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。  
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計・表示。閾値（例: uptime >= 99%、fill_rate >= 90%、P95 <= 200ms）を定義して PASS/FAIL を判定。日付フィルタ、DB パスの指定（--db または PAPER_TRADING_SQLITE_PATH）をサポート。P95 計算や欠損時の N/A 表示を実装。
- パッケージメタ
  - __init__.py: パッケージ名とバージョン (__version__ = "0.1.0") を設定。

Changed
- 初回リリースのため「変更」はありません（すべて新規追加）。

Fixed
- 初回リリースのため「修正」はありません。

Notes / 実装上の重要点・設計注意
- .env パーサはシングル/ダブルクォート、export プレフィックス、行末コメント（条件付き）に対応。自動読み込みでは OS 環境変数を保護して .env.local を上書き可能にする実装。プロジェクトルートが検出できない場合は自動ロードをスキップするため、パッケージ配布後の環境でも安全に動作する設計。  
- run_monitoring は監視処理の安全性を重視し、例外発生時でもループを継続して次のポーリングまで待機する挙動を採用。  
- position_sizing のスケーリング・丸めロジックは単元株（lot_size）に強く依存するため、将来的に銘柄別 lot_size の導入を想定した拡張ポイントをコメントで残している。  
- calc_regime_multiplier は Strategy 側の設計（Bear では通常 BUY シグナルが生成されない）を想定した補助的な安全弁として実装されている。  
- run_execution/run_monitoring では起動直後にプロセス優先度を "high" に設定する試みを行う。権限がない環境では警告を出して続行する。

今後の計画（抜粋）
- 銘柄別単元株対応（stocks マスタによる lot_size）の導入。  
- monitoring / execution の詳細な統計・メトリクス収集とダッシュボード連携（DuckDB を用いた分析パイプライン拡張）。  
- テスト充実（特に position_sizing のスケーリングロジック、ファクター計算のエッジケース）。

----------------------------------------------------
この CHANGELOG はソースから推測して作成しています。実際のリリースノートとして利用する際は、変更点の差分・マージ履歴・リリースプロセスに合わせて調整してください。