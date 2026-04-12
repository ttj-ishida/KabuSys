CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に準拠して記載します。  
バージョンはパッケージ内の __version__（0.1.0）およびコードから推測される主要追加を基に構成しています。日付はコード解析日 (2026-04-12) を使用しています。実際のリリース履歴と差異がある場合は適宜編集してください。

Unreleased
----------

Added
- AI ニュースセンチメントスコアリング機能を追加（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）に対して銘柄単位のセンチメントを JSON で取得。
  - バッチ処理（最大 20 銘柄/リクエスト）、トークン肥大対策（記事・文字数のトリム）、スコアの ±1.0 クリップを実装。
  - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライを想定。
  - 結果を ai_scores テーブルへ安全に置換（部分失敗時にも既存スコアを保護する実装方針）。

- リサーチ・分析モジュールを追加（src/kabusys/research/*）
  - ファクター計算: Momentum, Volatility, Value（DuckDB を用いた SQL+Python 実装）。
  - 特徴量探索: 将来リターン計算（複数ホライズン対応）、IC（Spearman）計算、ファクター統計サマリ、ランク付けユーティリティ。
  - DuckDB 接続を受け取り外部 API に依存しない設計。

- ポートフォリオ構築モジュールを追加（src/kabusys/portfolio/*）
  - 候補選定（スコア降順、タイブレーク）、等重配分・スコア加重配分、スコア全零時のフォールバック警告。
  - セクター集中制限（apply_sector_cap）、市場レジームに基づく乗数（calc_regime_multiplier）。
  - ポジションサイズ算出（risk_based / equal / score）、単元株（lot）丸め、投下資金の aggregate スケールダウンと残差再配分ロジック。

- 実行・監視エントリポイントを整備
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - BrokerClientFactory によるブローカー切替（本番 / paper_trading）、RiskManager / Reconciler 等の組み立て、ExecutionEngine の run_session 呼び出し。
    - paper_trading 環境では専用 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - SystemMonitor を用いた定期チェック、プロセス優先度設定、監視 DB 初期化。

- ユーティリティを追加・強化（src/kabusys/utils/*）
  - プロセス優先度・CPU affinity 設定ユーティリティ（set_process_priority, set_cpu_affinity）
    - Windows / POSIX を吸収し、権限不足や未サポート環境は警告でフォールバック。

- 設定読み込みの改善（src/kabusys/config.py）
  - .env 自動読み込み（.env → .env.local、OS 環境変数は保護して上書き順序を確保）。
  - .env パーサの堅牢化（export 形式、クォート内エスケープ、インラインコメント取り扱い）。
  - 設定プロパティで検証を実施（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。

- Paper Trading 検証レポートツールを追加（src/kabusys/tools/paper_verification_report.py）
  - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計して PASS/FAIL 判定を出力。
  - コマンドライン引数で期間指定（--from/--to）および DB パス指定可能。

Changed
- DuckDB と SQLite を併用するデータアクセス設計を採用（実行・リサーチ・AI モジュール間で使い分け）。
- Execution/Monitoring の起動時にプロセス優先度を最初に設定してから他リソースを初期化するように統一。

Fixed
- 設定値の不正入力に対するフォールバックや警告を明示的に追加
  - MONITOR_POLL_INTERVAL が 0 以下または非整数の際にデフォルトにフォールバック（run_monitoring）。
  - PAPER_FILL_MODE の不正値判定による ValueError。
  - LOG_LEVEL / KABUSYS_ENV のバリデーション強化。

0.1.0 - 2026-04-12
-----------------

Added
- 初期リリース（推定）
  - 基本的な自動売買システムのコア構成を実装:
    - 実行エンジン（ExecutionEngine）と注文管理（OrderManager / OrderRepository）
    - リスク管理（RiskManager）と Reconciler（注文の突合せ）
    - モニタリング用 SystemMonitor と監視 DB 初期化
    - 設定管理（Settings）と .env 自動読み込みロジック
    - プロセス優先度設定ユーティリティ（Windows / POSIX 対応）
    - ポートフォリオ構築、リスク調整、ポジションサイズ算出の基礎的実装
    - DuckDB/SQLite を利用した価格・ファイナンスデータの処理設計
    - パッケージ初期メタ情報（src/kabusys/__init__.py に __version__ = "0.1.0"）

Security
- OpenAI API キーは引数または環境変数（OPENAI_API_KEY）からしか取得せず、未設定時は明示的にエラーを出す仕様（ai/news_nlp）。

Notes / その他
- DuckDB の executemany の制約（バージョン依存）や一部の SQL 実行時エラー（テーブル未存在など）に対して、ツール側で sqlite3.OperationalError を捕捉してフォールバックする実装がある（tools/paper_verification_report）。
- 一部の関数に TODO コメントあり（例: price 欠損時のフォールバック価格、銘柄別 lot_size 管理等）。将来的な拡張余地を残す設計。

署名
----
この CHANGELOG は与えられたコードベースの内容から推測して作成しています。実際のリリースタグ・日付・順序や細かい修正履歴は、Git のコミット履歴やリリースノートを基に正式に作成してください。