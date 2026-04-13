# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。  
このプロジェクトは Keep a Changelog の形式に従います。  

フォーマット:
- 変更はカテゴリー別にまとめています（Added / Changed / Fixed / Security / …）。
- バージョンごとにリリース日を記載します。

## [0.1.0] - 2026-04-13

### Added
- 基本リリース。以下の主要コンポーネントを追加。
  - 起動スクリプト
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60秒）。0 以下の値はデフォルトにフォールバックする。
      - 監視は環境にかかわらず本番の sqlite_path を使用する仕様。
      - 起動時にプロセス優先度を "high" に設定。
    - src/kabusys/run_execution.py
      - ExecutionEngine 起動スクリプトを追加。
      - `KABUSYS_ENV=paper_trading` のときは paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
      - 起動時にプロセス優先度を "high" に設定。
      - ブローカークライアントのファクトリ経由で実環境 / モックを切替え。
      - 実行エンジン起動時に監視テーブルの存在を保証する初期化（冪等な init_monitoring_db 呼び出し）。
  - 設定管理
    - src/kabusys/config.py
      - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
      - 読み込み優先順位: OS 環境変数 ＞ .env.local ＞ .env。
      - 自動ロード無効化用フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
      - .env パーサ（エクスポート形式、引用符、エスケープ、インラインコメントなどに対応）。
      - Settings クラス：各種環境変数プロパティを提供（検証付き）。
        - 例: `PAPER_FILL_MODE`（instant|partial|never|reject の検証）、`KABUSYS_ENV`（development/paper_trading/live 検証）、`LOG_LEVEL` 検証など。
        - データベースや PID/kill flag のパス、閾値設定などのプロパティを追加。
  - ユーティリティ
    - src/kabusys/utils/process_priority.py
      - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収したプロセス優先度設定を実装。
      - CPU affinity を最初の N コアに固定する set_cpu_affinity 関数を追加。
      - 権限不足や未サポート環境では安全にスキップする設計。
  - ポートフォリオ構築（純粋関数群）
    - src/kabusys/portfolio/*
      - portfolio_builder.py: 候補選定（select_candidates）、等配分・スコア配分（calc_equal_weights, calc_score_weights）。
      - risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジーム乗数（calc_regime_multiplier）。
      - position_sizing.py: position size 計算（risk_based / equal / score）、単元株丸め、aggregate cap スケーリング、cost_buffer 考慮。
      - 設計方針として DB 非依存（メモリ内計算の純粋関数）を採用。
  - リサーチ / ファクター計算
    - src/kabusys/research/*
      - factor_research.py: Momentum / Volatility / Value のファクター計算関数。DuckDB を用いた SQL ベースの実装。
      - feature_exploration.py: 将来リターン計算、IC（Spearman ρ）計算、rank・統計サマリー等の実装。外部ライブラリに依存せず標準ライブラリのみで実装。
      - DuckDB 接続を受け取り prices_daily / raw_financials テーブルから計算する設計。
  - AI ニュース NLP スコアリング
    - src/kabusys/ai/news_nlp.py
      - raw_news に対して OpenAI API (gpt-4o-mini) を用いたセンチメントスコアリングを実装。
      - 銘柄ごとに記事を集約し、最大バッチサイズ（20 銘柄）で API 呼び出し。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対するエクスポネンシャルバックオフを実装（リトライ上限あり）。
      - レスポンスのバリデーション、スコアの ±1.0 クリップ、部分失敗時の DB 更新戦略（対象コードのみ置換）を採用。
      - ニュース集計ウィンドウ計算（JST基準 → UTC 変換）機能を提供。
  - ツール
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading の検証レポート生成スクリプトを追加。コマンドライン実行可能（期間指定オプションあり）。
      - システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（avg / max / P95）等を算出。
      - 判定基準（閾値）を定義（例: 稼働率 >= 99.0%、P95 <= 200 ms など）。
      - DB が存在しない場合のエラーメッセージを整備。

### Changed
- （初期リリースのため履歴上の変更なし）

### Fixed / Improvements
- .env パーサの堅牢化
  - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを正しく処理するように実装。
  - 空行やコメント行をスキップ。
  - 読み込み失敗時には警告を出し、安全に続行する。
- calc_score_weights: 全銘柄スコアが 0.0 の場合に等配分へフォールバックし警告を出力するよう改善。
- apply_sector_cap: "unknown" セクター（sector_map に未登録の銘柄）はセクター上限チェックから除外する。
- position_sizing:
  - 単元株（lot_size）で丸める処理、aggregate cap 超過時のスケーリングと残差に基づく再配分ロジックを実装。
  - price が欠損または 0 の場合はスキップして安全に動作。
- research モジュール:
  - ファクター / 将来リターン計算は不足データ時に None を返す設計で堅牢性を確保。
  - calc_forward_returns の horizons 入力検証を追加（正の整数かつ <= 252）。

### Security
- OpenAI API キーは引数または環境変数 `OPENAI_API_KEY` から取得。未設定時は ValueError を送出して明示的にエラーにする設計（誤ったキーでの無自覚な送信を防止）。
- news_nlp の設計においてルックアヘッドバイアス防止のために datetime.today() / date.today() を直接参照しない実装方針を採用（target_date を明示的に受け取る）。

### Notes / Known limitations
- run_monitoring は監視用 DB に本番 sqlite_path を使用するため、paper_trading 環境でも監視 DB は共有される点に留意してください（意図的な仕様）。
- process_priority の設定は権限が必要であり、失敗した場合は警告を出してスキップします。
- position_sizing の price 欠損時のフォールバック（前日終値や取得原価等）は TODO コメントとして残してあり、将来的な拡張を想定しています。
- ai/news_nlp の一部の実装（DB 書き込み直前の完全な成功/部分成功ハンドリングや詳細なエラーロギング）は安全性を考慮し設計されていますが、実環境での追加検証を推奨します。

---

今後のリリースでは、ユニットテスト、トレーシング（分散トレーシング/メトリクス）、および更なるエラー耐性の向上（リトライ戦略の微調整や API コスト最適化）を予定しています。