CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠しています。
https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-21
--------------------

Added
- 基本的な自動売買フレームワークを初期リリースとして追加。
  - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
- 設定・環境変数管理
  - Settings クラスを実装し、各種環境変数をプロパティで提供（src/kabusys/config.py）。
  - プロジェクトルート検出と .env 自動ロード機構を実装（.env / .env.local の読み込み順, KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
  - .env ファイルのパースはエクスポート形式やクォート・インラインコメント等に対応。
  - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、DUCKDB_PATH、SQLITE_PATH、KILL_FLAG_CLEAR_ON_START などのデフォルトおよび妥当性チェックを実装。
- 設定関連 CLI
  - 対話式設定ウィザード: python -m kabusys.config_setup（.env の初期作成 / 更新支援）を追加（src/kabusys/config_setup.py）。
  - 設定検証 CLI: python -m kabusys.validate_config（.env と config/*.yaml の検証。--strict オプション対応）を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス存在チェック、YAML パースチェック（PyYAML があれば内容検証）等を実装。
- 実行 / 監視エントリポイント
  - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を通じてブローカークライアントを作成（MockBroker が選択される想定）。
    - ExecutionEngine をスレッドで実行し、data/stop_requested.flag による停止を監視。実行 PID ファイル管理。
    - RiskManager の初期設定値（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を採用。
  - 監視ポーリング起動スクリプト: src/kabusys/run_monitoring.py
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計。
    - stop flag（data/stop_requested.flag）検知で安全にループを終了。
    - check_once() の例外はログに例外情報を出力して次回ポーリングへ継続。
- ロギング / プロセス制御ユーティリティ
  - 統一ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR 環境変数や引数でログディレクトリを変更可能。ディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, macOS, FreeBSD）を吸収して優先度設定を行う。権限不足などは警告ログを出してスキップ。
- ポートフォリオ構築モジュール（純粋関数群、DB 非依存）
  - 候補選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順・タイブレークに signal_rank を使用。
    - calc_equal_weights / calc_score_weights（スコア全0 の場合は等配分へフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター比率が閾値（デフォルト 30%）を超える場合に当該セクターを新規候補から除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: レジームに応じて投入資金乗数を返却（bull=1.0, neutral=0.7, bear=0.3、未知レジームは1.0でフォールバック）。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method に基づく株数算出（risk_based / equal / score）。
    - risk_based: 損切り率・リスク許容率でベース株数を計算、単元株（lot_size）で丸め。
    - equal/score: ウェイトに基づく配分、per-position および aggregate の上限チェック、cost_buffer を考慮した保守的見積り、利用可能現金を超える場合はスケールダウンして端数は lot_size 単位で再配分。
    - 単元株丸め・aggregate cap の実装により、注文額が available_cash を超えないように調整。
    - 複数の安全弁（価格未取得時のスキップ、max_per_stock 上限の順守）を含む。
- Paper Trading 検証ツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標を集計してレポートを標準出力に出力。
    - 指標: 稼働率（uptime）、注文成功率(fill_rate)、送信率(send_rate)、リスク却下数、平均/最大/P95 レイテンシ。
    - P95 計算、日付フィルタ（--from / --to）対応、閾値に基づく PASS/FAIL 判定を実装。
- 監視 DB 初期化ユーティリティ呼び出し
  - init_monitoring_db を run_execution/run_monitoring で起動時に呼び出して監視テーブルの存在を保証（冪等）。

Changed
- 初期リリースのため変更履歴なし。

Fixed
- 初期リリースのため修正履歴なし。

Known limitations / Notes
- src/kabusys/research/factor_research.py はファイル末尾で未完の箇所があり（切断あり）、リファクタや完成が必要。
- position_sizing: 将来的に銘柄別 lot_size をサポートする TODO が存在（現状は全銘柄共通の lot_size を使用）。
- risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積になる可能性があり、将来的なフォールバック価格の導入がコメントに示唆されている。
- run_monitoring は明示的に本番 sqlite_path を使用する設計。テスト用途で別 DB を使いたい場合はスクリプトを調整する必要あり。
- ログディレクトリ作成やプロセス優先度設定は OS 権限や環境に依存し、失敗した場合は警告を出して処理を続行する挙動。

Security
- .env は絶対に Git にコミットしないよう注意喚起（config_setup のヘッダーに注記あり）。
- シークレット値は対話ウィザードでマスク表示されるが、ファイルには平文で書き出されるため取り扱いに注意。

Acknowledgements
- 本 CHANGELOG はコードベース内の docstring・コメント・実装内容から推測して作成しています。実際の変更履歴やリリースノートは開発・運用チームの公式記録を優先してください。