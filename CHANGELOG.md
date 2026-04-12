CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式で記載しています。
https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-04-12
--------------------

Added
- 全体
  - 初回リリース。基本的な自動売買フレームワークのコア機能を追加。
  - パッケージバージョンを 0.1.0 に設定 (src/kabusys/__init__.py)。

- 実行/監視ランナー
  - run_execution: 実行エンジン起動スクリプトを追加。Engine の組み立て、Broker クライアント生成、ExecutionEngine のセッション実行を行う (src/kabusys/run_execution.py)。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite DB を使用して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加 (src/kabusys/run_monitoring.py)。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用する設計。

- 設定周り
  - Settings クラスを追加し、環境変数 / .env ファイルからの設定取得を一元化 (src/kabusys/config.py)。
    - 自動的にプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込む。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 多数のプロパティを提供（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / PID ファイル等）。
    - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。
    - paper_trading 用の PAPER_TRADING_SQLITE_PATH といったオプションを提供。

- .env パーサ
  - 複雑な .env の行を正しく扱うためのパーサを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理など） (src/kabusys/config.py)。

- DB/分析基盤
  - DuckDB を利用した解析接続サポートを追加（各モジュールで duckdb 接続を受け取る設計）。
  - 監視テーブルの存在を保証する init_monitoring_db 呼び出しを実装箇所に追加（起動時に冪等にチェック） (run_execution/run_monitoring)。

- ポートフォリオ構築
  - 銘柄選定と重み計算機能を追加 (src/kabusys/portfolio/portfolio_builder.py)。
    - select_candidates, calc_equal_weights, calc_score_weights を提供。
    - スコアが全て 0 の場合は等金額配分にフォールバックする挙動を明示。
  - セクター集中制限・レジーム乗数を提供 (src/kabusys/portfolio/risk_adjustment.py)。
    - apply_sector_cap（既存保有に基づくセクター除外）、calc_regime_multiplier（bull/neutral/bear マッピング）。
    - unknown セクターの扱い・ログ出力の挙動を明記。
  - 発注株数算出ロジックを追加（単元丸めや投下資金スケール、risk_based / equal / score の割当方式） (src/kabusys/portfolio/position_sizing.py)。
    - aggregate cap（全銘柄合計が利用可能現金を超える場合のスケーリング）や lot_size 単位での端数処理を実装。
    - cost_buffer による手数料・スリッページ見積りを考慮。

- リサーチ機能
  - ファクター計算: モメンタム・ボラティリティ・バリュー等の計算関数を追加 (src/kabusys/research/factor_research.py)。
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB のウィンドウ関数を活用した実装。
  - 特徴量探索: 将来リターン計算、IC（スピアマンランク相関）計算、統計サマリー等を追加 (src/kabusys/research/feature_exploration.py)。
    - calc_forward_returns, calc_ic, factor_summary, rank を実装。
    - 外部依存を持たない純粋 Python 実装（pandas 等に依存しない）。

- AI ニュース NLP
  - raw_news を OpenAI API（gpt-4o-mini）でセンチメント解析し ai_scores に書き込むモジュールを追加 (src/kabusys/ai/news_nlp.py)。
    - 記事集約・最大文字数/件数トリム、銘柄ごとのバッチ送信（最大 20 銘柄）を実装。
    - 429 / ネットワーク断 / 5xx 等に対する指数バックオフでのリトライやレスポンス検証、スコアの ±1.0 クリップなどの堅牢化を実装。
    - OpenAI API キーの取得やエラー時のフェイルセーフ挙動を実装。

- ツール
  - paper_verification_report: Paper Trading 検証用レポート生成スクリプトを追加 (src/kabusys/tools/paper_verification_report.py)。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計・判定（PASS/FAIL）して標準出力に出力。
    - 日付フィルタ (--from/--to)、DB パスの指定 (--db) に対応。
    - P95 算出ユーティリティ、欠損データ時の N/A 表示を実装。

- ユーティリティ
  - process_priority: プロセス優先度設定・CPU affinity 設定ユーティリティを追加 (src/kabusys/utils/process_priority.py)。
    - Windows / POSIX の差異を吸収して set_process_priority, set_cpu_affinity を提供。
    - 権限不足や未サポート環境時はログ警告でフォールバック。

Changed
- ロギング/エラーハンドリング
  - run_* スクリプトや多くの機能で適切なログ出力（info/debug/warning/exception）と安全な例外ハンドリングを整備。
  - run_monitoring のポーリングループで check_once() の例外をキャッチして次のポーリングへ継続する設計に。

Fixed
- 設定読み込みの堅牢化
  - .env の読み込みでファイル読み込み失敗時に警告を出してスキップするように改善（権限エラー等に対処）。
  - .env の override 処理に protected セットを導入し、OS 環境変数の上書きを防止する設計に。
- ポートフォリオ・発注量計算
  - 単元（lot_size）単位での丸め、利用可能現金に対する aggregate scaling、0/負の価格をスキップする防御コードを追加。
- レポート/統計
  - P95 計算で空リストは None を返すようにし、レポート表示を N/A にフォールバックするように修正。
- モニタリング
  - MONITOR_POLL_INTERVAL が不正（非数値や 0 以下）な場合にデフォルト 60 秒にフォールバックする検証処理を追加。

Notes
- セキュリティ/運用
  - OpenAI API キーや各種シークレットは環境変数経由での供給を想定。キー未設定時は明確に ValueError を送出する箇所があるため、運用時に .env 等での設定を確認してください。
- Paper Trading
  - paper_trading モードでは SQLite DB を分離して Paper 専用 DB（data/paper_trading.db など）に記録するため、本番データと完全に独立した検証が可能です。

Unreleased
- なし

Deprecated
- なし

Removed
- なし

Security
- なし

-----