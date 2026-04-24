CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。  
フォーマットの詳細: https://keepachangelog.com/ (英語)

Unreleased
----------

- （現時点なし）

[0.1.0] - 2026-04-24
--------------------

Added
- 基本アプリケーション構成を追加（初期リリース）。
  - パッケージ情報: kabusys.__version__ = "0.1.0"。
- 実行用・監視用の起動スクリプトを追加。
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite(DB) を使用し、本番 DB と分離。
    - ブローカークライアントは BrokerClientFactory 経由で作成（本番/モックを切替え可能）。
    - エンジンはデーモンスレッドで実行され、data/stop_requested.flag により安全に停止可能。
    - 起動時にプロセス優先度を "high" に設定する処理を導入。
    - init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず production 相当の sqlite_path を使用する設計。
    - stop フラグ（data/stop_requested.flag）検知でループを終了。
    - check_once() 内例外は捕捉してログに記録しループ継続する堅牢な実装。

- 設定管理機能を追加。
  - config.py:
    - Settings クラスを提供し、環境変数から各種設定を取得する統一インターフェースを追加。
    - .env 自動ロード機能を追加（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env 読み込みは OS 環境変数を保護（上書き禁止）しつつ .env.local で上書き可能。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, KILL_FLAG_CLEAR_ON_START 等のプロパティを追加。
    - KABUSYS_ENV / LOG_LEVEL などの値検証を実装（無効値で例外を投げる）。
  - config_setup.py: 対話式ウィザードにより .env の初期作成・更新を支援する CLI を追加。
    - シークレット入力のマスクやデフォルト値・選択肢をサポート。
    - .env の生成テンプレートを整備（.env を絶対にコミットしない旨の注意文を含む）。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数・パス・YAML 設定ファイルの存在や本番環境ガードなどをチェック。
    - --strict オプションで警告を FAIL 扱いにできる。

- 監視・検証ツールを追加。
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率、送信率、P95 レイテンシ等を計算し PASS/FAIL 判定を出力。
    - P95 計算、期間指定（--from / --to）、DB パス指定（--db / 環境変数）をサポート。
  - monitoring 側初期化を実行する init_monitoring_db 呼び出しを各起動スクリプトに統合。

- ポートフォリオ構築ライブラリを追加（pure functions）。
  - portfolio/portfolio_builder.py:
    - select_candidates: シグナルのスコアに基づく選定。
    - calc_equal_weights / calc_score_weights: 重み算出（スコア合計が 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限を適用するフィルタ。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数算出。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap によるスケールダウン、cost_buffer の考慮などを実装。

- 研究用ファクター計算モジュールを追加（research/factor_research.py）。
  - Momentum / Value / Volatility / Liquidity に関する設計方針と計算ロジックの骨組みを実装（DuckDB 接続を受け取る設計）。

- 汎用ユーティリティを追加・強化。
  - utils/logging_setup.py:
    - stdout への StreamHandler と TimedRotatingFileHandler（日次、30 日保持）をルートロガーに設定する統一ロギング設定を提供。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - LOG_LEVEL / LOG_DIR の解決順を実装。
  - utils/process_priority.py:
    - Windows / POSIX を吸収したプロセス優先度設定を実装（high/normal/low）。
    - CPU affinity を最初の N コアに固定する機能を追加。権限不足等の失敗は警告に留めて安全にスキップ。

Changed
- ログ設計:
  - ログは stdout に出力するように統一（cron / スケジューラ向けに stderr と分ける仕様）。
- .env 自動ロード:
  - OS 環境変数の保護（protected set）を導入して、意図しない上書きを防止。

Fixed
- 設定／パーサの堅牢化:
  - .env パーサは export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いなどを正しく処理するよう改善。
  - MONITOR_POLL_INTERVAL の不正値（0や負数、非整数）に対してデフォルトにフォールバックするようにし、警告ログを出力するように修正。
- 重み計算の安全性:
  - calc_score_weights は全スコア合計が 0 の場合に等金額配分へフォールバックして警告を出すように修正。
- プロセス優先度設定の失敗処理を穏健化（AccessDenied 等をキャッチして警告ログを出力し続行）。

Security
- 秘密情報取り扱い改善:
  - config_setup の対話入力でシークレットはマスクして表示。
  - .env のテンプレートに「絶対に Git にコミットしないこと」を明記。

Notes / Implementation details
- DB 関連:
  - 監視用には sqlite3（監視テーブル、trade_logs 等）を使用。分析や研究用に duckdb を使用する設計（duckdb 接続を各コンポーネントに注入）。
  - init_monitoring_db は冪等に監視テーブルの存在を保証する目的で呼ばれる。
- 実行エンジンの安全弁:
  - 起動前に data/stop_requested.flag をチェックし、既に停止フラグが立っている場合は起動を中止。
  - 起動中は同フラグをポーリングして停止をトリガーできる。
- Paper Trading:
  - PAPER_FILL_MODE（instant/partial/never/reject）を設定可能にし、MockBroker の挙動を切替えるためのフックを用意。
  - paper_trading 用の SQLite パスは PAPER_TRADING_SQLITE_PATH で上書き可能（デフォルト data/paper_trading.db）。

既知の制限
- research/factor_research.py はファクター計算の主要な設計と一部機能を実装しているものの、計算範囲（スキャン日数など）の定数や完全な SQL 実装は今後の整備が必要。  
- 銘柄別の lot_size（単元株数）に関する将来的な拡張点はコメントで残している（現状は全銘柄共通の lot_size を想定）。
- apply_sector_cap は価格欠損（price が 0.0）の場合にエクスポージャーが過少見積りとなる可能性があり、将来的にフォールバック価格ロジックを追加予定。

-- End of changelog --