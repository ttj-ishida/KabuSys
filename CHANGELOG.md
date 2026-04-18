CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/1.0.0/).
変更は後方互換性のあるものを優先して記載します。

Unreleased
----------
（なし）

[0.1.0] - 2026-04-18
--------------------
初回リリース — 基本的な実行/監視/設定/ポートフォリオ構築ユーティリティを実装。

Added
- 全体
  - パッケージ初期リリース。バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - CLI/ユーティリティ群とコアライブラリ群を提供。
- 設定管理
  - .env ファイルの自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git / pyproject.toml から探索して自動ロード。
    - 読み込み順: OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による無効化対応。
    - .env のパースで export プレフィックス、クォート、インラインコメント、エスケープ等に対応。
    - 環境変数必須チェック用の _require ヘルパー、および Settings クラスを提供。
    - 設定プロパティ例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE（有効値検証）、KABUSYS_ENV（development/paper_trading/live 検証）、LOG_LEVEL 等。
- 設定ウィザード
  - 対話式 .env 作成/更新ウィザードを実装（src/kabusys/config_setup.py）。
    - デフォルト値・選択肢表示、シークレットマスク表示、既存 .env の読み込みと上書き保存機能。
    - 保存時のテンプレート出力（.env 書式）を用意。
- 設定検証
  - 起動前の設定検証 CLI を実装（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パス存在チェック（親ディレクトリの存在有無警告）、config/*.yaml の存在・パースチェック（PyYAML があれば内容検証）を実行。
    - KABUSYS_ENV=live の際の追加ガード（LINE 設定、KILL_FLAG_CLEAR_ON_START の警告）を実装。
    - --strict オプションで警告を FAIL 扱いにする機能。
- 実行エンジン
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - プロセス優先度設定（High）を行うユーティリティ呼び出し。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用して完全に本番 DB と分離（PAPER_TRADING_SQLITE_PATH）。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading の場合は MockBrokerClient を利用）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動し、別スレッドで run_session を実行。
    - 停止フラグ（data/stop_requested.flag）検知で安全停止。
    - PID ファイル出力（data/execution.pid）。
    - RiskManager の既定設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 関連, max_drawdown）を提供し、初期ポートフォリオ値に broker.get_available_cash() を使用。
- 監視（Monitoring）
  - SystemMonitor 起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバックして警告）。
    - 監視 DB は環境に依らず本番 sqlite_path を使用（監視は常に本番 DB に記録される設計）。
    - 停止フラグ検知でループを終了、例外時はログ出力して次サイクルまで継続。
    - DuckDB と SQLite の接続初期化（init_monitoring_db 呼び出しにより監視テーブルの存在を保証）。
- ロギング
  - 統一ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）をルートロガーに設定。
    - LOG_DIR / app_name に基づくログパス決定、ファイル出力失敗時はコンソールのみで継続。
    - 既存ハンドラをクリアして二重設定を防止。
- プロセス制御ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX (Linux/macOS/FreeBSD) を吸収して set_process_priority('high'|'normal'|'low') を提供。
    - set_cpu_affinity による CPU コア固定機能を実装（権限不足などは警告でスキップ）。
- ポートフォリオ構築ライブラリ
  - 銘柄選定と重み計算（pure functions、メモリ内）を実装（src/kabusys/portfolio/*）。
    - select_candidates: スコア降順・タイブレークロジックを実装。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重を実装（スコア合計が 0 の場合は等金額にフォールバック）。
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮、売却予定銘柄を除外、"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: market regime に応じたレバレッジ乗数（bull/neutral/bear）を提供。未知のレジームは警告して 1.0 にフォールバック。
    - calc_position_sizes: allocation_method ('risk_based' / 'equal' / 'score') に基づく発注株数決定、単元株丸め（lot_size）、per-position 上限・aggregate cap のスケーリングロジック、cost_buffer を考慮した保守的なコスト見積り、残差配分の実装。
  - portfolio パッケージエクスポートを追加（src/kabusys/portfolio/__init__.py）。
- ツール
  - Paper Trading 検証レポート生成スクリプトを実装（src/kabusys/tools/paper_verification_report.py）。
    - SQLite（paper_trading DB）から system_status / trade_logs / risk_logs を集計して稼働率、注文成功率、送信率、リスク却下数、平均/最大/P95 レイテンシを出力。
    - PASS/FAIL 判定基準を導入（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms）。
    - 日付フィルタ（--from / --to、ISO8601 UTC に変換）および --db オプションに対応。
- リサーチ（構想）
  - ファクター計算モジュールの骨組みを追加（src/kabusys/research/factor_research.py）。
    - モメンタム / ボラティリティ / 流動性 / バリュー等の計算方針と定数を定義。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - （注）ファイルは途中までの実装（骨組み）。今後の関数実装が必要。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / 運用上の注意
- 監視 (run_monitoring.py) は MONITOR_POLL_INTERVAL によるポーリング間隔制御を行います。無効な値が設定されるとデフォルト 60 秒にフォールバックします。
- Execution は paper_trading モードで本番 DB と分離されます。paper_trading 用 DB は環境変数 PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）で指定してください。
- .env ファイルは秘密情報を含むため、決してリポジトリにコミットしないでください（config_setup のヘッダも注意喚起を行っています）。
- ログは既定で logs/<app_name>.log に日次ローテートで出力されます。ログディレクトリ作成に失敗した場合は標準出力のみで継続します。

今後の予定（例）
- factor_research の各ファクター計算の実装完了
- ExecutionEngine / Monitoring の統合テスト追加
- Strategy / Data モジュールの追加実装（価格取得、シグナル生成など）
- 単体テスト・CI の整備

--- 
（この CHANGELOG はコードベースからの推測に基づいて作成されています。実際の変更履歴・リリースノートとして利用する場合は必要に応じて修正してください。）