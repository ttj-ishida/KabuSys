# Keep a Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠します。

全般
- バージョン管理: __version__ = 0.1.0
- リリース日: 2026-04-19

[0.1.0] - 2026-04-19
=====================

Added
-----
- 基本アプリケーション基盤を実装（初期リリース）。
  - パッケージ情報: kabusys.__init__ にバージョンを追加。

- 起動スクリプト / デーモン類
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔の上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル (data/stop_requested.flag) の検知で安全にループ終了。
    - Monitoring は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する仕様。
    - 実行開始時にプロセス優先度を "high" に設定。
    - sqlite3 / DuckDB への接続と監視 DB 初期化呼び出しを実装。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成（MockBroker を含む想定）。
    - ExecutionEngine を別スレッドで起動し、stop flag により安全に停止する制御を実装。
    - 起動時にプロセス優先度を "high" に設定。PID ファイル書き込みパスを設定。

- 設定管理・検証・ウィザード
  - config.py
    - 環境設定読み込み／管理クラス Settings を実装。
    - .env の自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化を提供。
    - .env パーサは export プレフィックス、クォート（シングル/ダブル）内のバックスラッシュエスケープ、インラインコメントの扱い等に対応。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境種別など）。
    - PAPER_FILL_MODE（paper trading の fill 動作）に対する検証と有効値チェックを実装。
    - デフォルト値: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db, PAPER_TRADING_SQLITE_PATH=data/paper_trading.db 等。

  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML が利用可能な場合）等を実行。
    - --strict オプションで警告を FAIL 扱いにする機能を追加。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定の確認や KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。

  - config_setup.py
    - .env の初期作成・更新を対話的に支援するウィザード CLI を追加。
    - J-Quants / kabu API / DB パス / LOG_LEVEL / KILL_FLAG_CLEAR_ON_START 等の設定項目を対話形式で入力し .env を生成可能。
    - 既存 .env の読み込み・現在値再利用、シークレット項目はマスク表示、生成された .env の保存確認を実装。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定 select_candidates（スコア降順、タイブレークロジック）を実装。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）を実装。

  - portfolio/risk_adjustment.py
    - セクター集中上限を適用する apply_sector_cap を実装（当日売却予定コードの除外や "unknown" セクターの挙動を明示）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未知レジームは 1.0 にフォールバック）。

  - portfolio/position_sizing.py
    - ポジションサイズ計算 calc_position_sizes を実装。
    - allocation_method=("risk_based"|"equal"|"score") に対応。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap によるスケーリング、コストバッファ考慮、残余キャッシュを用いた端数配分ロジックを実装。
    - price 欠損時のスキップやログ記録を考慮。

  - portfolio パッケージ化により上記関数群をエクスポート。

- リサーチ / ファクター計算（基盤）
  - research/factor_research.py（計算方針と定数を含む）
    - Momentum / Value / Volatility / Liquidity 系ファクター算出の方針を実装（DuckDB 接続を受け prices_daily / raw_financials を参照する設計）。
    - Pパラメータ（21/63/126/200 日など）やスキャン範囲の定義など、モジュール基盤を追加。
    - （注）ファイル末端での実装が途中の箇所あり（以降の計算ロジックは継続実装予定）。

- ユーティリティ
  - utils/logging_setup.py
    - 共通ログ設定ユーティリティを実装。
    - root ロガーに stdout StreamHandler と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定。
    - ログディレクトリの自動作成（失敗時はファイル出力をスキップして stdout のみで継続）。
    - ログレベル解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）。
    - stdout を使う理由やハンドラ再設定ロジック（重複防止）を説明する実装。

  - utils/process_priority.py
    - マルチプラットフォーム（Windows / POSIX）でプロセス優先度設定（nice / Windows priority class）を吸収するユーティリティを実装。
    - set_process_priority(level) で "high" / "normal" / "low" を設定（権限不足や未対応 OS の場合は警告でスキップ）。
    - set_cpu_affinity(cpu_count) により CPU affinity を最初の N コアに固定する補助関数を実装（未対応時は警告でスキップ）。

- 監視 DB 初期化連携
  - monitoring.monitoring_db.init_monitoring_db 呼び出しを起動スクリプトに組み込み、監視テーブルが存在することを保証（冪等に実行）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / --db）から検証レポートを生成する CLI を追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定を出力する。
    - P95 の算出、期間フィルタリング、テーブル存在チェックや例外時のフォールバックを実装。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を設定。

Changed
-------
- 初回リリースのため変更履歴はありません（新規実装）。

Fixed
-----
- 初回リリースのため修正履歴はありません。

Security
--------
- 初回リリースのためセキュリティ修正履歴はありません。
- 注意点:
  - .env ファイルは絶対に Git にコミットしない旨を config_setup のテンプレートに明記。
  - 機密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）は Settings で必須チェックを行い、不在時は起動前に明示的にエラーを出す。

Notes / Implementation details
------------------------------
- DB
  - DuckDB は分析用（duckdb_path）、SQLite は監視・注文履歴用（sqlite_path / paper_sqlite_path）として使い分け。
  - run_monitoring は環境に関わらず監視用 sqlite_path（デフォルト data/monitoring.db）を使用する点に注意。

- プロセス管理
  - 実行スクリプトは起動時に優先度を高く設定する試みを行う（権限不足時は警告）。
  - 停止制御はプロジェクトルート/data/stop_requested.flag 等のフラグファイルに依存する。

- ロギング
  - stdout への出力を基本としつつ、logs/<app_name>.log に日次ローテーションで出力（ディレクトリ作成に失敗した場合はファイル出力をスキップ）。

- 環境変数パーサ
  - export プレフィックスやクォート内バックスラッシュのエスケープ、インラインコメントの取り扱い等、実務でよくある .env 書式のバリエーションに対応。

今後
----
- research/factor_research.py の完全実装（各ファクター計算の SQL/Python 実装）。
- strategy / execution 周りの単体テストと、MockBroker を用いた統合テストの追加。
- 更なる監視メトリクス、アラート送信 (LINE 等) の実装とドキュメント整備。
- 単元ごとの型注釈の強化・公開 API の安定化。

----
この CHANGELOG はコードベースから推測して作成しています。必要であれば項目の追加修正・翻訳調整を行います。