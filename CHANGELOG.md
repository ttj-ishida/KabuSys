CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

注: 以下は現在のコードベースの内容から推測して作成した変更履歴です。実際のコミット履歴ではありません。

Unreleased
----------

- なし。

0.1.0 - 2026-04-16
------------------

Added
- パッケージ初期リリース: kabusys の基本機能を追加。
  - コア実行スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV が paper_trading の場合は専用の paper_trading DB を使用し、MockBrokerClient を想定した分離動作を提供。
    - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ(data/stop_requested.flag)で安全終了。
  - 設定管理
    - config.py: .env 自動読み込みロジック（.env, .env.local）、プロジェクトルート検出、環境変数ラッパ（Settings クラス）を実装。各種パス・閾値・モード（paper_trading / live / development）をプロパティで提供。
  - モニタリング DB 初期化
    - monitoring_db の初期化呼び出しを行う処理を run_monitoring/run_execution に追加（冪等にテーブルを保証）。
  - Execution コンポーネント群（実行系）
    - ExecutionEngine、BrokerClientFactory、OrderManager、OrderRepository、Reconciler、RiskManager 等の組み立て呼び出し（run_execution から使用）。RiskManager 初期設定値（max_position_pct 等）をデフォルトで提供。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder: 候補選定(select_candidates)、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights) を追加。
    - portfolio.position_sizing: position sizing（リスクベース / equal / score）ロジックを実装。lot_size、cost_buffer、aggregate cap スケーリング、端数処理の再配分ロジックを含む。
    - portfolio.risk_adjustment: セクター上限適用(apply_sector_cap)、レジーム乗数(calc_regime_multiplier) を実装。
  - リサーチ / ファクター計算
    - research.factor_research: モメンタム / ボラティリティ / バリュー系ファクター（calc_momentum, calc_volatility, calc_value）を DuckDB を用いて実装。
    - research.feature_exploration: 将来リターン計算(calc_forward_returns)、IC 計算(calc_ic)、統計サマリー(factor_summary)、ランク変換(rank) を実装。外部依存は使用せず純粋に標準ライブラリと DuckDB で動作。
  - AI ニュース NLP
    - ai.news_nlp: raw_news を OpenAI API（gpt-4o-mini）でスコアリングし ai_scores に書き込む処理を追加。バッチ処理、最大文字数制限、スコアクリッピング、JSON 検証、部分更新戦略を備える。
  - ツール
    - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを算出し PASS/FAIL 判定を出力。コマンドライン引数 (--from, --to, --db) に対応。
  - ユーティリティ
    - utils.process_priority: クロスプラットフォームでプロセス優先度と CPU affinity を設定するヘルパーを実装（set_process_priority, set_cpu_affinity）。権限不足等は警告ログでフォールバックする。
  - パッケージメタ
    - __init__.py に __version__ = "0.1.0" を追加し、主要 API を __all__ でエクスポート。

Changed
- .env ロード方針の導入
  - OS 環境変数を保護しつつ .env/.env.local を自動読み込みするロジックを追加（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションあり）。.env.local は優先的に上書きする。
- run_monitoring の DB 動作
  - 監視処理は KABUSYS_ENV に関わらず本番 sqlite_path を使用する（設計上の明示）。run_execution は paper_trading 環境時に専用 DB を利用。
- 実行時のプロセス優先度設定
  - run_execution/run_monitoring 起動時に set_process_priority("high") を最初に呼ぶことで優先度を上げる動作を追加（失敗時はログに警告を残して継続）。

Fixed
- .env パーサの堅牢化
  - config._parse_env_line() を改良し、シングル／ダブルクォート内のエスケープ処理、インラインコメントの扱い、export プレフィックス対応などを実装。無効行や不正な行は無視するように改善。
- DB 初期化の冪等性確保
  - init_monitoring_db() を呼び出すことで監視用テーブルが存在しない場合でも安全に初期化されるように（複数回呼んでも問題ない）。
- Paper 検証レポートの堅牢化
  - データ不足時（テーブルが存在しない等）に sqlite3.OperationalError をキャッチして N/A 表示や default 値でフォールバックするようにした。

Security
- ai.news_nlp で OpenAI API キーの必須チェックを追加。引数 api_key もしくは環境変数 OPENAI_API_KEY が未設定の場合は ValueError を送出し、誤った無認証呼び出しを防止。
- process priority / cpu affinity の設定で権限不足が生じた場合は例外を握り潰さず警告ログに記録するようにして、安全にフォールバック。

Notes / Implementation details
- run_monitoring では停止ファイル(data/stop_requested.flag)を検知するとループを抜けて安全に終了します。ポーリング間隔は MONITOR_POLL_INTERVAL（秒）で指定可能。無効値はデフォルト 60 秒にフォールバックします。
- run_execution は停止フラグ検知時に Engine.stop() を呼び出してセッションを停止する設計です。実行中の PID を data/execution.pid に書き込む想定（pid_file 引数経由）。
- position_sizing の aggregate cap スケールダウン時に lot_size 単位での再配分ロジックを持ち、残余キャッシュで端数を埋める実装があります。
- research モジュールは DuckDB の時間窓やウィンドウ関数を活用し、営業日ベースのラグ（LEAD/LAG）を用いてファクターを算出します。データ不足時は None を返すことで上位ロジックでの除外やフォールバックを簡単にしています。
- ai.news_nlp は結果を部分置換（削除→挿入を対象コードに限定）することで、部分失敗時に既存データを保護する設計です。また API 呼び出しは最大リトライ回数と指数バックオフを持ち、429/5xx/ネットワーク断等を考慮しています。
- config.Settings は各種閾値（CPU/MEM/DISK）や pid/kill フラグパスをプロパティで提供しており、実行時に容易に参照できます。

Removed
- なし。

Deprecated
- なし。

Security
- 既知の潜在的問題:
  - news_nlp の JSON 検証は厳密だが、API 側の出力が期待通りでない場合（モデルが厳密な JSON を返さない等）スコア取得が失敗する可能性がある。失敗時はフォールバック/スキップする実装になっているが、運用時は監視とアラート設定を推奨。

今後の予定（提案）
- 単体テストと CI の追加（特に position sizing、risk logic、ai.news_nlp の入出力検証）。
- run_execution/run_monitoring の systemd / supervisor 用ユニットや Docker イメージ化による運用向上。
- portfolio の lot_size を銘柄毎に持たせる（stocks マスタの拡張）。
- ai.news_nlp の出力検証・スキーマ検証を強化し、フォールバックの改善（ロールアップ要約→再送等）。

--- 

（この CHANGELOG はコード内のドキュメント文字列・関数名・ログメッセージ・コメント等から推測して作成しています。実際の変更履歴を作成する際はコミット履歴を参照してください。）