KEEP A CHANGELOG
すべての注目すべき変更を時系列で記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース。以下の主要機能・コンポーネントを追加しました。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョン: kabusys v0.1.0 を導入。

- 設定・環境読み込み (kabusys.config)
  - .env / .env.local 自動読み込み機能（プロジェクトルートを自動検出）。
  - export 形式やクォート、行内コメントに対応した堅牢な .env パーサを実装。
  - 環境変数取得用 Settings クラスを導入（J-Quants / kabu API / データベース / 監視閾値 / 実行環境など）。
  - 環境値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）の実装。

- 実行・監視スクリプト
  - run_execution.py:
    - ExecutionEngine 起動スクリプト。KABUSYS_ENV に応じた DB 選択（paper_trading の場合は paper_trading.db を使用）および BrokerClientFactory 経由でブローカークライアントを生成。
    - stop フラグ (data/stop_requested.flag) と pid ファイル管理をサポート。
    - デーモンスレッドでエンジンを実行し、停止フラグを検知して安全停止を実行。
  - run_monitoring.py:
    - SystemMonitor ポーリングループ起動スクリプト（デフォルト 60 秒、MONITOR_POLL_INTERVAL 環境変数で上書き可能）。
    - 監視は本番 sqlite_path を使用（環境にかかわらず本番監視 DB を参照する設計）。
    - stop フラグ検知でループ終了、KeyboardInterrupt ハンドリング、DB 接続のクリーンアップ。

- 実行ユーティリティ (kabusys.utils.process_priority)
  - クロスプラットフォームなプロセス優先度設定（Windows / POSIX の差分吸収）。
  - CPU Affinity 設定ユーティリティを提供。
  - アクセス権限や未対応プラットフォーム時は警告ログを出してフォールバック。

- ポートフォリオ構築モジュール (kabusys.portfolio)
  - portfolio_builder:
    - シグナル選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。全スコアが 0 の場合は等配分へフォールバック。
  - risk_adjustment:
    - セクター集中制限を適用する apply_sector_cap（既存ポジション時価を考慮、"unknown" セクターは制限対象外）。
    - 市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知レジームは 1.0 にフォールバック）。
  - position_sizing:
    - allocation_method に応じた株数算出 calc_position_sizes（risk_based / equal / score）。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap、コストバッファを考慮したスケーリングアルゴリズムを実装。
    - 現行ポジション差分算出により買付分のみを返す。

- 研究・リサーチモジュール (kabusys.research)
  - factor_research:
    - Momentum / Volatility / Value ファクター計算関数（calc_momentum / calc_volatility / calc_value）。DuckDB の prices_daily / raw_financials を用いた SQL ベース実装。
    - ATR, MA200, 1M/3M/6M リターンなどを計算し、データ不足時は None を返す設計。
  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応）。
    - スピアマンランク相関（IC）計算 calc_ic、rank、および factor_summary（基本統計量）。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- ニュース NLP モジュール (kabusys.ai.news_nlp)
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント解析し、銘柄ごとのスコアを ai_scores テーブルへ書き込むワークフローを実装。
  - バッチ処理（最大 20 銘柄/コール）、トークン肥大対策（記事数・文字数上限）、JSON Mode を利用した厳密なレスポンス検証を実装。
  - リトライ（429 / ネットワーク / 5xx）を指数バックオフで処理し、部分失敗時も他銘柄データを保護するために対象コード限定で更新。

- ツール (kabusys.tools.paper_verification_report)
  - Paper Trading 向け検証レポート生成 CLI。SQLite（デフォルト data/paper_trading.db）を読み、稼働率・注文成功率・送信率・P95 レイテンシ等を集計して PASS/FAIL を判定。
  - P95 計算、日付範囲フィルタ (--from/--to)、しきい値を定義しレポート出力を行う。

- DB 初期化ユーティリティ
  - 監視用テーブルの冪等な初期化 init_monitoring_db を呼び出す組み込み（monitoring テーブルの存在を保証）。

### 変更 (Changed)
- （初回リリースのため履歴上の変更はありません）

### 修正 (Fixed)
- 設定値や入力値の堅牢化:
  - MONITOR_POLL_INTERVAL の不正値検出時にデフォルト値へフォールバックするようにし、警告ログを出力。
  - PAPER_FILL_MODE の無効値検出時に明確な例外を送出。
  - calc_score_weights: 全銘柄スコアが 0 の場合に等配分へフォールバックして警告を出力。
  - DuckDB / SQLite 参照時にテーブル欠如で例外となる箇所を try/except で安全に扱い、ツールが DB の存在有無に寛容になるよう対応（paper_verification_report）。

### 廃止 (Removed)
- （該当なし）

### セキュリティ (Security)
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出して誤使用を防止。

### 既知の制限・注意点 (Notes / Known issues)
- news_nlp や research モジュールは DuckDB の特定テーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores 等）に依存します。これらテーブルのスキーマ/データが揃っていない環境では実行できません。
- run_monitoring は「監視は本番 sqlite_path を使用する」設計のため、開発環境で実行する際は sqlite_path の指定に注意してください。
- apply_sector_cap のセクター露出計算は price_map に価格が無い（0.0）場合、露出が過少見積りされる可能性があります（コード内に TODO を記載）。将来的に価格フォールバックを追加予定。
- calc_position_sizes の単元丸めやスケーリングは lot_size が全銘柄共通である前提です。将来的に銘柄別 lot_size をサポートする計画あり。

--- 

今後のリリース案内（例）
- Unreleased: Broker / ExecutionEngine のテスト追加、news_nlp の部分失敗時のロールバック改善、単元情報の銘柄別対応などを予定。

（注）この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートとして使用する場合はリリース作業・コミット履歴に基づく最終確認を行ってください。