Keep a Changelog 準拠の CHANGELOG.md

すべての変更は主にコードベースの追加・実装をコードから推測して記載しています。実際のコミット履歴がある場合はそちらを優先してください。

以下はバージョン 0.1.0（初回リリース想定）としてのまとめです。

## [Unreleased]


## [0.1.0] - 2026-04-16
初回公開想定リリース。システム全体のコア機能（実行エンジン、監視、ポートフォリオ構築、リサーチ、ツール、ユーティリティ）が実装されています。

### 追加
- 全体
  - パッケージ初期バージョンを設定（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開用に主要モジュールをエクスポート（portfolio, execution, monitoring 等）。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor をポーリングで起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用するよう実装。
    - プロセス優先度を High に設定してから起動し、停止フラグ（data/stop_requested.flag）を検知して graceful shutdown。
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory を利用してブローカークライアントを作成（paper/live 切替対応を想定）。
    - ExecutionEngine を別スレッドで起動し、停止フラグを検知したら engine.stop() を呼び停止。
    - 実行用 PID ファイルサポート（data/execution.pid）。

- 設定管理
  - config.py
    - プロジェクトルートを .git または pyproject.toml から自動検出し、.env / .env.local を自動ロードする仕組みを実装（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサは export プレフィックス、引用符付き値（バックスラッシュエスケープ対応）、インラインコメント処理などに対応。
    - Settings クラスを通じて各種設定プロパティを提供（J-Quants / kabu / LINE / DB / 監視 / システム設定等）。
    - 設定のバリデーションを実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等の有効値チェック）。
    - デフォルト値と Path 型の展開を導入（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH など）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - CLI オプションで期間指定（--from, --to）や DB パス（--db）を指定可能。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、P95レイテンシ等の指標を集計・判定してレポート出力。
    - 判定基準（デフォルト）を設定：
      - 稼働率 >= 99.0%
      - 成立率 (fill rate) >= 90.0%
      - 送信率 (send rate) >= 95.0%
      - P95 レイテンシ <= 200 ms

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補を選択（タイブレークに signal_rank を使用）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア正規化配分を実装。全スコアが 0 の場合は等金額にフォールバック（WARNING）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中の上限チェックと候補の除外ロジックを実装（"unknown" セクターは除外の対象外）。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull/neutral/bear => 1.0/0.7/0.3）、未知レジームはフォールバックして 1.0。
  - portfolio/position_sizing.py
    - calc_position_sizes: 発注株数決定ロジックを実装（allocation_method: risk_based / equal / score）。
    - リスクベース算出、単元株丸め(lot_size)、1銘柄上限・投下資金上限、コストバッファ（cost_buffer）を考慮した aggregate scaling 実装。
    - 利用可能現金を超える場合のスケールダウンと端数処理（fractional remainders による lot 単位の追加配分）を実装。

- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離の計算（prices_daily を参照）。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（target_date 以前の最新財務データを使用）。
    - DuckDB を用いた SQL+ウィンドウ関数による実装。
  - research/feature_exploration.py
    - calc_forward_returns: 将来リターン（複数ホライズン）を計算。horizons 引数を受ける（デフォルト [1,5,21]）。
    - calc_ic / rank / factor_summary: スピアマンランク相関（IC）、ランク化、統計サマリー（count/mean/std/min/max/median）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）を使ってセンチメントスコアを生成し ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を計算して対象記事を抽出。
    - 1バッチ最大 20 銘柄、銘柄ごとに最大記事数 / 文字数でトリム（トークン肥大化対策）。
    - 429 / ネットワーク / タイムアウト / 5xx に対してエクスポネンシャルバックオフでリトライ（上限あり）。
    - レスポンスのバリデーションとスコアの ±1.0 でのクリッピング。
    - API キーの指定は引数 api_key または環境変数 OPENAI_API_KEY。
    - （実装途中でファイル末尾が切れている可能性あり。コードベース参照推奨）

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows と POSIX（Linux/Mac/FreeBSD）両対応でプロセス優先度を設定。アクセス権限エラー時は警告でスキップ。
    - set_cpu_affinity(cpu_count): カレントプロセスの CPU affinity を設定（None で未設定）。入力検証と権限エラーハンドリングあり。

### 変更
- 監視処理
  - 監視ループの挙動: check_once() 呼び出し時の例外は捕捉してログ出力し次回ポーリングへ継続（監視の耐障害性向上）。
  - モニタリング DB 初期化 (init_monitoring_db) を接続直後に冪等に実行してテーブル存在を保証。

- DB ハンドリング
  - Execution 起動時に paper_trading モードでは専用 SQLite を使用するよう分離（本番 DB との混同を防止）。

### 修正（推定・注意）
- .env 読み込みで OS 環境変数を保護するための protected 処理を追加（.env.local で OS 環境を上書きしない）。これはテスト・デプロイ環境での予期せぬ上書きを防止するための措置です。
- PAPER_FILL_MODE の入力値検証を追加（instant/partial/never/reject のみ許容）。不正な値は ValueError を送出。
- calc_score_weights で全スコアが 0 の場合のフォールバックロジックを追加（警告ログ出力）。

### 既知の制限 / 注意点
- ai/news_nlp.py の末尾が切れている（配布されたコードで途中終了している）。完全な実装の確認が必要。
- 一部関数の TODO が残存（例: apply_sector_cap 内の価格欠損時のフォールバック仕様、position_sizing の将来的な lot_size 拡張）。
- process_priority.set_cpu_affinity は OS の権限や psutil のサポート状況に依存し、失敗時は警告を出して処理をスキップする設計です。
- DuckDB を利用した SQL は prices_daily / raw_financials / raw_news 等のテーブル構造に依存します。DB スキーマの前提が満たされていることを確認してください。

### マイグレーション / 設定メモ
- .env 自動読み込みが有効（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。
- 主要な環境変数:
  - KABUSYS_ENV (development / paper_trading / live)
  - SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / DUCKDB_PATH
  - MONITOR_POLL_INTERVAL（監視ポーリング秒、デフォルト 60）
  - PAPER_FILL_MODE（paper_trading のフィル動作）
  - OPENAI_API_KEY（ai/news_nlp で使用）
  - LOG_LEVEL 等
- Paper Trading を使用する場合、PAPER_TRADING_SQLITE_PATH を適切に設定し、paper_trading 環境で起動してください（実行エンジンは paper 用 DB に記録）。

---

（注）上記は与えられたコード内容から推測して作成した CHANGELOG です。実際のコミット履歴やリリースノートが利用できる場合は、そちらを参照して差し替えてください。