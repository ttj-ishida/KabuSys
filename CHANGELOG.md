CHANGELOG
=========

このファイルは Keep a Changelog のガイドラインに準拠して作成されています。
https://keepachangelog.com/ja/1.0.0/

フォーマット:
- Unreleased: 今後の変更
- バージョン: YYYY-MM-DD の形式でリリース日を記載

[Unreleased]
------------

（未リリースの変更はここに記載してください）

0.1.0 - 2026-04-13
-----------------

初期公開リリース。

Added
- 全体
  - パッケージ初期実装を追加。モジュール群を通じて自動売買エンジン、モニタリング、リサーチ、ポートフォリオ構築、ツール、ユーティリティ、AIニューススコアリングを提供。
  - DuckDB / SQLite を使ったローカルデータ基盤を標準搭載。
- 実行用エントリポイント
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（data/paper_trading.db がデフォルト）を使用し、MockBrokerClient を利用して本番 DB と分離して動作可能。
    - プロセス優先度設定（高優先）を実行開始時に行う。
    - ExecutionEngine 起動前に OrderRepository、OrderManager、RiskManager、Reconciler の組立てを実施。RiskManager にはデフォルトの RiskConfig を使用。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化する（init_monitoring_db）。
    - プロセス優先度を設定し、例外発生時にログを残してポーリング継続するフェイルセーフなループを提供。
- 設定管理
  - config.py: .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
    - .env パーサは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントを考慮した堅牢な実装。
    - 各種環境変数プロパティ（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等）、検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を追加。
- ポートフォリオ構築
  - portfolioモジュール:
    - portfolio_builder: 候補選定（スコア降順・タイブレーク）、等金額配分、スコア加重配分（スコア全部0なら等配分にフォールバック）。
    - risk_adjustment: セクター集中の上限適用（apply_sector_cap）、レジーム乗数計算（calc_regime_multiplier、bull/neutral/bear 対応、未知レジームは警告とフォールバック）。
    - position_sizing: 各銘柄の発注株数計算（risk_based / equal / score）、単元丸め（lot_size）、aggregate cap（利用可能現金に応じたスケーリング）や cost_buffer を用いた保守的見積り。
- リサーチ
  - research モジュール:
    - factor_research: Momentum / Volatility / Value ファクター計算（DuckDB の prices_daily / raw_financials を参照）。MA200、ATR20、各種モメンタムや流動性指標を計算。
    - feature_exploration: 将来リターン（複数ホライズン）計算、IC（Spearman の rho）計算、ファクター統計サマリー、ランク付けユーティリティを提供。外部ライブラリに依存しない実装。
- AI ニューススコアリング
  - ai/news_nlp.py:
    - raw_news と news_symbols を集約し OpenAI API（gpt-4o-mini、JSON Mode 想定）へバッチ送信して銘柄ごとの ai_score を ai_scores テーブルへ書き込む機能を追加。
    - バッチサイズ、記事数と文字数のトリミング、429/ネットワーク/5xx の指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップ、部分成功時の既存データ保護（DELETE→INSERT の範囲限定）などを実装。
    - API キーは引数か環境変数 OPENAI_API_KEY から取得（未設定時は ValueError を送出）。
    - 時刻ウィンドウは JST を基準に UTC に変換して判定し、ルックアヘッドバイアスを防止するため datetime.today() を参照しない設計。
- ユーティリティ
  - utils/process_priority.py:
    - プロセス優先度設定（Windows: HIGH/ NORMAL/ IDLE、POSIX: nice 値）と CPU affinity 設定ユーティリティを提供。
    - 未対応 OS の扱いや権限不足時のフェイルオーバー（警告ログ）を実装。
- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を行う。
    - 日付フィルタ対応（--from/--to）、DB パス指定（--db または PAPER_TRADING_SQLITE_PATH 環境変数）、P95 計算ロジック、欠測時の N/A 表示などを実装。
- データベース
  - monitoring_db 初期化を各実行スクリプト起動時に行い、監視テーブルが存在することを保証（冪等）。

Changed
- なし（初期リリース）

Fixed
- .env 読み込みの堅牢化:
  - クォート内のバックスラッシュエスケープ、インラインコメントの扱い、export プレフィックス対応等により .env パースの誤動作を軽減。
- 環境変数の検証強化:
  - KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の不正値検出と明確なエラーメッセージを追加。
- MONITOR_POLL_INTERVAL の不正値（0 以下や非数）を検出してデフォルトにフォールバックするようにして time.sleep の ValueError を回避。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーを明示的に要求する実装。未設定時は例外を発生させることで、秘密鍵の抜け落ちを検出しやすくしている。

Notes / 実装上の注意
- Paper Trading モードは実行時に本番 DB と明確に分離する設計（PAPER_TRADING_SQLITE_PATH）。本番 DB を誤って上書きしないよう注意が必要。
- 一部関数は将来的な拡張（例: lot_size を銘柄ごとに管理する、価格フォールバック源の追加）を想定して TODO コメントを残している。
- DuckDB / SQLite のスキーマやテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, trade_logs, risk_logs, system_status など）への依存があるため、データ投入・マイグレーションを事前に行う必要がある。
- process_priority / set_cpu_affinity は権限やプラットフォーム依存で失敗することがあるが、失敗時は警告ログを出して処理を続行するフェイルセーフを採用。

今後の予定（例）
- AI スコアリングのレスポンス検証を更に強化（スキーマ検証ライブラリ導入の検討）。
- 銘柄別 lot_size 管理、単元未満の注文ロジック改善。
- モニタリングで取得するメトリクス拡張（ディスク IO やネットワーク遅延など）。
- DuckDB を用いた分析パイプラインのバッチ最適化。

--- 

（必要に応じて Unreleased セクションへの変更や、以降のバージョン追加を行ってください）