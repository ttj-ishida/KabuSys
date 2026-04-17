CHANGELOG
=========
すべての目立った変更を記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  

バージョン付け方針: メジャー/マイナー/パッチ。  
初回リリースとして 0.1.0 を記載しています（パッケージ内の __version__ に合わせています）。

Unreleased
----------
（現在なし）

0.1.0 - YYYY-MM-DD
------------------
注: 日付は適宜置き換えてください。以下はコードベースから推測した初期リリースの主要変更点です。

Added
- 基本 CLI / 実行エントリ
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル (data/stop_requested.flag) を監視して安全にループを終了。
    - Monitoring は環境に関わらず本番 sqlite_path を使用する設計。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用して本番 DB と隔離。
    - 停止フラグ・PID 管理をサポートし、エンジンをバックグラウンドスレッドで実行。
- 環境設定管理
  - config.Settings クラスを追加。環境変数（.env/.env.local の自動ロードを含む）から設定を取得。
  - .env ローダーは export プレフィックス、クォート、行内コメントなどに対応し、OS 環境変数を保護する override ロジックを実装。
  - 各種設定プロパティを提供（DB パス、paper_trading 用パス、PID/kill flag パス、閾値、PAPER_FILL_MODE 検証等）。
- モジュール: ポートフォリオ構築関連
  - portfolio.portfolio_builder: 銘柄選定 (select_candidates)、等配分/スコア重み (calc_equal_weights / calc_score_weights) を追加。score が全て 0 の場合は等配分へフォールバック。
  - portfolio.risk_adjustment: セクター集中制限適用 (apply_sector_cap)、市場レジーム乗数 (calc_regime_multiplier) を追加。未知レジームは警告を出してフォールバック。
  - portfolio.position_sizing: ポジションサイズ計算 (calc_position_sizes) を追加。allocation_method に応じた株数算出（risk_based / equal / score）、単元株丸め、aggregate cap によるスケーリング、コストバッファ考慮を実装。
- 研究 / リサーチ
  - research.factor_research: モメンタム・ボラティリティ・バリュー（PER/ROE）ファクター計算を実装。DuckDB の prices_daily / raw_financials テーブルを参照。
  - research.feature_exploration: 将来リターン計算（複数ホライズン）、IC（スピアマン ρ）計算、ファクター統計サマリー、ランク関数を実装。外部ライブラリに依存しない純粋 Python 実装。
  - research パッケージのエクスポートを整備（zscore_normalize などとの統合）。
- AI ニュース NLP（下流のスコアリング）
  - ai.news_nlp: raw_news を OpenAI API（gpt-4o-mini）でセンチメント解析して ai_scores に書き込むためのロジックを実装（バッチ処理、トークン肥大対策、リトライ、レスポンス検証、スコアクリップ等）。タイムウィンドウ計算ユーティリティも含む。
  - API キーの検証と例外処理を実装。
  - （ファイルの末尾で処理関数の一部が続く設計になっているが、現状のコードは途中で切れている可能性あり。）
- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成ツールを追加。稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し PASS/FAIL 判定を行う CLI を提供。
    - デフォルト DB は data/paper_trading.db。--from/--to/--db オプションをサポート。
    - P95 計算、欠損データへの頑健な取り扱い（OperationalError を捕捉して N/A を返す）を実装。
- DB / インテグレーション
  - sqlite3 と DuckDB の接続を利用する設計を導入（monitoring 用テーブル初期化のため init_monitoring_db を呼び出し）。
- ユーティリティ
  - utils.process_priority: プロセス優先度と CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分を吸収し、設定失敗時は警告でスキップするフェイルセーフを実装。
  - set_cpu_affinity により最初の N コアにプロセスを固定可能。

Changed
- ログ・起動の初期化箇所でプロセス優先度を最初に上げる設計を採用（run_monitoring/run_execution）。
- ExecutionEngine の paper_trading モードでは DB を分離することで本番データと完全に分離する運用をサポート。

Fixed / Robustness improvements
- 環境変数パーサー (_parse_env_line):
  - export キーワード対応、クォート内のバックスラッシュエスケープ処理、インラインコメント処理などを改善して .env の柔軟な解析を実現。
- MONITOR_POLL_INTERVAL の取り扱い:
  - 不正値（整数以外、0 以下）を検知してデフォルトにフォールバックし、警告ログを出すようにした。
- PAPER_FILL_MODE の検証を追加し、不正な値は ValueError を投げることで早期に設定ミスを検出。
- ファクター / リサーチ系はデータ欠損時に None を返すなど安全に動作するように設計（window 内の行数不足・NULL の伝播抑制など）。
- calc_score_weights: 全スコアが 0 の場合に等金額配分にフォールバックして警告を出力。
- calc_regime_multiplier: 未知レジームに対して警告を出しフォールバック値を返す。
- calc_position_sizes: price が欠損または 0 の場合はスキップ、単元株での切捨て/追加配分ロジック、aggregate cap スケーリングの実装でキャッシュ不足時のスケーリングを保守的に処理。
- utils.process_priority / set_cpu_affinity: 権限不足や未対応プラットフォームへの対応を強化（例外捕捉と警告）。

Known issues / Notes
- ai/news_nlp.py は高度な処理（OpenAI との送受信・DB 置換処理）を実装しているが、現状のソースが途中で切れている箇所がある（fetch_articles から先が断片的）。本番運用前に未実装部分の完成とエンドツーエンドのテストが必要。
- position_sizing の価格フォールバックは TODO コメントが残っている（price が欠損した場合の前日終値や原価のフォールバックは未実装）。
- DuckDB の一部操作（executemany 等）に関する実装上の制約（params が空でないことの確認など）に注意。

セキュリティ
- なし（現時点で顕在のセキュリティ修正は確認されていません。API キー等の扱いは環境変数経由で想定）。

参考 / 補足
- パッケージバージョン: __version__ = "0.1.0"
- 初期設計は「本番 DB と paper_trading DB の明確な分離」「DuckDB を用いたオフライン集計/リサーチ」「OpenAI を使ったニューススコアリング（フェイルセーフ設計）」を重視しています。

もし特定の変更点（例: ai/news_nlp の未完了箇所、calc_position_sizes のスケールアルゴリズム等）について詳細なリリースノートや TODO を作成したい場合は、その旨を教えてください。さらに細かく分割してバージョン履歴を作成します。