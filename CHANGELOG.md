# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 基本リリースを追加。以下の主要機能・モジュールを実装しました。
  - 実行エンジン起動スクリプト
    - run_execution.py：ExecutionEngine を起動する CLI スクリプトを追加。  
      - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離する仕組みを導入。  
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、EngineConfig に基づく ExecutionEngine の起動・停止ロジックを実装。  
      - 停止フラグ (data/stop_requested.flag) と PID ファイル管理をサポート。デーモンスレッドでセッションを実行し、フラグ検知で安全に停止可能。
  - 監視ポーリング起動スクリプト
    - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。  
      - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔をオーバーライド可能（デフォルト 60 秒）。0 以下や不正値はフォールバックしてデフォルトを使用。  
      - 監視は環境に関係なく本番 sqlite_path（Settings.sqlite_path）を参照する設計。停止フラグ検知でループを終了。
  - 設定管理
    - config.py：.env ファイル自動ロード機能と豊富な環境変数パースを実装。  
      - プロジェクトルートの自動検出（.git または pyproject.toml）を実装。CWD に依存しない読み込み。  
      - .env/.env.local の読み込み順序（OS 環境 > .env.local > .env）、override/protected の概念を導入。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。  
      - .env の各行パーサは export プレフィックス、クォート文字列、バックスラッシュエスケープ、インラインコメントなどを正しく扱う。  
      - 各種設定プロパティを追加（J-Quants / kabuAPI / LINE / DB パス / 監視しきい値 / PAPER_FILL_MODE バリデーション 等）。
  - ポートフォリオ構築ライブラリ
    - kabusys.portfolio:
      - portfolio_builder.py：候補選定（select_candidates）・等金額／スコア加重重み計算（calc_equal_weights / calc_score_weights）を実装。スコア全ゼロ時は等金額へフォールバックし警告を出力。
      - position_sizing.py：発注株数決定ロジック（calc_position_sizes）を実装。  
        - risk_based / equal / score の配分方式、単元株（lot_size）丸め、max_position_pct／max_utilization／cost_buffer を考慮した aggregate cap スケーリング、端数配分アルゴリズムを実装。  
      - risk_adjustment.py：セクター上限適用（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。unknown セクターはセクター上限を適用しない設計。
  - 研究・ファクター計算
    - kabusys.research:
      - factor_research.py：モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、相対ATR、20日平均売買代金、出来高比）およびバリュー（PER, ROE）ファクター計算関数を実装。DuckDB を用いた SQL ベースの計算で、欠損データハンドリングを考慮。
      - feature_exploration.py：将来リターン計算（calc_forward_returns）、IC（Spearman ランク相関）計算（calc_ic）、ファクター統計サマリ（factor_summary）、ランク関数を実装。外部ライブラリに依存せず標準実装。
  - AI ニュース NLP スコアリング
    - kabusys.ai.news_nlp.py：raw_news から銘柄別センチメントを生成して ai_scores テーブルへ格納するための実装を追加。  
      - OpenAI API（gpt-4o-mini）を利用したバッチ処理（最大バッチサイズ 20）、JSON Mode 出力のバリデーション、スコアの ±1.0 クリップ、再試行（429/ネットワーク/5xx に対する指数バックオフ）などを備える。  
      - ニュース収集ウィンドウ（前日15:00 JST〜当日08:30 JST を UTC に変換）を計算するユーティリティ（calc_news_window）を実装。  
      - API キー未設定時は ValueError を送出する安全策を導入。フェイルセーフにより API 失敗時は処理をスキップして継続する設計。
  - 検証ツール
    - tools/paper_verification_report.py：Paper Trading 用の検証レポート生成スクリプトを追加。  
      - システム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均・最大・P95）を集計して PASS/FAIL 判定を出力。CLI オプション --from/--to/--db を提供。
  - ユーティリティ
    - utils/process_priority.py：プロセス優先度設定ユーティリティ（set_process_priority）を追加。  
      - Windows と POSIX（Linux/Mac/FreeBSD）を吸収し、適切な nice / priority を設定。アクセス権限や未対応 OS では警告を出してスキップ。  
      - CPU affinity を設定する set_cpu_affinity を追加。

### 変更 (Changed)
- パッケージ初期バージョンとして全体構成を確立：
  - パッケージメタ情報（kabusys.__init__.__version__ = "0.1.0"）を設定。
  - kabusys.research パッケージの public API を __all__ で整理。

### 修正 (Fixed)
- run_monitoring のポーリング間隔取得で不正な環境変数値（非数値・0 以下）を扱う際に警告してデフォルトにフォールバックするよう堅牢化。
- .env ファイル読み込みでファイルオープンに失敗した際に警告（warnings.warn）を出して処理継続するよう改善。
- calc_score_weights で全スコアが 0.0 の場合の挙動を等金額配分にフォールバックして警告を出すようにし、ゼロ除算を回避。

### 注意点 / 既知の制約 (Notes)
- run_monitoring は「監視 DB」に関して環境に関わらず Settings.sqlite_path（本番 DB）を使用します。テストや paper_trading と分離したい場合は設定の上書きを検討してください。
- position_sizing の価格欠損（price が 0.0 のケース）は TODO コメントの通り現状では単純にスキップします。将来、前日終値や取得原価などのフォールバックロジックを検討中です。
- news_nlp モジュールは外部 API（OpenAI）を使用するため、API キー管理とレート制限に注意してください。処理は部分的失敗を許容するよう設計されていますが、完全な冪等性や部分ロールバックの要件がある場合はデータベース側での追加保護が必要です。
- DuckDB を利用する SQL 実装は DuckDB のバージョン依存（executemany の挙動など）に注意が必要です（コード中に説明あり）。

---

今後の予定（例）
- テストカバレッジ拡充・ユニットテスト追加
- position_sizing の価格フォールバック改善
- news_nlp の部分失敗時のリカバリ戦略強化とメトリクス計測

（以上）