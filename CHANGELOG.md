CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。
バージョン付けはリポジトリ内の __version__ を基にしています（0.1.0）。

[Unreleased]
-------------

（現時点のコードベースは 0.1.0 としてリリース相当と判断しました。今後の変更はここに追記してください。）

0.1.0 - 2026-04-16
------------------

Added
- 初回リリース: KabuSys の基本コンポーネント群を追加。
  - 実行・監視
    - run_execution.py: ExecutionEngine を起動するスクリプトを追加。  
      - KABUSYS_ENV=paper_trading 時は paper_sqlite_path を用いて本番 DB と完全に分離（Paper Trading 用 DB: data/paper_trading.db をデフォルト）。
      - BrokerClientFactory を用いたブローカークライアントの切替（Mock を含む想定）。
      - Execution エンジンを別スレッドで起動し、data/stop_requested.flag による安全停止に対応。
      - PID 書き込み（data/execution.pid）をサポート。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
      - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視処理は常に本番 sqlite_path を参照する設計（環境に依らない監視データ収集）。
      - data/stop_requested.flag でループ停止。
  - 設定管理
    - config.py: 環境変数/.env 自動読み込み機能を実装。  
      - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を読み込む（OS 環境変数を保護する仕組みを含む）。  
      - 複雑な .env 行（export 形式、クォート、エスケープ、インラインコメント）に対応するパーサ実装。  
      - Settings クラスにより環境値を型付きかつ検証付きで取得（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等のバリデーション）。
  - データベース / 分析基盤
    - DuckDB 統合: 各種リサーチ・AI モジュールが DuckDB 接続を受け取る設計（prices_daily / raw_financials 等の読み取りを想定）。
    - monitoring_db 初期化ヘルパーを起動スクリプトから呼び出して監視テーブルの存在を保証。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - portfolio/portfolio_builder.py: 候補選定（select_candidates）と重み算出（calc_equal_weights, calc_score_weights）を実装。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とレジーム乗数計算（calc_regime_multiplier）を実装。
    - portfolio/position_sizing.py: 発注株数計算（calc_position_sizes）を実装。  
      - risk_based / equal / score の割当方式に対応。単元株（lot_size）、max_position_pct、max_utilization、手数料バッファ(cost_buffer) を考慮したスケーリングロジックを実装。
  - リサーチ / ファクター
    - research/factor_research.py: Momentum / Volatility / Value ファクター計算（calc_momentum, calc_volatility, calc_value）を実装。  
      - DuckDB SQL を利用して日付ウィンドウ内で集計・ウィンドウ関数で計算。
    - research/feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリ（factor_summary）、ランク変換（rank）を実装。  
      - 外部依存を持たない純 Python 実装（pandas 等未使用）。
    - research パッケージは kabusys.data.stats の zscore_normalize と合わせてエクスポート。
  - AI / ニュース
    - ai/news_nlp.py: raw_news テーブルのニュースを OpenAI（gpt-4o-mini を想定）でスコアリングするモジュールを追加。設計上の特徴:
      - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換して扱う）に基づく記事集約。
      - 銘柄ごとに記事数・文字数の上限を設けてトークン肥大を制御（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
      - バッチ（最大 _BATCH_SIZE=20 銘柄）送信、429/ネットワーク/5xx に対する指数バックオフのリトライ実装を想定。
      - API キー未設定時は ValueError を送出。レスポンス JSON のバリデーションとスコアの ±1.0 クリップ。
      - 成果は ai_scores テーブルへ置換的に反映する方針（部分失敗時の保護を考慮）。
  - ツール
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。CLI から期間（--from/--to）・DB パス（--db）を指定可能。出力内容:
      - システム稼働率（system_status）、注文成功率/送信率（trade_logs）、リスク却下数（risk_logs）、API レイテンシ（平均/最大/P95）を集計して人間可読なレポートを表示。
      - PASS/FAIL 判定基準（稼働率 99%, fill_rate 90%, send_rate 95%, P95 latency <= 200ms）を採用。
      - DB テーブルが存在しない場合に sqlite3.OperationalError を捕捉して N/A を扱う耐障害性を実装。
  - ユーティリティ
    - utils/process_priority.py: プロセス優先度設定と CPU affinity 設定のユーティリティを追加。  
      - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収。権限不足や未サポート環境では警告ログを出して安全にスキップ。
  - パッケージメタ
    - __init__.py に __version__ = "0.1.0" を追加。

Changed
- なし（初回リリースのため該当なし）。

Fixed
- 設定/実行時の堅牢性向上（実装から推測）
  - MONITOR_POLL_INTERVAL のパース時に不正な値（負数・非整数）が指定された場合、警告を出してデフォルト値にフォールバックする実装を追加。
  - .env パーサがクォートやエスケープ、インラインコメントを適切に処理するよう強化（export 形式への対応含む）。
  - run_monitoring/run_execution/ツール系で DB 接続後のテーブル未存在や OperationalError を想定した例外処理を導入し、部分的な欠落データでも処理を継続するようになっている。
  - process_priority の呼び出しで権限不足や未実装の API に対して例外を捕捉し、ワーニングログでフォールバックするようにした。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY により提供する設計。未設定時は例外を投げて誤使用を防止。

Notes / 実装上の注意（コードから推測）
- 多くの関数は「純粋関数」あるいは明示的に外部副作用（DB 書込等）をコントロールしており、ユニットテストが容易な設計になっています（特に portfolio/**, research/**）。
- prices_daily / raw_financials / trade_logs 等のスキーマ依存があるため、DuckDB / SQLite のスキーマ整備が前提です。
- 一部ファイル（例: ai/news_nlp.py）の末尾が実装途中のように見える断片が存在するため（コード断片からの推測）、実運用前にレビュー・追加実装が必要な箇所が残る可能性があります。
- Paper Trading 用 DB を完全分離する設計や、監視ループが環境に依存しない DB を使う方針など、安全運用を意識した設計判断が随所に見られます。

今後の推奨
- news_nlp のエラーハンドリング・部分成功時のロールバック/トランザクション処理の明確化。
- position_sizing の lot_size を銘柄別に設定できるよう拡張（TODO コメントあり）。
- DuckDB のスキーマ定義とサンプルデータをリポジトリに同梱し、研究モジュールの動作確認を容易にすること。

--- 

（この CHANGELOG はコードの内容から推測して作成しています。実際の変更履歴やリリース日付はリポジトリ管理方針・コミット履歴に従って調整してください。）