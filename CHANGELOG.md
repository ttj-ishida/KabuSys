CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  
https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- （現状なし）

0.1.0 - 2026-04-13
------------------

Added
-----
- 基本パッケージの初期リリースを追加。
  - バージョン: __version__ = "0.1.0"
- 実行エントリポイント
  - run_execution.py: 実売買/ペーパートレーディング両対応の ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は設定にかかわらず本番 sqlite_path を使用して監視データを記録。
- 環境設定/読み込み
  - config.py:
    - プロジェクトルートを .git または pyproject.toml から自動検出し、.env/.env.local を自動読み込み（OS 環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - 堅牢な .env パーサ実装（export、クォート、バックスラッシュエスケープ、インラインコメント等に対応）。
    - Settings クラスを提供。多数の環境変数プロパティ（DB パス、API トークン、監視閾値、PID/KILL ファイルパス、環境判定など）をラップ。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の入力値検証を実装。
- モニタリング関連
  - monitoring_db の初期化を呼び出す場所を run 系スクリプトで確実に実行（冪等）。
- ユーティリティ
  - utils/process_priority.py:
    - プラットフォーム差を吸収するプロセス優先度設定ユーティリティを追加（Windows / POSIX 対応）。
    - CPU affinity を設定する set_cpu_affinity を追加。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップする実装。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - シグナル選定（select_candidates）・等配分（calc_equal_weights）・スコア配分（calc_score_weights）を実装。
  - portfolio/risk_adjustment.py:
    - セクター集中上限適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）を実装。
    - sell_codes を考慮した露出計算、unknown セクターは上限除外などの挙動を設計。
  - portfolio/position_sizing.py:
    - allocation_method ("risk_based", "equal", "score") による株数決定ロジックを実装。
    - 単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer（手数料/スリッページ見積り）をサポート。
    - スケーリング後の端数処理は remainder ソートで再配分するロジックを実装。
- リサーチ / ファクター計算
  - research/factor_research.py:
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、流動性）、バリュー（PER/ROE）などの DuckDB ベースのファクター計算を追加。
    - DuckDB に対する効率的なウィンドウ集計 SQL を採用。
  - research/feature_exploration.py:
    - 将来リターン計算（複数ホライズン）、IC（スピアマンランク相関）計算、rank/summary ユーティリティを追加。外部依存を持たず標準ライブラリのみで実装。
- AI ニュース NLP
  - ai/news_nlp.py:
    - raw_news を集約して OpenAI API（gpt-4o-mini）へバッチ送信し、銘柄別のセンチメントスコアを ai_scores テーブルへ書き込む機能を追加。
    - バッチサイズ、文字数上限、記事数上限、スコアクリップ（±1.0）、最大リトライ＆指数バックオフなどの保護機構を実装。
    - 出力検証、部分失敗時のテーブル更新で既存スコア保護（DELETE→INSERT の範囲限定）を採用。
    - ニュース収集ウィンドウの時間計算ユーティリティ calc_news_window を提供。
- ツール
  - tools/paper_verification_report.py:
    - ペーパートレーディングの検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計し、PASS/FAIL 判定を出力。
    - CLI オプション --from/--to/--db をサポート。
- DuckDB / SQLite 統合
  - 各モジュールが DuckDB 接続・SQLite 接続を受け取ってデータ操作を行う設計を採用。

Changed
-------
- 既存の設計方針を明確化
  - research, portfolio, position sizing 等の関数群を「DB 参照なし（メモリ計算）」や「DuckDB 経由でのみ参照」などの責務分離に従って整理。
- .env 自動ロードの優先順位を明確化（OS 環境 > .env.local > .env）。
- 実行スクリプトで最初にプロセス優先度を設定するように統一。

Fixed
-----
- 入力検証の追加 / 安全化
  - MONITOR_POLL_INTERVAL が不正な整数や 0 以下の場合にフォールバックして例外を避けるよう修正。
  - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL の不正値チェックを追加し、誤設定時にわかりやすい例外を投げるようにした。
  - news_nlp の API キー未設定時に明示的な ValueError を発生させるようにした。
- プロセス優先度 / CPU affinity の設定で権限不足や未対応環境に対して安全にスキップし、ログで通知するように改善。
- 各集計処理（paper_verification_report 等）でテーブル未存在時に sqlite3.OperationalError を捕捉してフォールバックする堅牢化を実装。

Security
--------
- OpenAI API キー等の機密情報は Settings/環境変数経由で管理する設計。自動 .env ロード時も OS 環境変数は上書きされないよう保護。

Notes / Known limitations
-------------------------
- position_sizing の lot_size は現状グローバルな単位（デフォルト 100）を想定。将来的に銘柄別 lot_map を受け取る拡張予定。
- apply_sector_cap の価格欠損（price=0.0）時は露出が過小評価されうる点を TODO コメントで指摘。将来的なフォールバック価格の導入を検討中。
- research モジュールは prices_daily / raw_financials テーブルに依存。テーブルの完全性により結果が大きく変化する。
- ai/news_nlp の OpenAI 呼び出しは外部 API に依存するため、API のレートやコストに注意が必要。

--- 

（今後のリリースでは各機能ごとの細かな改善・バグ修正・パフォーマンスチューニングを追記していきます。）