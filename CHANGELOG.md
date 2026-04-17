CHANGELOG
=========

すべての重要な変更を記録します。このファイルは Keep a Changelog の書式に準拠しています。  

現在の日付: 2026-04-17

Unreleased
----------

（なし）

[0.1.0] - 2026-04-17
-------------------

Added
- 全体
  - 初期リリース。日本株自動売買システム "KabuSys" のコア機能群を実装。

- パッケージメタ情報
  - パッケージ初期バージョンを設定: __version__ = "0.1.0"。

- 設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env ファイルのパース処理を強化（export プレフィックス、シングル/ダブルクォート、インラインコメントの扱い、エスケープ処理対応）。
  - 環境変数の取得ラッパー Settings を提供。DBパス、Paper Trading設定、監視閾値、ログレベル、実行環境判定（development/paper_trading/live）などをプロパティとして公開。
  - 必須環境変数未設定時に明確なエラーを投げる _require 実装。

- 実行 / 監視スクリプト
  - run_execution.py
    - ExecutionEngine 起動エントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（data/paper_trading.db デフォルト）を使用し、本番 DB と完全分離。
    - BrokerClientFactory 経由でブローカークライアントを作成し、OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine をデーモンスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止処理を実装。
    - 実行 PID ファイル path をサポート（data/execution.pid デフォルト）。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動エントリポイントを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視データは一元管理）。
    - 停止フラグ検知でループ終了、KeyboardInterrupt での正常終了処理を実装。

- モジュール: portfolio
  - portfolio_builder
    - select_candidates: BUYシグナルをスコア降順＋タイブレークでソートして上位 N を選出。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装。スコア合計が 0 の場合は等金額にフォールバックして警告。
  - risk_adjustment
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算し、上限比率を超えるセクターの新規候補を除外するロジックを実装（unknown セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた投下資金乗数を返す。
  - position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score） に基づき銘柄ごとの発注株数を算出。単元株丸め、1銘柄上限、aggregate cap（利用可能現金に応じたスケールダウン）、cost_buffer を考慮した慎重なスケーリングを実装。

- モジュール: research
  - factor_research
    - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily/raw_financials を参照して、モメンタム・ボラティリティ・バリュー系ファクターを計算する関数を実装（SQL ベースで高効率に計算）。
    - 各関数はデータ不足時に None を返すなど堅牢に実装。
  - feature_exploration
    - calc_forward_returns: 指定日から複数ホライズン先の将来リターンを一括計算。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。
    - factor_summary: 列ごとの count/mean/std/min/max/median を標準ライブラリで計算（pandas 非依存）。
    - rank: 同順位は平均ランクで処理するランク化ユーティリティ。

- モジュール: research パッケージ公開
  - z-score 正規化ユーティリティ (kabusys.data.stats.zscore_normalize) を re-export。
  - 上記の factor 関数・解析ユーティリティを __all__ で公開。

- ユーティリティ (kabusys.utils)
  - process_priority
    - set_process_priority(level): Windows / POSIX(Linux, Darwin, FreeBSD) を吸収してプロセス優先度を設定。権限不足や未サポート環境では警告してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数にプロセスをピンニングする機能。引数検証あり。権限不足時は警告してスキップ。

- モジュール: monitoring
  - monitoring_db:init_monitoring_db の呼び出しにより監視用テーブルの整備を行う（冪等）。

- ツール (kabusys.tools)
  - paper_verification_report.py
    - Paper Trading 用の検証レポート生成 CLI を追加。PAPER_TRADING_SQLITE_PATH（または --db）で指定した SQLite DB を読み、システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）などを算出し、PASS/FAIL 判定を出力。
    - P95 の計算、日付フィルタ指定（--from / --to）をサポート。
    - DB が存在しない場合のエラーメッセージを実装。

- AI ニュース NLP (kabusys.ai.news_nlp)
  - raw_news から銘柄ごとに記事を集約し、OpenAI API (gpt-4o-mini) を用いて銘柄別センチメント（-1.0〜1.0）を算出するスコアリング機能を追加。
  - バッチ単位・トークン肥大化対策（記事数・文字数制限）、429/5xx/タイムアウト等に対する指数バックオフでのリトライ処理、レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗に対する既存データ保護（削除→挿入の限定）等を設計・実装。
  - calc_news_window: JST→UTC のニュース収集ウィンドウを厳密に計算するユーティリティ。

Changed
- （初回リリースのため該当なし）

Fixed
- 設定/実行の堅牢化:
  - MONITOR_POLL_INTERVAL が不正（0 以下、非数）の場合は警告してデフォルト 60 秒にフォールバック。
  - PAPER_FILL_MODE の値検証を実装し、無効値は ValueError を投げる（明示的エラー）。
  - process_priority は未サポート OS や権限不足時に例外を投げずログ警告でスキップするよう堅牢化。

Security
- （該当なし）

Removed
- （該当なし）

Deprecated
- （該当なし）

注記 / 既知の制限
- position_sizing.calc_position_sizes
  - 将来的に銘柄ごとの単元サイズ（lot_size）を stocks マスタで持たせる予定（現在は全銘柄共通 lot_size 引数）。
- risk_adjustment.apply_sector_cap
  - price_map に欠損 (0.0) がある場合、エクスポージャーが過少見積りされてしまう可能性がある旨を TODO コメントで指摘。将来的に前日終値等のフォールバックを検討予定。
- ai.news_nlp
  - OpenAI API キーが必須（api_key 引数または環境変数 OPENAI_API_KEY）。
  - 大量のニュースや API エラー発生時は部分的にスコア未更新のケースがある（設計上、失敗しても処理継続してフェイルセーフにする）。
- research / feature_exploration
  - 外部ライブラリ（pandas 等）に依存しない実装のため、非常に大規模なデータセットではパフォーマンス上のチューニングが必要になる可能性あり（現状は DuckDB + 標準ライブラリで実装）。
- run_monitoring / run_execution
  - 停止フラグは file-system ベース（data/stop_requested.flag）。運用時のフラグ管理に注意。

今後の予定（予定項目の抜粋）
- 銘柄ごとの lot_size 管理（stocks マスタの導入）
- apply_sector_cap の価格フォールバック実装
- AI モジュールの追加検証・エラーハンドリング強化
- ドキュメント（User Guide / Deployment / Config）整備

ライセンス
- 本リポジトリのライセンス情報は別途 LICENSE ファイルを参照してください。