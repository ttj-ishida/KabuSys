CHANGELOG
=========

すべての注目すべき変更を記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。セマンティックバージョニングに従います。

Unreleased
----------
- なし

0.1.5 - (ツール追加)
--------------------
Added
- Paper Trading 検証用の CLI スクリプトを追加。
  - kabusys.tools.paper_verification_report: 指定期間の稼働率・注文成功率・送信率・レイテンシなどを集計して PASS/FAIL 判定を出力する。
  - DB パスはコマンド引数または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。
  - P95 計算や各種しきい値による判定ロジックを実装。

0.1.4 - (ポートフォリオ構築・ポジションサイズ)
----------------------------------------------
Added
- ポートフォリオ構築関連の純関数群を実装。
  - kabusys.portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選定。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重の重み計算。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限の適用ロジック。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: 等分配／スコア／リスクベースに基づく発注株数決定、単元株丸め、aggregate cap によるスケーリング、コストバッファ考慮などのロジックを実装。

Changed
- ポートフォリオ API をパッケージ化して kabusys.portfolio からまとめてエクスポート。

0.1.3 - (ロギング・プロセス優先度周りの改善)
---------------------------------------------
Added
- 統一ロギング設定ユーティリティを導入。
  - kabusys.utils.logging_setup.setup_logging:
    - stdout への StreamHandler と日次ローテーションを行う TimedRotatingFileHandler をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR 環境変数を尊重、既存ハンドラをクリアして二重出力を防止。
    - ファイルハンドラ作成失敗時はコンソールのみで継続。
    - デフォルトで logs/<app_name>.log を使用、30日分保持。

Added
- プロセス優先度・CPU affinity 設定ユーティリティを追加。
  - kabusys.utils.process_priority:
    - set_process_priority(level): Windows/Linux/Mac の差分を吸収して優先度を設定（"high"/"normal"/"low"）。
    - set_cpu_affinity(cpu_count): 指定コア数に固定（サポートされる OS のみ）。
    - 起動スクリプト（execution / monitoring）で起動直後に優先度を "high" に設定するよう変更。

Fixed
- ログディレクトリ作成失敗時の挙動を明確化し、標準エラーに警告を出すようにした。

0.1.2 - (実行・監視ランタイムの整備)
------------------------------------
Added
- 実行エンジン起動スクリプトを追加。
  - src/kabusys/run_execution.py:
    - ExecutionEngine の起動フロー（ブローカクライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、スレッド実行、停止フラグ検知による安全停止）。
    - Paper Trading モード (KABUSYS_ENV=paper_trading) 時は MockBrokerClient を使用し、本番 DB と分離して data/paper_trading.db を利用する（デフォルト）。
    - 起動時にプロセス優先度を high に設定、PID ファイル書き出しサポート。
- 監視起動スクリプトを追加。
  - src/kabusys/run_monitoring.py:
    - SystemMonitor のポーリングループ実装。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する挙動を明記。
    - 停止フラグ（data/stop_requested.flag）検知で安全にループ終了。
    - check_once() の例外はログ出力して次のポーリングへ継続。
- DuckDB 接続サポートを追加（両スクリプトで duckdb.connect を使用）。

Changed
- 実行と監視で DB 初期化（監視テーブルの冪等的初期化）処理を行うようにして、起動時に必要テーブルが存在することを担保。

0.1.1 - (設定読み込みと検証ツール)
---------------------------------
Added
- 環境変数 / .env の読み込み機構を強化。
  - src/kabusys/config.py:
    - プロジェクトルートを .git / pyproject.toml から自動検出して .env/.env.local を自動読み込み（テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env パーサーを堅牢化（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなど）。
    - Settings クラスを追加して各種設定値（DB パス、API トークン、しきい値、環境判定フラグ等）にアクセス可能に。
    - PAPER_FILL_MODE 等のバリデーションを実装。
- 対話式の設定ウィザードを追加。
  - src/kabusys/config_setup.py:
    - .env を対話的に作成・更新するウィザード。既存値の読み込み、シークレットマスク、デフォルト提示、保存確認を実装。
- 設定検証コマンドを追加。
  - src/kabusys/validate_config.py:
    - 起動前に必須環境変数や config/*.yaml、DB パスの存在などを検証する CLI。
    - --strict オプションで警告を失敗扱いにできる。

Changed
- 環境読み込み順序: OS 環境 > .env.local > .env（OS 環境は上書き禁止）。

0.1.0 - Initial release
-----------------------
Added
- パッケージ初期リリース。
  - コア機能:
    - 実行系（execution）と監視系（monitoring）の骨組み。
    - 注文管理・リスク管理・実行エンジンのためのモジュール構成（ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager のインターフェース想定）。
    - 監視用 DB と監視フローの基本。
  - ポートフォリオ / 戦略関連:
    - 研究用モジュール（factor_research）の雛形（DuckDB を使ったファクター計算の方針と一部定数）。
  - ユーティリティ:
    - ロギング・プロセス優先度・ユーティリティモジュールの基礎。
  - パッケージ metadata:
    - __version__ = "0.1.0"

Notes / 既知の TODO
------------------
- factor_research.calc_momentum の実装が途中（スニペット末尾で途切れている）ため、研究モジュールの一部ロジックは未完。
- position_sizing や risk_adjustment の将来的な拡張（銘柄ごとの lot_size を stocks マスタで持たせる等）について TODO コメントが残っている。
- 一部ファイル I/O（ログディレクトリ作成、SQLite/DuckDB ファイル作成等）での権限エラー処理は現状ログ出力にとどまるため、運用時に注意が必要。

ライセンス / バージョニング
---------------------------
- セマンティックバージョニングに従ってリリース管理を行ってください。
- 重大な互換性のある変更はメジャーバージョンを引き上げて記録してください。

以上