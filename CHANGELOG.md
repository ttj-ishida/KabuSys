CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠します。
このファイルでは主要な追加・変更点・修正点を日本語で記載しています。

フォーマット:
- Added: 新機能
- Changed: 既存の振る舞いの変更（互換性に注意）
- Fixed: バグ修正や堅牢性向上
- Removed: 削除された機能

Unreleased
----------
（現在の作業中の変更はここに記載します）

0.1.0 - 2026-04-13
-----------------

Added
- 基本機能の初期実装を追加（パッケージ初期リリース）。
  - パッケージバージョンを __version__ = "0.1.0" として公開。
  - エントリポイントスクリプト:
    - run_execution.py: ExecutionEngine を起動するスクリプトを追加。プロセス優先度設定、SQLite / DuckDB 接続、Broker クライアントの生成、ExecutionEngine のセッション実行を行う。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
  - ツール:
    - tools.paper_verification_report: Paper Trading 用の検証レポート生成コマンドラインツールを追加。稼働率・注文成功率・送信率・レイテンシ等を集計して PASS/FAIL 判定を出力可能。--from/--to/--db オプションをサポート。
  - ポートフォリオ構築モジュール:
    - portfolio.portfolio_builder: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - portfolio.position_sizing: 各種配分アルゴリズム（risk_based / equal / score）、lot サイズ丸め、aggregate cap によるスケーリングを実装。
    - portfolio.risk_adjustment: セクター上限適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）を実装。
    - portfolio パッケージエクスポートを整備（__all__）。
  - リサーチ / ファクター計算:
    - research.factor_research: Momentum / Volatility / Value ファクター計算（DuckDB を用いた SQL 実行）を実装。
    - research.feature_exploration: 将来リターン計算、IC（Spearman ランク相関）計算、ファクター統計サマリー、ランク付けユーティリティを実装。外部ライブラリに依存せず純粋 Python + DuckDB で動作。
    - research パッケージのエクスポートを整備（zscore_normalize を含む）。
  - AI ニュース NLP:
    - ai.news_nlp: raw_news / news_symbols を集約して OpenAI API（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores に書き込む処理基盤を実装。タイムウィンドウ計算、チャンク処理、スコアクリップ、リトライポリシーの考慮、レスポンス検証、DuckDB への書き込み方針（部分成功時の保護）などを含む。
  - 設定 / 環境変数管理:
    - config.Settings: 各種環境変数のラッパー。デフォルト値、パス展開、型変換、バリデーションを備える（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の検証）。
    - .env 自動読み込み機能を実装: プロジェクトルート（.git または pyproject.toml）を基準に .env と .env.local を読み込み（OS 環境変数を保護して上書き制御）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - 環境変数パーサーは export KEY=val 形式、クォート/エスケープ、インラインコメントの扱いをサポート。
  - ユーティリティ:
    - utils.process_priority: プラットフォーム差分を吸収してプロセス優先度（high/normal/low）と CPU affinity 設定を行うユーティリティを追加。Windows / POSIX（Linux / Darwin / FreeBSD）をサポートし、アクセス権限不足などのエラーは警告ログとして処理して失敗しないフォールトトレラントな実装。
  - 監視 DB 初期化ユーティリティ（monitoring.monitoring_db）や SystemMonitor などの監視基盤（run_monitoring から利用）を用意。

Changed
- データベースの分離ポリシーを明確化:
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では paper 用 SQLite DB（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離する設計にした。Execution 起動時に settings.is_paper に応じて接続先を切り替える。
  - 監視機能は環境にかかわらず本番 sqlite_path を使用する（監視系は本番データに対して常に稼働状況を記録する意図）。
- run_monitoring のポーリング間隔制御:
  - MONITOR_POLL_INTERVAL 環境変数を追加でサポート。0 以下や整数変換失敗などの不正値は警告を出しデフォルト（60 秒）にフォールバックする。
- config の .env 読み込み順序と上書きルール:
  - 読み込み順序は OS 環境 > .env.local > .env。OS 環境変数は protected として自動ロードで上書きされない。
- research / factor モジュールは DuckDB を受け取り SQL 実行でデータ取得を行う設計で、外部 API への依存を避けるよう変更（初期実装方針）。

Fixed
- 環境変数パーサーの堅牢性向上:
  - クォート文字列内のバックスラッシュエスケープ、インラインコメントの扱い、export 形式のサポート等を実装し、複雑な .env 行を正しく解釈するようにした。
  - _load_env_file においてファイル読み込み失敗時は警告を発し続行するようにしてプロセスの起動失敗を避ける。
- process_priority のエラー処理強化:
  - psutil による優先度 / affinity 設定が権限不足や未対応 OS で失敗した場合、例外を投げず警告ログに変換して処理を継続するようにした。
- position_sizing のスケーリングと端数処理の堅牢化:
  - aggregate cap 超過時のスケールダウン処理で lot_size 単位での丸めと残余キャッシュに基づく追加配分を実装し、再現性のためソートの安定化（二次キーにコード）を行った。
- research.feature_exploration の入力検証:
  - calc_forward_returns の horizons 引数に対して不正（非正の整数や 252 超）を検出して ValueError を返すようにした。

Documentation
- 各モジュールに詳細な docstring を追加:
  - 設計思想、引数説明、戻り値、注意点（例: レジーム乗数の取り扱い、ニュース処理のタイムウィンドウ、DuckDB の参照テーブルなど）を明記。
- tools.paper_verification_report にレポートの閾値、出力フォーマット、コマンドライン引数の説明を追加。

Security & Safety
- OpenAI API キーの取り扱い:
  - ai.news_nlp.score_news は api_key 引数または環境変数 OPENAI_API_KEY を要求し、未設定時は ValueError を送出して誤用を防止。
- デフォルトのファイルパスは data/ 以下に集約（duckdb: data/kabusys.duckdb, sqlite: data/monitoring.db, paper_trading: data/paper_trading.db）。Path.expanduser を使い ~ パスも解決。

Notes / Known limitations
- news_nlp モジュールは API 呼び出しのリトライやレスポンス検証を考慮しているが、外部 API のクォータやモデル出力フォーマット変化には運用側での監視が必要。
- 一部 TODO コメント（例: position_sizing の銘柄別 lot_size 対応、apply_sector_cap の価格欠損時のフォールバック）を残している。将来的な改善対象。
- DuckDB への executemany 等、バージョン依存の制約を回避するための注意点がコード内に記載されている（実行環境の DuckDB バージョンに注意）。

Acknowledgements
- 初期実装により、PortfolioConstruction.md / StrategyModel.md / Execution 設計に基づいた主要なコンポーネントを揃えました。今後はテストカバレッジ、運用用ドキュメント、監視アラートの追加などを予定しています。