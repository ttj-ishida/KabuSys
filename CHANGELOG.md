# Changelog

すべての注記は Keep a Changelog の規約に準拠します。  
出典: https://keepachangelog.com/ja/1.0.0/

※以下はコードベースの内容から推測して作成した変更履歴です。

## [Unreleased]

- （現在該当なし）

## [0.1.0] - 2026-04-12

### Added
- 基本アーキテクチャと主要コンポーネントを実装（初期リリース）。
  - 実行・監視スクリプト
    - run_execution.py
      - ExecutionEngine の起動エントリポイントを実装。
      - BrokerClientFactory 経由でブローカークライアントを生成し、paper_trading 環境では専用の SQLite（data/paper_trading.db）を使用する分離設計を採用。
      - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてセッションを実行。
      - duckdb（分析用）と sqlite（監視・発注ログ用）を併用。
      - 起動時にプロセス優先度を "high" に設定する処理を追加。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを実装。
      - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒、値検証あり）。
      - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視用 DB の一貫性確保）。
      - 例外発生時にループを継続する堅牢な実装（ログ出力を伴う）。
  - 設定管理
    - config.py
      - .env / .env.local の自動読み込みを実装（プロジェクトルートを .git または pyproject.toml から検出）。
      - export KEY=... 形式、クォート、エスケープ、インラインコメント等に対応した堅牢な .env パーサを実装。
      - OS 環境変数を保護するための上書きガード（protected set）を実装。
      - 各種環境設定プロパティを提供（パス、閾値、挙動フラグなど）。値検証（列挙型チェック、数値変換等）を行う。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動 .env 読み込みを無効化可能。
      - settings インスタンスを公開。
  - ポートフォリオ構築（純関数群）
    - portfolio.portfolio_builder
      - シグナルのソート・候補選定（score・signal_rank に基づく）と、等金額／スコア加重配分を実装。全スコア 0 の場合は等配分へフォールバック。
    - portfolio.risk_adjustment
      - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター比率計算、当日売却予定の除外、"unknown" セクターの扱いを定義。
      - レジームに基づく乗数（calc_regime_multiplier）を実装（bull/neutral/bear のマップとフォールバック）。
    - portfolio.position_sizing
      - position sizing ロジックを実装（risk_based / equal / score の allocation_method をサポート）。
      - 単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金を超えた場合のスケールダウン）を実装。
      - cost_buffer を導入して手数料/スリッページを保守的に見積る。
      - スケーリング時の端数処理（lot 単位での残差を考慮して追加配分）を実装し再現性を確保。
  - モニタリング DB 初期化ユーティリティ（monitoring_db.init_monitoring_db 呼び出しを実装）
    - run_* スクリプトで起動前に監視テーブルの存在を保証する処理を追加（冪等）。
  - ユーティリティ
    - utils.process_priority
      - Windows / POSIX を吸収するプロセス優先度設定（set_process_priority）。
      - CPU affinity を設定する set_cpu_affinity（最初の N コアにピン留め）。
      - psutil の AccessDenied 等は警告でスキップするフェイルセーフ設計。
  - 研究・ファクター計算
    - research.factor_research
      - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20 等）、バリュー（PER/ROE）を DuckDB SQL ベースで計算。
      - ウィンドウ関数を多用し、データ不足の際には None を返す堅牢な設計。
    - research.feature_exploration
      - 将来リターン計算（任意ホライズン）、IC（Spearman の ρ）計算、ファクター統計サマリーを実装。pandas 等に依存しない実装。
  - ツール
    - tools.paper_verification_report
      - Paper Trading の検証レポート生成スクリプトを実装（コマンドライン引数 --from/--to/--db をサポート）。
      - システム稼働率・注文成功率・送信率・レイテンシ（P95）等を算出し、閾値と比較して PASS/FAIL を判定。
      - P95 計算、日付フィルタ、DB 存在チェック、OperationalError のハンドリング等を実装。
  - AI ニュース NLP（部分実装）
    - ai.news_nlp
      - raw_news を OpenAI（gpt-4o-mini）でバッチセンチメント解析して ai_scores に格納するロジックを実装。
      - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）を提供。
      - バッチサイズ、記事・文字数上限、リトライ（429/ネットワーク/5xx に対する指数バックオフ）などを考慮。
      - 出力バリデーション、スコアの ±1.0 クリップ、部分失敗時の既存スコア保護（対象コードのみ置換）を設計。

### Changed
- プロジェクト初期の設計決定
  - 分析用 DB とトランザクション用 DB を明確に分離（DuckDB と SQLite）。
  - Paper Trading 環境は本番 DB と完全に分離（PAPER_TRADING_SQLITE_PATH を使用）。
  - .env 読み込みはプロジェクトルート検出に基づき実行（CWD に依存しない）。

### Fixed / Robustness
- 設定・環境変数の堅牢化
  - .env のクォート・エスケープ・コメント処理を実装し、意図しない切り取りや誤読を防止。
  - 自動読み込み時に OS 環境変数を上書きしない保護機構を追加。
  - 各種環境変数の値検証（KABUSYS_ENV, PAPER_FILL_MODE, LOG_LEVEL 等）。無効値時に明確なエラーを送出。
- 実行時の堅牢性向上
  - run_monitoring のポーリング間隔 MONITOR_POLL_INTERVAL の入力検証とフォールバック（不正値時に警告）。
  - run_monitoring / run_execution で DB コネクションを finally ブロックで必ずクローズ。
  - process_priority 設定時に権限不足や未対応 OS を警告でスキップするフェイルセーフを実装。
- ポートフォリオロジックのフォールバック
  - 全スコア 0 の場合、score_weights が等金額配分へフォールバックして安全策を講じる。
  - price 欠損（0.0）時のログとスキップで不正発注を防止する注意喚起コメントを実装。
- レポート / 分析の頑健性
  - tools.paper_verification_report はテーブル不存在（OperationalError）を捕捉し、空データ扱いでレポートを継続表示。
  - P95 算出や平均・最大レイテンシの None 対応を実装。

### Security
- OpenAI API キーの扱いは引数優先、その後環境変数 OPENAI_API_KEY を参照。未設定時は明確に ValueError を送出。

### Notes / Known limitations
- news_nlp モジュールは設計上の基本処理を備えるが、実際の API 呼び出し周りや DuckDB 書き込みのトランザクション周りの完全な例外処理は今後拡充の余地あり（コードは途中まで示されている）。
- position_sizing は全銘柄共通の lot_size を想定。将来的に銘柄別 lot_size を導入するための TODO コメントあり。
- apply_sector_cap のエクスポージャー計算は price が欠損している場合に過少見積になりうる旨のコメントがあり、将来的にフォールバック価格参照を検討する設計。

---

（以降のリリースでは、モジュールごとのテスト追加、API エラー時のより詳細なリトライポリシー、DuckDB/SQLite のマイグレーション管理強化、監視アラート・通知機能（LINE 等）の実装等を計画してください。）