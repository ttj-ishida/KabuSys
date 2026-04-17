CHANGELOG
=========

すべての注目すべき変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。

[0.1.0] - 2026-04-17
-------------------

Added
- 初回リリース。KabuSys の基本機能群を実装しました（自動売買システムのコア機能）。
- パッケージ情報
  - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
  - エクスポートモジュール群: data, strategy, execution, monitoring。

- 設定 / 初期化 (src/kabusys/config.py)
  - .env 自動ロード機構を実装（プロジェクトルートを .git / pyproject.toml で検出）。
  - .env と .env.local の読み込み順を定義し、OS 環境変数を保護する仕組みを実装。
  - 環境変数取得ユーティリティ（必須変数チェック、各種デフォルト、バリデーション）。
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の検証ロジックを実装。
  - settings オブジェクトを提供。

- 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
  - ExecutionEngine 起動フローを実装:
    - プロセス優先度を設定（高優先）。
    - SQLite / DuckDB 接続を確立（paper_trading 環境時は paper_db を使用して本番 DB と分離）。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - ExecutionEngine を別スレッドで起動し、停止フラグ（data/stop_requested.flag）を監視して安全終了。
  - デフォルトのリスク設定（RiskConfig）を導入（max_position_pct, max_utilization, rate_limit_per_sec 等）。
  - エンジン用 PID ファイル path の取り扱い。

- 監視プロセス起動スクリプト (src/kabusys/run_monitoring.py)
  - SystemMonitor の初期化とポーリングループを実装。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
  - 監視用 DB 初期化（Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用する仕様）。
  - 停止フラグ検知でループを終了。

- ユーティリティ: プロセス優先度 / CPU affinity (src/kabusys/utils/process_priority.py)
  - クロスプラットフォームでのプロセス優先度設定を実装（Windows / POSIX を吸収）。
  - CPU affinity を N コアに固定する関数を提供。
  - 権限不足や未対応プラットフォーム時は警告を出してスキップする安全設計。

- ポートフォリオ構築 (src/kabusys/portfolio/*)
  - 銘柄選定 / 重み計算 (portfolio_builder.py)
    - select_candidates: スコア降順 + signal_rank タイブレーク。
    - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合は等金額へフォールバック）。
  - セクター制限 / レジーム乗数 (risk_adjustment.py)
    - apply_sector_cap: 既存ポジションのセクターエクスポージャーに基づき新規候補を除外。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull/neutral/bear）。
  - 株数決定 / 丸めロジック (position_sizing.py)
    - risk_based / equal / score の allocation_method をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap によるスケールダウン、cost_buffer を考慮。
    - 合計投資額が可用現金を上回る場合のスケーリングと端数配分アルゴリズムを実装。

- リサーチ / ファクター計算 (src/kabusys/research/*)
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を DuckDB 上で計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比を計算。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を計算（財務データがない場合は NULL 扱い）。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）で将来リターンを取得。
    - calc_ic / rank / factor_summary: スピアマン相関（IC）計算、ランク付け、統計サマリーを実装。
  - research パッケージは外部依存を増やさず DuckDB の SQL と純 Python で実装される設計。

- AI ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
  - raw_news を銘柄別に集約し、OpenAI (gpt-4o-mini) を用いて各銘柄に対するセンチメントスコアを算出し ai_scores に書き込む設計。
  - バッチ処理（最大 _BATCH_SIZE=20）、トークン肥大化対策（最大記事数・文字数トリム）、429/ネットワーク/5xx に対する指数バックオフ再試行、レスポンスのバリデーション、±1.0 にクリップするロジックを導入。
  - score_news(): API キー未設定時は ValueError を送出。
  - ニュース収集ウィンドウの計算ユーティリティ calc_news_window() を実装（JST ベースで前日 15:00 〜 当日 08:30 相当の UTC 範囲）。

- ツール: Paper Trading 検証レポート (src/kabusys/tools/paper_verification_report.py)
  - CLI ツールを提供（python -m kabusys.tools.paper_verification_report）。
  - 指定期間の system_status / trade_logs / risk_logs を集計し、稼働率・注文成功率・送信率・P95 レイテンシ等の指標を算出して PASS/FAIL 判定を出力。
  - P95 算出、日付フィルタの構築、DB 存在チェックと各種 SQL フォールバック（テーブルがない場合に安全に動作）を実装。
  - 簡易的な閾値（稼働率 99%、注文成功率 90% 等）をデフォルト設定。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーを必要とする機能あり（ai/news_nlp.py）。API キーの取り扱いは環境変数 OPENAI_API_KEY または明示的引数で指定する設計。秘密情報の管理に注意してください。

Notes / Known limitations
- run_monitoring は KABUSYS_ENV にかかわらず monitoring 用に settings.sqlite_path（本番想定）を使用する仕様です。環境分離が必要な状況では注意してください。
- process priority / cpu affinity は権限不足や未対応 OS ではログ警告の上でスキップされます（安全設計）。
- PAPER_FILL_MODE や KABUSYS_ENV 等は厳密にバリデートします。不正な値は ValueError を発生させます。
- position_sizing: price が欠損（0.0）の場合、エクスポージャーや株数計算で過少評価される可能性がある旨の TODO コメントあり。将来的にフォールバック価格の導入を検討する必要があります。
- research モジュールは DuckDB 上のテーブル（prices_daily / raw_financials 等）を前提とします。該当テーブルが整備されていない環境では一部機能が動作しません。
- ai/news_nlp の外部 API 呼び出しはネットワークの不安定さやレート制限の影響を受けます。実装は再試行と部分的失敗時のフェイルセーフを備えていますが、運用上の監視は推奨します。

作者注
- 各モジュールに詳細な docstring と設計メモを埋めています。実運用前に設定ファイル（.env）と DB パスの確認、権限（プロセス優先度設定など）を行ってください。