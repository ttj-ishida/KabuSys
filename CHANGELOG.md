# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
セマンティックバージョニングを意図していますが、ここでは現時点での初期公開リリースとして v0.1.0 を記載します。  
（内容は与えられたコードベースから推測してまとめています）

## [0.1.0] - 2026-04-13

### 追加 (Added)
- 実行エントリポイントを追加
  - run_execution.py: ExecutionEngine 起動スクリプト。環境変数 KABUSYS_ENV=paper_trading のときは paper_trading 用の専用 SQLite DB を使い、MockBrokerClient を利用する設計を採用。
  - run_monitoring.py: SystemMonitor をポーリングで起動する監視スクリプト。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔オーバーライドに対応。
- 設定管理モジュール (kabusys.config)
  - .env 自動ロード機能（プロジェクトルートの検出：.git または pyproject.toml を基準）を実装。ロード順序は OS 環境 > .env.local > .env。
  - .env パースの堅牢化（export プレフィックス、クォート付き値のエスケープ処理、インラインコメントの扱い等）。
  - Settings クラスで各種設定をプロパティとして提供（DB パス、OpenAI 等のトークン、監視閾値、環境判定フラグなど）。
  - 必須環境変数未設定時の明示的エラー (_require)。
- 監視・監査関連
  - monitoring_db の初期化ユーティリティ（init_monitoring_db）を呼び出して監視テーブルの存在を保証。
  - run_monitoring はどの KABUSYS_ENV でも本番 sqlite_path を監視 DB として使う設計（意図的な運用方針）。
- 実行系構成
  - ExecutionEngine 組み立て：BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler を組み合わせてセッション実行。
  - RiskManager 用の RiskConfig にデフォルトパラメータを設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 関連、max_drawdown 等）。
- ポートフォリオ構築モジュール (kabusys.portfolio)
  - portfolio_builder: シグナル選別 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
  - risk_adjustment: セクター集中制限 (apply_sector_cap)、市場レジームに基づく乗数 (calc_regime_multiplier) を実装。
  - position_sizing: 各銘柄の発注株数計算ロジック (calc_position_sizes)。risk_based / equal / score の配分方式、単元株切り捨て、aggregate cap によるスケーリング、手数料・スリッページ見積り用 cost_buffer をサポート。
- リサーチ・ファクター計算 (kabusys.research)
  - factor_research: Momentum / Volatility / Value ファクター計算（DuckDB 接続を受け prices_daily / raw_financials を参照）。
  - feature_exploration: 将来リターン計算(calc_forward_returns)、IC（calc_ic）、ファクター統計サマリー (factor_summary) 、ランク付けユーティリティ (rank) を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - DuckDB を用いた高速集計を前提とした設計。
- ニュース NLP スコアリング (kabusys.ai.news_nlp)
  - OpenAI (gpt-4o-mini) を用いて raw_news を銘柄ごとに集約してセンチメントスコアを算出、ai_scores テーブルへ書き込み。
  - バッチ処理（最大 20 銘柄/リクエスト）、記事数／文字数のトリム、429/ネットワーク/5xx に対する指数バックオフのリトライ実装、レスポンスバリデーション、スコアの ±1.0 クリップを実装。
  - タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST の記事を対象）を util として提供。
- ツール
  - Paper Trading 検証レポート生成ツール (kabusys.tools.paper_verification_report)。期間指定 (--from / --to) によるレポート出力、稼働率・注文成功率・送信率・レイテンシ（P95）などを算出して PASS/FAIL 判定を出力。
- ユーティリティ
  - process_priority ユーティリティ (kabusys.utils.process_priority): Windows / POSIX を吸収してプロセス優先度設定（high/normal/low）を提供。CPU affinity を設定する set_cpu_affinity も実装し、アクセス拒否等は警告でスキップする堅牢化を行った。
- パッケージ情報
  - kabusys.__version__ を "0.1.0" に設定。

### 変更 (Changed)
- DB 周り
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と分離する挙動を採用（安全な検証運用のため）。
  - monitoring の初期化は冪等で実行されるよう init_monitoring_db を起動時に呼び出す。
- ロギング・運用
  - 起動時にプロセス優先度を "high" に設定する呼び出しを導入（run_execution / run_monitoring の先頭）。
  - 実行中の例外はログに例外トレースを出力してループ継続するフェイルセーフ設計（監視ループの堅牢化）。
- 環境変数扱いの改善
  - Settings のプロパティで値検証を強化（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の検証と明示的なエラーメッセージ）。
  - .env ロード時に OS 環境変数を保護する protected 機構を導入し、.env.local の上書き挙動を制御。

### 修正 (Fixed)
- 環境変数関連の堅牢化
  - MONITOR_POLL_INTERVAL の不正な値（数値以外、0以下）を検出して警告しデフォルト（60秒）にフォールバックする処理を追加。
  - .env パーサーでのクォート処理やエスケープ処理の不備に対処し、インラインコメントの誤検出を防止。
- ニュース NLP / API 呼び出し
  - OpenAI 呼び出しでの部分失敗時に他銘柄の既存スコアを保持するため、更新操作をコードで限定して実行するロジックを採用（部分失敗耐性）。
  - API キー未設定時に明示的な ValueError を投げるよう改善。
- リサーチ・統計ロジック
  - P95 の算出ロジックを実装（パーセンタイルのインデックス計算を明示）。
  - calc_ic の入力検証で有効レコード数が 3 未満のとき None を返す安全対策。
  - rank() 関数で ties を平均ランクで扱う際に浮動小数点丸め（round(..., 12)）を導入して安定性を確保。
- position sizing のスケーリング
  - aggregate cap 適用時のスケーリング／端数処理を改良し、lot_size 単位での再配分を実装。コスト見積りに cost_buffer を導入して保守的な見積りを可能に。

### ドキュメント・注意 (Documentation / Notes)
- 各モジュールの docstring に設計方針・戻り値・期待される DB スキーマなどの説明を付与。特に research / portfolio / ai モジュールは外部依存を避け DuckDB / prices_daily / raw_financials 等のスキーマ前提で設計されている点に注意。
- run_monitoring は運用上、どの環境でも本番の sqlite_path を参照する設計になっているため、テスト環境で実行する際は sqlite_path を適切に設定すること。
- PAPER_FILL_MODE 等の環境変数は有効値が限定されており、誤設定時は起動時に例外が発生する。ドキュメント（.env.example 相当）に従って設定すること。

---

今後の予定（推測）
- 単体テスト・CI の追加、エラー監視の強化、より細かいログレベル設定の適用、Broker クライアントのモック強化とインテグレーションテストの整備などが想定されます。