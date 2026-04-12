CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
初回リリースの内容は、ソースコード内の実装・コメントから推測してまとめたものです。

[Unreleased]
-----------

- （なし）

[0.1.0] - 2026-04-12
-------------------

Added
- 基本アプリケーションを初期リリース
  - パッケージバージョンを __version__ = "0.1.0" として公開（src/kabusys/__init__.py）。
- 実行・監視プロセス起動スクリプト
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。実行環境に応じてブローカークライアントを生成し、OrderRepository、OrderManager、RiskManager、Reconciler 等を組み立ててセッションを実行する（src/kabusys/run_execution.py）。
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）（src/kabusys/run_monitoring.py）。
- Paper Trading 用ユーティリティ
  - paper_verification_report: paper trading の SQLite DB を元に運用検証レポートを生成する CLI スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。稼働率、注文成功率、送信率、レイテンシ（P95）などを集計し PASS/FAIL を表示。
- ポートフォリオ構築モジュール（純粋関数群）
  - 銘柄選定と配分: select_candidates, calc_equal_weights, calc_score_weights（src/kabusys/portfolio/portfolio_builder.py）。
  - リスク調整: apply_sector_cap（セクター集中制限）、calc_regime_multiplier（レジーム乗数）（src/kabusys/portfolio/risk_adjustment.py）。
  - 銘柄ごとの発注数算出: calc_position_sizes（risk_based / equal / score の配分方式、単元株丸め、aggregate cap スケーリング等）（src/kabusys/portfolio/position_sizing.py）。
- リサーチ／ファクター計算
  - ファクター計算: calc_momentum、calc_volatility、calc_value（DuckDB を用いた prices_daily / raw_financials 参照）（src/kabusys/research/factor_research.py）。
  - 特徴量探索ユーティリティ: 将来リターン計算(calc_forward_returns)、IC 計算(calc_ic)、ランク変換(rank)、ファクター統計サマリ(factor_summary)（src/kabusys/research/feature_exploration.py）。
- AI ニュース NLP スコアリング
  - OpenAI（gpt-4o-mini）を用いたニュースのセンチメントスコアリング機能を追加（バッチ処理・リトライ・結果バリデーション・スコアクリッピング・DuckDB への一括登録を実装）（src/kabusys/ai/news_nlp.py）。
  - ルックアヘッドバイアス防止のため、内部で datetime.today()/date.today() を直接参照しない設計。
- 汎用ユーティリティ
  - process_priority: クロスプラットフォームでのプロセス優先度設定および CPU affinity 設定ユーティリティを追加（psutil 使用、Windows / POSIX 差分抽象化）（src/kabusys/utils/process_priority.py）。
- 設定管理
  - Settings クラスによる環境変数ラッパーを実装（自動 .env ロード、厳密な値検証/フォールバック、パス展開など）（src/kabusys/config.py）。
  - .env/.env.local の自動読み込み: プロジェクトルート（.git または pyproject.toml）を探索して .env を読み込み。OS 環境変数を保護しつつ .env.local で上書き可能。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- DB / 分析基盤
  - DuckDB を組み込み、リサーチ・AI モジュールでの高速集計に利用（複数箇所で duckdb.connect を使用）。
- 監視 DB 初期化
  - init_monitoring_db による監視テーブルの冪等な初期化を run_execution/run_monitoring 起動時に実行。

Changed
- 実行時のプロセス優先度を起動直後に "high" へ設定するようにし、重要プロセスの実行安定性を向上（run_execution, run_monitoring）。
- run_execution:
  - paper_trading 環境では MockBrokerClient を使用し、data/paper_trading.db に記録することで本番 DB と完全分離する動作を導入。
- run_monitoring:
  - 監視処理は KABUSYS_ENV にかかわらず本番の sqlite_path を参照する仕様（設計上の注記）。
- paper_verification_report:
  - レポートの判定基準（稼働率、成功率、送信率、P95 レイテンシなど）と出力フォーマットを整備。
- portfolio、position_sizing:
  - lot_size 単位での丸め、aggregate cap によるスケーリングと残余配分（端数処理）を実装して発注株数算出の安定化を図った。
- config:
  - .env パーサを強化（export 形式、クォート内エスケープ、インラインコメント処理、上書き制御などに対応）。
  - PAPER_FILL_MODE 等の設定値に対する入力検証を追加（有効値チェックで誤設定を早期検出）。

Fixed
- 環境変数の不正値に対するフォールバック挙動を明確化
  - MONITOR_POLL_INTERVAL が不正値（0 以下や非数）の場合はログに警告を出しデフォルト 60 秒にフォールバック（run_monitoring）。
- position_sizing:
  - 価格欠損・ゼロ価格の銘柄をスキップすることでゼロ除算や不正な株数計算を回避。
- process_priority / set_cpu_affinity:
  - psutil による権限エラーや未対応プラットフォームでの挙動をキャッチして安全にスキップするようにした（警告ログ出力）。
- research モジュール:
  - データ不足時の None ハンドリング（ウィンドウに必要行数が足りない場合に None を返す）を統一的に実装。
- ai/news_nlp:
  - API 呼び出しに対して 429 / ネットワーク / タイムアウト / 5xx を想定した指数バックオフのリトライ戦略を実装（堅牢化）。
  - OpenAI レスポンスのバリデーション・スコアクリップを導入し不正応答を保護。

Security
- ai/news_nlp:
  - ルックアヘッドバイアス防止のため、スコア算出ロジックで外部的に与えられた target_date を使用し、内部で現在日時を盲目的に参照しない設計を採用。
- config:
  - OS 環境変数を保護するため .env 自動ロードで既存の OS 環境変数を上書きしないデフォルト挙動を採用。必要に応じて .env.local で上書き可能。

Notes / Known behaviors
- run_monitoring は意図的に「監視用 DB は環境にかかわらず本番 sqlite_path を使用する」仕様になっているため、開発環境での利用時は sqlite_path の設定に注意が必要。
- paper_trading モードでは DB が分離される（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）ため、本番データへの影響は回避される設計。
- 一部の DuckDB 操作（executemany 等）はバージョンによる制約があるため、空パラメータなどに対する安全チェックを実装している。
- OpenAI の呼び出し部分は API キー（OPENAI_API_KEY）を必要とする。未設定時は明示的なエラーを発生させる。

---

この CHANGELOG はソースコード内の実装とコメントから推測して作成しています。リリースノートとして公開する際は、実際のリリース日・差分・影響範囲をプロジェクトの変更履歴管理（Git のコミットログ等）と照合のうえ調整してください。