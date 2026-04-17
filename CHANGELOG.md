# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
現在のバージョン: 0.1.0（初回リリース）

注: 日付はリリース日です。

## [Unreleased]
- 開発中の変更はここに記載します。

## [0.1.0] - 2026-04-17
初回公開リリース。

### 追加
- 全体
  - パッケージ kabusys を新規追加。バージョンは __version__ = "0.1.0"。
  - DuckDB / SQLite を利用したローカル分析・監視基盤を提供。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git / pyproject.toml を基準に探索）。
  - .env のパースはコメント、export プレフィックス、シングル／ダブルクォート、エスケープ、インラインコメントの取り扱いに対応。
  - 環境変数保護（OS 環境変数を上書きしない）をサポート。
  - Settings クラスを実装し、アプリケーションで使用する設定（DB パス、API トークン、閾値、環境種別など）をプロパティで提供。
  - KABUSYS_ENV / LOG_LEVEL の妥当性チェック、PAPER_FILL_MODE の有効値チェックを追加。

- 実行エンジン関連
  - 実行エントリ run_execution.py を提供。ExecutionEngine を起動し、停止フラグや pid ファイルに対応。
  - Paper Trading モード（KABUSYS_ENV=paper_trading）向けに MockBrokerClient を使用し、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）へデータを分離。
  - ExecutionEngine の起動前に初期設定（ブローカ、OrderRepository、OrderManager、RiskManager、Reconciler 等）を組み立てるロジックを追加。
  - RiskManager のデフォルト設定を実装（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。initial_portfolio_value は broker.get_available_cash() から取得して初期化。

- 監視関連
  - run_monitoring.py を追加。SystemMonitor をポーリングするループを起動するスクリプト。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログを残してデフォルトにフォールバック。
  - 監視は実行環境にかかわらず本番 sqlite_path を使用して監視テーブルを操作。
  - 停止フラグ（data/stop_requested.flag）検知によりループを終了する仕組みを実装。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder: BUY シグナルの候補選択（スコア降順、signal_rank によるタイブレーク）、等金額配分・スコア加重配分を実装。
  - position_sizing: 各方式（risk_based, equal, score）に基づく発注株数計算、単元（lot_size）丸め、aggregate cap によるスケールダウン、コストバッファ考慮のロジックを実装。
  - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を実装。未知レジームは警告ログを出してフォールバック。

- 研究・ファクター分析（kabusys.research）
  - factor_research: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、相対ATR、出来高関連）、バリュー（PER/ROE）ファクター計算を追加。DuckDB 接続を受け取り SQL で高速に計算。
  - feature_exploration: 将来リターン計算（任意ホライズン）、Spearman（ランク）ベースの IC 計算、ファクターの統計サマリー、ランク付けユーティリティを提供。
  - research パッケージは zscore_normalize（kabusys.data.stats 依存）等のユーティリティを export。

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。稼働率・注文成功率・送信率・レイテンシ（平均／最大／P95）等を期間指定で集計し、PASS/FAIL 判定を行う CLI。
  - レポートは SQL での集計と簡易統計により出力。DB が存在しない場合はエラーメッセージを出力して終了。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news テーブルを用いて OpenAI（gpt-4o-mini）へバッチ送信し、各銘柄ごとのセンチメントを -1.0〜1.0 でスコア化して ai_scores テーブルへ書き込む処理を実装（score_news）。
  - バッチサイズ、トークン肥大化対策（記事数・文字数のトリム）、API 呼び出しのリトライ（指数バックオフ）、レスポンス検証、スコアのクリッピング、部分成功時のデータ置換戦略（対象コードに限定した DELETE/INSERT）などの堅牢化を実装。
  - OpenAI API キー未設定時は例外を出す（api_key 引数または OPENAI_API_KEY 環境変数）。

- ユーティリティ（kabusys.utils）
  - process_priority: プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。Windows と POSIX 系（Linux/Mac/FreeBSD）の差分を吸収し、アクセス権限や未対応環境では警告ログを出してスキップ。
  - set_process_priority() を起動時に呼び出して優先度を上げる運用を想定（run_monitoring/run_execution で利用）。

### 変更
- DB 初期化
  - init_monitoring_db(sqlite_conn) を実行して監視用テーブルの存在を保証（冪等化）。

- 実行フロー
  - run_execution.run_session をスレッドで起動し、メインスレッドは停止フラグ監視と thread.join で安全に待機・停止を行うように改善。

### 修正（バグ修正・堅牢化）
- 環境変数パースの堅牢化
  - .env のパース処理でクォート内のバックスラッシュエスケープやインラインコメントの取り扱いを修正し、より正確に値を読み込むようにした。
  - MONITOR_POLL_INTERVAL の取得で 0 以下や非整数値の扱いを安全にフォールバックするようにし、time.sleep に渡して ValueError にならないように保護。

- データ欠損・例外耐性
  - factor/research / volatility / value の計算で過去データ不足時に None を返す（NULL 伝播を適切に扱う）。
  - Paper report のクエリ実行時に sqlite3.OperationalError をキャッチしてデフォルト値で続行するようにした（テーブル未作成時の耐性）。
  - news_nlp の API 呼び出しで 429/ネットワーク断/タイムアウト/5xx をリトライし、失敗時は安全にスキップして処理を継続。

- ロギング・デバッグ
  - 各モジュールに debug/info/warning レベルのログを追加し、動作状況やフォールバック理由を記録可能にした。

### 注意点 / 既知の制限
- news_nlp モジュールは OpenAI API を利用するため、実際の運用には OPENAI_API_KEY の設定が必要。
- position_sizing では現在すべての銘柄が共通の lot_size（デフォルト 100）を仮定。将来的に銘柄ごとの単元対応に拡張予定（TODO コメントあり）。
- apply_sector_cap は price_map に価格が欠損（0.0）だとエクスポージャーを過少見積もる可能性がある（コメントに注記。将来的なフォールバック実装を検討）。
- プラットフォーム依存のプロセス優先度設定や CPU affinity は権限不足や未サポート環境ではスキップされる（警告ログ出力）。

---

ファイル構成（主な追加ファイル）
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/run_monitoring.py
- src/kabusys/run_execution.py
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/portfolio/*.py
- src/kabusys/research/*.py
- src/kabusys/ai/news_nlp.py
- src/kabusys/utils/process_priority.py

（必要であれば、各モジュールの詳細な変更点や内部 API の使用例を別途追記します。）