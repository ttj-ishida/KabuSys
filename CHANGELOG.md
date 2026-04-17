CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
合意済みの互換性ポリシーは Semantic Versioning に準じます。

[Unreleased]
-----------

- 進行中 / 注意点
  - ai/news_nlp.py が途中で切れており（ファイル末尾が不完全）、ニュース集約・API呼び出し部分の実装が完了していません。OpenAI API 呼び出しと記事集約の最終処理は未完成のため、本番運用前に実装とテストが必要です。
  - portfolio.position_sizing の将来的な拡張点として、銘柄ごとの lot_size を持たせる案がコメントに残されています（TODO）。設計変更があれば破壊的変更の可能性あり。

0.1.0 — 2026-04-17
------------------

Added
- 基本ランチパッケージとバージョン
  - パッケージ初期バージョンを追加: kabusys.__version__ = "0.1.0"（src/kabusys/__init__.py）。
- 実行/監視用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。paper_trading 環境では MockBrokerClient を使用し、paper_trading 用 SQLite に完全分離して記録する仕組みを備える。停止フラグ／PID 管理、スレッド管理を含む（src/kabusys/run_execution.py）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能。プロセス優先度設定、監視 DB 初期化を行う（src/kabusys/run_monitoring.py）。
- 設定・環境変数管理
  - Settings クラスを追加し、各種環境変数を型付きプロパティで提供（src/kabusys/config.py）。
  - .env 自動読み込み機能を実装（プロジェクトルート検出ロジック付き）。読み込み順序: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーは export プレフィックス、クォート文字列、インラインコメントを考慮した堅牢な実装を提供。
  - PAPER_TRADING_SQLITE_PATH / PAPER_FILL_MODE 等、paper_trading 関連設定を追加。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: シグナル選択（select_candidates）、等金額・スコア加重の重み計算（calc_equal_weights, calc_score_weights）を実装（src/kabusys/portfolio/portfolio_builder.py）。
  - portfolio.position_sizing: position size（株数）計算ロジックを実装。risk_based / equal / score の allocation 方法、単元株丸め、aggregate cap によるスケーリング、cost_buffer を考慮した投下金額調整を提供（src/kabusys/portfolio/position_sizing.py）。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）および市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装（src/kabusys/portfolio/risk_adjustment.py）。
  - portfolio パッケージの __all__ を整備して主要関数をエクスポート（src/kabusys/portfolio/__init__.py）。
- リサーチ／ファクター計算
  - research.factor_research:
    - モメンタム（calc_momentum）、ボラティリティ/流動性（calc_volatility）、バリュー（calc_value）ファクター計算を DuckDB を用いて実装。過不足時は None を返す堅牢な設計（src/kabusys/research/factor_research.py）。
  - research.feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリ（factor_summary）を実装。外部依存を持たずに標準ライブラリで完結（src/kabusys/research/feature_exploration.py）。
  - research パッケージのエクスポートを整備（src/kabusys/research/__init__.py）。
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成立率、送信率、レイテンシ（P95）を集計し PASS/FAIL 判定を出力。コマンドライン引数で期間や DB パスを指定可能（src/kabusys/tools/paper_verification_report.py）。
- 監視 DB 初期化ユーティリティ使用
  - run_* スクリプトおよび execution 起動時に monitoring_db.init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）（src/kabusys/run_monitoring.py, src/kabusys/run_execution.py）。
- プロセス制御ユーティリティ
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定ユーティリティを実装。権限不足や未対応 OS を考慮してワーニングでフォールバック（src/kabusys/utils/process_priority.py）。

Changed
- 環境に依存しない DB 接続挙動
  - 監視プロセスは KABUSYS_ENV に関わらず本番 sqlite_path を使用する仕様に変更（run_monitoring）。
  - 実行エンジンは paper_trading 環境時に paper_sqlite_path を使用するように分離（run_execution）。

Fixed
- 環境変数パーシングの堅牢化
  - .env パーサーでクォート内のバックスラッシュエスケープ、export プレフィックス、インラインコメントの扱いを正しく処理するように修正（src/kabusys/config.py）。
- モニタリング間隔の検証
  - MONITOR_POLL_INTERVAL が不正（非整数、0 以下など）の場合にデフォルトへフォールバックするロジックを追加し、ログ警告を出すようにした（src/kabusys/run_monitoring.py）。
- レポート/集計の耐障害性
  - paper_verification_report はテーブルが存在しない場合の sqlite3.OperationalError を捕捉してデフォルト値にフォールバックするようにしている（src/kabusys/tools/paper_verification_report.py）。
- ファクター／統計関数の数値安定化
  - rank 関数は丸め（round(..., 12)）を行い ties の扱いを安定化。calc_ic は有効レコードが不足する場合に None を返す等、数値的に頑健化（src/kabusys/research/feature_exploration.py）。

Notes / Known issues
- ai/news_nlp.py は OpenAI ベースのニュース NLP スコアリングを実装中で、設計メモと多くの堅牢化（バッチ処理、リトライ、レスポンス検証等）が書かれているものの、ファイル末尾が不完全で実行できない状態です。APIキーの注入、JSON Mode のパース、DuckDB への書き戻しロジックも含まれる予定です（src/kabusys/ai/news_nlp.py）。
- position_sizing の価格欠損時のエクスポージャー見積りに関する TODO（フォールバック価格の検討）など、将来の改善点がコメントに残されています。
- 一部の機能（ExecutionEngine、SystemMonitor、BrokerFactory 等）は本 CHANGELOG で言及したスクリプトから呼び出されていますが、実際の内部実装（発注処理やブローカーの詳細）はこの差分には含まれません。実運用前に統合テストを推奨します。

参考
- 主要ファイル:
  - src/kabusys/config.py
  - src/kabusys/run_execution.py
  - src/kabusys/run_monitoring.py
  - src/kabusys/portfolio/*
  - src/kabusys/research/*
  - src/kabusys/tools/paper_verification_report.py
  - src/kabusys/utils/process_priority.py
  - src/kabusys/ai/news_nlp.py (未完成)

--- 
（以降のリリースでは、ai/news_nlp の完了、テスト追加、及び実行エンジン/モニタリングの統合テスト結果に基づくバグフィックス等を追記予定）