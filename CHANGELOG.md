Keep a Changelog 準拠の CHANGELOG.md（日本語）
※コードベースから推測して作成しています。実際の変更履歴と差異がある場合があります。

All notable changes
===================

[0.1.0] - 2026-04-16
--------------------

Added
- パッケージ全体
  - 初期リリース相当の機能群を追加。パッケージバージョンは src/kabusys/__init__.py にて 0.1.0 を設定。
- 起動スクリプト
  - run_monitoring.py を追加。SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト data/stop_requested.flag ファイルの存在で検知。
    - 監視は実運用用の sqlite_path を使用（KABUSYS_ENV に依存せず本番 DB を参照）。
    - 起動時にプロセス優先度を High に設定（utils/process_priority.set_process_priority を利用）。
  - run_execution.py を追加。ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite DB（settings.paper_sqlite_path）を使用し、本番 DB から完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組み立てと起動を実装。
    - 停止フラグ検知によるエンジン停止、PID ファイル（data/execution.pid）対応。
- 設定管理
  - config.py を追加。
    - .env 自動読み込み機能（プロジェクトルートの .env と .env.local）を実装。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env ファイルのパース改善: export プレフィックス対応、クォートされた値（エスケープ対応）の解析、インラインコメントの扱い、無効行のスキップ等を実装。
    - Settings クラスを導入し、環境変数をプロパティ経由で取得（必須キー検査、デフォルト値、バリデーション含む）。
    - 各種設定追加: J-Quants / kabu API / LINE / DuckDB/SQLite パス / Paper Trading 関連設定 / 監視閾値 / PID/kill フラグパス / KABUSYS_ENV / LOG_LEVEL 等。
    - PAPER_FILL_MODE の有効値検査（instant/partial/never/reject）や KABUSYS_ENV のバリデーションを実装。
- モニタリング関連
  - monitoring_db の初期化呼び出しを run_monitoring と run_execution の起動フローに追加（監視テーブルの存在を保証し冪等に初期化）。
- ツール
  - tools/paper_verification_report.py を追加。Paper Trading の検証レポート出力ツールを CLI で提供。
    - system_status / trade_logs / risk_logs を集計して稼働率・注文成功率・送信率・レイテンシ（P95 など）を算出。
    - パス/フェイル基準を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）し、PASS/FAIL 判定を出力。
    - --from / --to / --db オプション対応。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全0時のフォールバックと警告あり。
  - portfolio/risk_adjustment.py: セクター集中制限適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）を実装。unknown セクターの扱いや警告ログあり。
  - portfolio/position_sizing.py: 銘柄毎の発注株数算出（risk_based / equal / score）を実装。単元株（lot_size）丸め、per-position/aggregate cap、cost_buffer を考慮したスケーリング、残差処理ロジックあり。
  - portfolio/__init__.py で上記関数を公開。
- ユーティリティ
  - utils/process_priority.py を追加。Windows / POSIX の差分を吸収してプロセス優先度（set_process_priority）・CPU affinity（set_cpu_affinity）を設定するユーティリティを提供。権限不足や未対応 OS 時は警告ログでスキップ。
- リサーチ（DuckDB ベース）
  - research/factor_research.py を追加。Momentum/Volatility/Value ファクターを DuckDB SQL とウィンドウ関数で計算する関数（calc_momentum, calc_volatility, calc_value）を実装。営業日ベースのホライズン・window 範囲の定義等を含む。
  - research/feature_exploration.py を追加。将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク化ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。外部ライブラリに依存せず純 Python 実装。
  - research/__init__.py で主要関数群を公開（zscore_normalize は kabusys.data.stats から供給）。
- AI / ニュース NLP
  - ai/news_nlp.py を追加。raw_news を OpenAI（gpt-4o-mini）でセンチメント解析して ai_scores に書き込むロジックの骨子を実装。
    - ニュース収集ウィンドウ計算（calc_news_window）、バッチサイズやトークン対策、リトライ（429 / ネットワーク / 5xx に対する指数バックオフ）、レスポンス検証、スコア ±1.0 クリップ、部分失敗に備えたテーブル更新戦略（該当コードに限定した DELETE→INSERT）などを設計で盛り込む。
    - OpenAI API キーの解決と未設定時の ValueError 発生。
    - 注: ファイル末尾は切れており、処理の全体実装はコード末尾で中断（以降の実装が存在する可能性あり）。
- DB（DuckDB / SQLite）接続
  - 各種モジュールが DuckDB 接続（DuckDBPyConnection）を受け取り SQL を実行する設計。また、sqlite3 を用いた軽量ローカル DB と併用。

Changed
- コード設計
  - 各種処理は「DB 参照なしの純粋関数」「DuckDB SQL を用いる分析関数」「実行/監視のプロセス制御スクリプト」に役割分離され、テスト容易性と境界を意識した設計に整備。
  - .env の自動読み込みをプロジェクトルートベースに変更し、CWD に依存しないよう改善。
  - run_monitoring は実行環境にかかわらず本番 sqlite_path を使用する方針に明示的に変更（監視データを本番 DB に集約する意図）。
  - run_execution は paper_trading 環境時に専用 DB を使用する（本番 DB と完全分離）設計を明確化。
- ロギング/エラー処理
  - 不正な環境変数や値（MONITOR_POLL_INTERVAL の負値/非整数、PAPER_FILL_MODE・KABUSYS_ENV・LOG_LEVEL の無効値等）に対して明示的な警告・例外を追加。
  - set_process_priority / set_cpu_affinity は権限不足や未対応 API 呼び出しを警告ログでスキップする堅牢化を実施。

Fixed
- .env パーサー
  - export プレフィックスやクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどの処理漏れを補正。
- ポートフォリオ計算
  - スコア合計が 0 の場合に等金額配分へフォールバックしてゼロ除算等を回避（警告ログあり）。
  - position_sizing の aggregate cap スケール処理で小数端数や単元株丸めを明示的に扱う処理を実装。

Known issues / Notes
- ai/news_nlp.py の末尾でコードが中断しており、_fetch_articles 以降の実装が切れている（コードベースにより処理の続きが存在する可能性あり）。実運用前に該当処理の完了確認が必要。
- position_sizing.apply_sector_cap の価格欠損時（price == 0.0）にエクスポージャーが過少評価され、誤った除外判定を招く可能性がある旨の TODO コメントあり（将来的にフォールバック価格導入を検討）。
- DuckDB 側での executemany に関する制約（コメントで言及）に注意。ai モジュールで params が空の場合の処理回避を意図した注記がある。
- 一部の設計選択（監視は本番 DB の使用等）は運用方針に依存するため、複数環境を運用する場合は再確認推奨。

Security
- 環境変数に機密情報（API キー等）を直接期待しており、Settings._require によって未設定時は失敗させる設計。デプロイ時は .env や環境変数の取り扱いに注意すること。

その他
- ドキュメント参照: 各モジュールの docstring に設計方針・参照ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）が記載されているため、実装詳細やアルゴリズム仕様はそちらを参照可。

(以降のリリースでは ai/news_nlp の未完成部分の完成化、テスト追加、各モジュールの単体テスト充実、監視/実行の運用オプション拡張などが想定されます。)