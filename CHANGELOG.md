CHANGELOG
=========
この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
バージョニングはセマンティックバージョニングを想定しています。

Unreleased
----------
（現時点で未リリースの変更はありません）

0.1.0 - 2026-04-16
------------------

Added
- 初回リリース。
- コア機能の追加:
  - Execution エンジン起動スクリプト（src/kabusys/run_execution.py）
    - KABUSYS_ENV に応じた DB 分離（paper_trading 時は data/paper_trading.db を使用）。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine の起動処理。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理（data/execution.pid）に対応。
    - スレッド化してデーモン実行、停止フラグ検知で安全に停止。
  - 監視（Monitoring）起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor を用いたポーリングループ。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - check_once() 実行時の例外を捕捉して次ポーリングへ継続。
  - 設定管理モジュール（src/kabusys/config.py）
    - .env / .env.local の自動読み込み（OS 環境変数を保護）。
    - .env パースの細かい仕様対応（export 形式、クォートやエスケープ、コメント処理）。
    - Settings クラスに各種プロパティを用意（DB パス、API トークン、監視閾値、環境判定 等）。
    - KABUSYS_ENV / LOG_LEVEL 等の値検証を実装。
  - Portfolio 構築モジュール（src/kabusys/portfolio/*）
    - 候補選定（select_candidates）、等配分/スコア配分（calc_equal_weights / calc_score_weights）。
    - セクター制限（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）。
    - ポジションサイズ計算（calc_position_sizes）: リスクベース / equal / score ベース、単元株丸め、aggregate cap スケーリング等。
  - Research モジュール（src/kabusys/research/*）
    - ファクター計算（calc_momentum, calc_volatility, calc_value）。
    - 特徴量探索ユーティリティ（将来リターン calc_forward_returns、IC 計算 calc_ic、統計サマリー factor_summary、rank）。
    - DuckDB 接続を受け取り SQL を用いて高速に計算する設計。
  - AI ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news を OpenAI API（gpt-4o-mini 想定）でセンチメント解析し ai_scores テーブルへ書き込み。
    - バッチ処理、トークン肥大化対策（記事数・文字数制限）、エクスポネンシャルバックオフによるリトライ、レスポンス検証、スコアクリップ（±1.0）。
    - ニュース収集ウィンドウ計算ユーティリティ（JST→UTC の変換）。
  - ツール: Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - paper_trading DB を解析して稼働率、注文成功率、送信率、レイテンシ（P95）などをレポート出力。
    - デフォルト閾値と PASS/FAIL 判定ロジックを実装。
  - ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows/Linux/macOS の差を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する関数を提供。
  - パッケージメタ情報（src/kabusys/__init__.py）にバージョン 0.1.0 を追加。

Changed
- （初回リリースのため該当なし）

Fixed
- 環境変数パースの堅牢化:
  - export 形式、クォート内のバックスラッシュエスケープ、行内コメントの判定等に対応。
  - 自動読み込みはプロジェクトルートが特定できない場合にスキップする安全策を実装。
- MONITOR_POLL_INTERVAL の入力検証:
  - 0 以下や非整数が設定された場合にデフォルト値へフォールバックし警告を出力。
- 監視ループ・実行エンジンの堅牢化:
  - monitor.check_once() の例外を捕捉してループ継続。
  - 起動時に停止フラグが既に立っている場合は起動を中止する判定を追加。
- DuckDB / SQLite 関連:
  - 監視テーブル初期化関数 init_monitoring_db を起動時に呼び、テーブル存在を保証（冪等）。
- AI モジュール:
  - OpenAI API キー未設定時は ValueError を送出して明示的に失敗するようにした（呼び出し側でハンドリング可能）。
  - レスポンスの検証・スコア範囲クリップ等で不正データ流入を防止。

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は処理を中止して明示的にエラーを返す仕様。

Notes
- Paper Trading 環境は本番 DB と完全に分離される設計（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
- 多くの関数は外部副作用を持たない純関数として設計され、ユニットテストが容易。
- 一部の箇所で将来の改善がコメントとして残されています（例: position_sizing の銘柄別 lot_size 対応、apply_sector_cap の価格フォールバック処理）。
- プラットフォーム固有の権限不足（プロセス優先度設定や CPU affinity 設定）が発生した場合は警告を出しスキップするフォールトトレラント設計。

Breaking Changes
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

参考（重要な環境変数・デフォルト）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- OPENAI_API_KEY: OpenAI API キー（AI ニュース処理に必須）

今後の予定（コード中コメントに基づく）
- 銘柄ごとの単元株情報（lot_size）をマスタ管理し position_sizing に取り込む拡張。
- apply_sector_cap での価格欠損時のフォールバック実装（前日終値や取得原価を利用）。
- AI モジュールの部分失敗時のさらなるリトライ・再試行戦略やバッチ制御の改良。

--- 
この CHANGELOG は、提示されたソースコードから推測可能な機能追加・設計上の意図・注意点を基に作成しています。必要であれば、各リリース項目を実際のコミットやリリース日付に合わせて調整してください。