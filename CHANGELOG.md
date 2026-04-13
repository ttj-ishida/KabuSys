# Changelog

すべての重要な変更は Keep a Changelog の形式に準拠して記載しています。

## 0.1.0 - 2026-04-13

### Added
- 全体
  - 初回リリース。自動売買システム "KabuSys" の基本モジュール群を追加。
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として設定。

- 実行 / 監視
  - 実行用エントリポイント:
    - src/kabusys/run_execution.py
      - ExecutionEngine を起動する CLI スクリプトを追加。
      - 起動時にプロセス優先度を "high" に設定（set_process_priority を呼び出し）。
      - 環境が `paper_trading` の場合、paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
      - BrokerClientFactory を用いて環境に応じたブローカークライアントを生成し、OrderRepository, OrderManager, RiskManager, Reconciler 等を組み立ててセッションを実行。
  - 監視用エントリポイント:
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループを起動するスクリプトを追加。
      - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト: 60 秒）。不正な値や 0 以下はデフォルトへフォールバックして警告を出力。
      - 監視データベースは実稼働 DB パス（Settings.sqlite_path）を使用して初期化（KABUSYS_ENV に関わらず本番 sqlite_path を参照）。
      - 起動時にプロセス優先度を "high" に設定。

- 設定 / 環境読み込み
  - src/kabusys/config.py
    - .env 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - 読み込み順序: OS 環境 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - .env パーサを実装し、シングル/ダブルクォート、export 形式、インラインコメント等に対応。
    - Settings クラスを導入し各種設定プロパティを提供:
      - J-Quants / kabu / LINE API 関連の設定取得。
      - duckdb/sqlite パス、paper_trading 用 sqlite パスの取得。
      - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject" のみ許容）。
      - 監視関連（pid ファイル/kill flag 等）や閾値（CPU/MEM/DISK）、
      - LOG_LEVEL / KABUSYS_ENV 値の検証と補助プロパティ（is_live / is_paper / is_dev）。

- ポートフォリオ構築
  - src/kabusys/portfolio/*
    - portfolio_builder:
      - シグナルのランキング選定（select_candidates）。
      - 等金額配分(calc_equal_weights)・スコア重み配分(calc_score_weights)、スコア全 0 の場合は等分配へフォールバック。
    - risk_adjustment:
      - セクター集中制限を適用する apply_sector_cap（売却予定銘柄を除外、"unknown" セクターは上限除外）。
      - 市場レジームに応じた乗数を返す calc_regime_multiplier（bull/neutral/bear のマッピング、未知値は警告の上 1.0 フォールバック）。
    - position_sizing:
      - position サイズ算出ロジック calc_position_sizes を実装（risk_based / equal / score の方式に対応）。
      - 単元（lot_size）、手数料・スリッページ見積り係数(cost_buffer) を考慮した aggregate cap（スケールダウン）実装。
      - 単元丸め、1銘柄上限、available_cash による集約上限、価格欠損時の扱い、残余キャッシュを用いた再配分ロジックを実装。

- 研究用モジュール
  - src/kabusys/research/*
    - factor_research:
      - モメンタム (calc_momentum)、ボラティリティ/流動性 (calc_volatility)、バリュー (calc_value) のファクター計算を追加。
      - DuckDB 接続を受け取り SQL ベースで高速に集計・ウィンドウ関数を用いて計算。
    - feature_exploration:
      - 将来リターン計算 calc_forward_returns（複数ホライズン対応）。
      - IC（Information Coefficient）計算 calc_ic（Spearman のランク相関）、およびランク付けユーティリティ rank。
      - ファクター統計サマリ factor_summary（count/mean/std/min/max/median）。
    - research パッケージ __init__ で主要関数と zscore_normalize を公開。

- AI / ニュース NLP
  - src/kabusys/ai/news_nlp.py
    - raw_news を OpenAI API（gpt-4o-mini）でセンチメント解析し、銘柄ごとのスコアを ai_scores テーブルへ書き込む機能を実装。
    - 処理フロー: ニュースウィンドウ（JST ベースを UTC に変換）、記事集約、銘柄ごとのトリミング（最大記事数と最大文字数）、バッチ送信（最大 20 銘柄/リクエスト）、エラーハンドリング（429/ネットワーク/5xx のリトライ）、レスポンス検証、スコアの ±1.0 クリップ、部分成功時の置換戦略（対象コードのみ置き換え）。
    - OpenAI API キー未設定時は ValueError を送出。
    - API クライアントに OpenAI パッケージを使用。

- ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - レポート指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数 等。
    - CLI 引数で期間（--from/--to）および DB パス（--db）を指定可能。PAPER_TRADING_SQLITE_PATH 環境変数で代替可。
    - デフォルト閾値を定義し（稼働率 99% 等）、Pass/Fail 判定を出力。
    - DB が存在しない場合のエラーメッセージを出力。

- ユーティリティ
  - src/kabusys/utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows/POSIX を吸収）。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未サポート OS の場合は警告ログを出して安全にスキップ。

### Changed
- 環境変数読み込みの挙動
  - .env パーサがより寛容かつ正確にクォート・エスケープ・コメントを処理するようになり、export 形式にも対応。
  - 自動ロードがプロジェクトルートに依存するようになり、配布後も CWD に依存せずに動作する設計に変更。

- DB 初期化
  - run_execution/run_monitoring 起動時に monitoring 用テーブルの初期化（init_monitoring_db）を呼ぶことで、監視テーブルが存在することを冪等的に保証。

### Fixed
- 安全性 / ロバスト性の向上
  - MONITOR_POLL_INTERVAL の不正値（非整数、0 以下）を検出して警告を出し、デフォルト値にフォールバックする処理を追加（run_monitoring）。
  - position_sizing 等で価格が取得できない（None/0）場合は対象から除外することでゼロ除算や不正な発注量算出を回避。
  - AI スコアリングで API キーが未設定の場合に明示的にエラーを出すようにして、無駄な API 呼び出しを防止。

### Notes / Breaking changes
- Settings のいくつかのプロパティは入力値検証を行います（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。これらが不正な値のまま環境変数に設定されていると起動時に ValueError を送出して停止するため、デプロイ時は .env の内容を確認してください。
- run_monitoring は監視データ用に常に Settings.sqlite_path を使用します。開発環境で監視 DB を分離したい場合は sqlite_path を明示的に変更してください。

### Security
- なし（本リリース時点で特記すべきセキュリティ修正はありません）。

もしリリースノートに追加したい詳細（例: 各関数の入力例、既知の制限、将来予定の改善点など）があれば教えてください。必要に応じてセクションを追記します。