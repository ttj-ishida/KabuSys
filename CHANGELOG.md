CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" 準拠です。

全体方針
--------
- バージョン番号はパッケージ内の __version__ に合わせています（現行: 0.1.0）。
- 各項目はファイル・機能単位で要点を要約しています。実装の細かい挙動やパラメータは該当ソース（src/kabusys 以下）を参照してください。

Unreleased
----------
（なし）

[0.1.0] - 2026-04-24
--------------------
Added
- 基本アプリケーション骨格を実装
  - パッケージのメタ情報を追加（src/kabusys/__init__.py、__version__ = "0.1.0"）。
- 環境設定管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - .env の自動読み込み（プロジェクトルート検出: .git または pyproject.toml 基準）。
    - .env と .env.local の読み込み順序（OS 環境変数優先）。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
    - 各種プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判別等）。
    - PAPER_FILL_MODE の検証（"instant"/"partial"/"never"/"reject" のみ許容）。
    - KABUSYS_ENV / LOG_LEVEL の値検証。
  - .env のパースロジックを強化
    - export プレフィックス対応、クォート文字列（'"/"）のエスケープ処理、行末コメントの扱い等をサポート（src/kabusys/config.py）。
- 設定ウィザード CLI
  - 対話式 .env 生成・更新ツールを追加（src/kabusys/config_setup.py）。
    - 各設定項目の説明、既存 .env の取り込み、シークレット値のマスク表示、保存確認を実装。
    - .env の書式で安全に書き込む機能を提供。
- 設定検証 CLI
  - 起動前チェックツールを実装（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス親ディレクトリ確認、config/*.yaml の存在と PyYAML によるパース検査（PyYAML 未導入時は警告）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定確認や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を失敗扱いにできる。
- 実行 / 監視起動スクリプト
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - 起動時にプロセス優先度を "high" に設定。
    - paper_trading モードでは専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory により本番/ペーパーのクライアント選択を行う設計（ドキュメント化）。
    - 停止フラグ（data/stop_requested.flag）および pid ファイル管理による制御ループを実装。
  - SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告の上デフォルトにフォールバック。
    - 監視用 DB（monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明記。
    - 停止フラグ検出・例外ハンドリング・finalize（接続クローズ）を実装。
- ロギング基盤
  - 統一的なログ設定ユーティリティを実装（src/kabusys/utils/logging_setup.py）。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - ログレベル・ログディレクトリの解決順を定義（関数引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - stdout を使用することでタスクスケジューラ等とのリダイレクト運用を想定。
- プロセス優先度 / CPU affinity ユーティリティ
  - クロスプラットフォーム対応のプロセス優先度設定と CPU affinity を実装（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収し、psutil を利用して nice 値 / priority を設定。
    - 権限不足や未対応プラットフォームでは警告を出してスキップする堅牢な実装。
- ポートフォリオ構築ロジック（純粋関数群）
  - 候補選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順・タイブレーク条件を実装。
    - calc_equal_weights / calc_score_weights: スコア正規化とフォールバック（全スコアが 0 の場合は等配分）。
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター別エクスポージャー算出と、上限超過セクターの新規候補除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）と未知レジームの警告フォールバック。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の allocation_method を実装。
    - lot_size 単位で丸め、1銘柄上限や aggregate cap（利用可能現金）を考慮したスケーリングと残差処理ロジックを実装。
    - cost_buffer を用いた保守的見積り（手数料・スリッページ）。
- Paper Trading 検証ツール
  - 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率（fill）, 送信率（send）, P95 レイテンシ等の集計と閾値判定を実装。
    - デフォルトの DB パスは data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で上書き可能）。
    - P95 計算ユーティリティや日付フィルタの実装。
- DuckDB / SQLite 統合
  - 分析用に DuckDB 接続、監視/履歴用に SQLite 接続を利用する実装方針を反映（各起動スクリプトで接続確立）。
- 監視 DB 初期化
  - init_monitoring_db 呼び出しで監視テーブルの存在を保証（冪等に初期化）。

Changed
- 初期リリースのため該当なし（最初の公開）。

Fixed
- 初期リリースのため該当なし。

Deprecated
- 初期リリースのため該当なし。

Removed
- 初期リリースのため該当なし。

Security
- 初期リリースのため該当なし。

補足（実装上の注意点）
- run_monitoring は MONITOR_POLL_INTERVAL が不正（整数でない、0 以下等）の場合、警告してデフォルト 60 秒にフォールバックします。
- run_monitoring は監視 DB として settings.sqlite_path（本番用パス）を使用します。開発/ペーパーでの監視データ分離が必要な場合は設計上の考慮が必要です。
- run_execution は paper_trading モード時に PAPER_TRADING_SQLITE_PATH を使用して DB を分離します。
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされます。CI/テスト等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用してください。
- process_priority / CPU affinity 操作は権限や OS に依存します。失敗した場合は警告を出して処理を継続します。

今後の予定（短期）
- research モジュール（factor_research.py）はファクター計算ロジックを含むが一部未完（ファイル末尾が途中）。DuckDB に対するクエリ最適化とユニットテスト整備を予定。
- broker / execution 系のユニットテスト強化（MockBrokerClient の挙動確認、risk_manager/emulator のテストなど）。
- ログ・メトリクスの外部送信（LINE 通知や外部モニタリング）統合の拡充。

----- 
（この CHANGELOG はソースコードの内容から推測して作成しています。実際の変更履歴やリリースノートはリポジトリのコミット履歴／リリース定義を優先してください。）