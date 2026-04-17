CHANGELOG
=========
（Keep a Changelog 準拠・日本語）

フォーマット:
- Unreleased（開発中の変更）
- 各リリースはバージョンと日付を付記

Unreleased
----------
（現在なし）

0.1.0 - 2026-04-17
-----------------
初期リリース。コードベースから推測される主な機能・改善・仕様を記載します。

Added
- 基本構成・エントリポイント
  - パッケージ初期化とバージョン番号（kabusys.__version__ = "0.1.0"）。
  - 実行用スクリプト:
    - run_execution.py: ExecutionEngine 起動スクリプト。バックグラウンドスレッドでエンジンを起動し、stop フラグや pid ファイルで制御。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - CLI ツール:
    - config_setup.py: 対話式 .env ウィザード（.env の作成・更新支援）。
    - validate_config.py: .env と config/*.yaml を起動前に検証する CLI（--strict オプションで警告も FAIL 扱いに）。
    - tools.paper_verification_report: ペーパートレード用検証レポート生成ツール（期間指定・DB 指定可能）。

- 環境・設定管理
  - Settings クラス（kabusys.config）により環境変数を集中管理。プロパティ経由で取得する設計。
  - 自動 .env ロード機構:
    - プロジェクトルート検出（.git または pyproject.toml を基準）による .env / .env.local の自動読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサーの強化:
    - export プレフィックス対応、クォート値内のエスケープ解釈、インラインコメント処理（クォートなしは '#' の直前が空白/タブでコメントとみなす）など、現実的な .env 構文をサポート。
    - 自動ロード時に OS 環境変数を保護（.env.local は上書き可能だが OS 環境変数は protected）。

- ポートフォリオ構築・サイズ計算（純粋関数群、DB 非依存）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順で候補選択（タイブレークに signal_rank を使用）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（スコア合計が 0 の場合は等配分へフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限（既存ポジションのセクター比率が上限を超える場合、新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数（未知レジームはフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: リスクベース／等配分／スコア配分に対応した発注株数の算出。単元株丸め、1銘柄上限、aggregate cap（利用可能現金でスケールダウン）、cost_buffer（スリッページ/手数料の保守的見積）等を実装。

- 実行・リスク管理基盤
  - run_execution が環境に応じて paper_trading 用 DB（分離された PAPER_TRADING_SQLITE_PATH）を使用。KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用する想定（BrokerClientFactory）。
  - RiskManager のデフォルト構成値（max_position_pct / max_utilization / rate_limit_per_sec / circuit_breaker 等）を Execution 起動時に設定。
  - Reconciler / OrderManager / OrderRepository を組み合わせて ExecutionEngine を初期化・起動。

- 監視機能
  - run_monitoring により SystemMonitor を定期実行。監視 DB（SQLite）と分析用 DuckDB を使用し、監視テーブルの初期化を保証（init_monitoring_db）。
  - 停止フラグファイル（data/stop_requested.flag）でグレースフルにループを終了可能。

- DuckDB 統合
  - DuckDB を利用したリサーチ/分析モジュール（research.factor_research）と Execution/Monitoring の分析用途向け接続を実装。

- 研究用ファクター計算
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離率を DuckDB から計算。
    - calc_volatility: ATR、20日平均売買代金、出来高比などを計算するための基盤（NULL の伝播制御などデータ欠損を考慮）。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority: psutil を使いプラットフォーム間でプロセス優先度を設定（Windows / POSIX に対応、失敗時は警告でスキップ）。
    - set_cpu_affinity: 指定コア数へ CPU affinity を固定するユーティリティ（利用不可時は警告でスキップ）。

- ペーパートレード検証レポート
  - tools.paper_verification_report:
    - system_status / trade_logs / risk_logs を集計して稼働率、注文成功率（Fill）、送信率（Sent）、レイテンシ（平均/最大/P95）等を算出。
    - 閾値に基づく PASS/FAIL 判定（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200 ms など）。

Changed
- （該当なし／初期リリース）

Fixed
- （該当なし／初期リリース）
  - ただし実装上以下の例外処理やフォールバックが明示されている：
    - .env 読み込み失敗時の警告表示。
    - process_priority / cpu_affinity 設定が失敗した場合にログでスキップ。
    - run_monitoring の monitor.check_once() 内例外は捕捉して次回ポーリングへ継続。

Security
- .env 作成ウィザードの出力ヘッダで「.env は絶対に Git にコミットしないこと」を明記。
- Settings では必須環境変数未設定時にエラーを出す設計（_require）。

Notes / その他の設計上のポイント（実装から推測）
- 環境分離:
  - paper_trading 用 DB と本番 DB を明確に分離。ペーパートレードのデータは data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）に記録される想定。
- フォールバックと安全弁:
  - 多くの算出関数がデータ不足時に None を返すか等価のフォールバックを行う設計で、上位ロジックで安全に扱えるよう配慮されている。
- ロギング/監視:
  - 各所で logger を用いた詳細ログを出力、運用時に情報・警告・例外ログで原因追跡しやすい構成。
- 可搬性:
  - プラットフォーム差分（Windows / POSIX）や optional な依存（psutil, PyYAML）を考慮した実装。依存がない環境では該当チェックをスキップして graceful degrade する。

将来の改善候補（コード中の TODO 等から推測）
- position_sizing: 銘柄毎の lot_size をサポートする（将来的に stocks マスタを参照する想定）。
- apply_sector_cap: 価格欠損時のフォールバック（前日終値や取得原価を使う）を実装。
- config/*.yaml の内容検証は PyYAML がインストールされている場合にのみ行われるため、CI などで明示的に依存を宣言するとよい。

以上。コード内容から推測してまとめました。追加でリリースノートの粒度や翻訳（英語版）の要望があれば対応します。