# Changelog

すべての重要な変更は Keep a Changelog の慣例に従って記載します。  
日付はリリース日を示します。更新履歴は機能追加・変更・修正を中心にまとめています。

最新: 0.1.0 — 2026-04-17

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 全体
  - 初回公開リリース。日本株自動売買システム "kabusys" のコア機能群を実装。
  - DuckDB / SQLite を併用したデータ処理基盤を提供。DuckDB は時系列・分析処理、SQLite は監視・実行ログ用に想定。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。スレッドでエンジンを実行し、stop フラグ（data/stop_requested.flag）を検知して安全に停止可能。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてエンジンを構築。
    - RiskManager に適用されるデフォルト構成（max_position_pct 等）を定義し、broker.get_available_cash() を初期ポートフォリオ値として使用。
    - 起動直後にプロセス優先度を "high" に設定する処理を追加（utils.process_priority.set_process_priority を使用）。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視処理は環境にかかわらず本番用 sqlite_path（Settings.sqlite_path）を使用して初期化。
    - 停止フラグ（data/stop_requested.flag）でループを終了、KeyboardInterrupt での終了にも対応。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順序を明確化（OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - シンプルかつ堅牢な .env パーサを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応）。
    - Settings クラスを提供し、各種環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, PAPER_FILL_MODE, DB パス類, 監視しきい値 等）をプロパティとして取得・検証。
    - 環境値の検証ロジックを実装（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の有効値チェックなど）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成 CLI を追加。指定期間のシステム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数などを集計し PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ組立、DB 存在チェック、SQL 実行時の安全ハンドリング（テーブルがない場合のフォールバック）を実装。
    - CLI 引数: --from / --to（YYYY-MM-DD）、--db（データベースパス、環境変数での指定にも対応）。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - シグナル選定（スコア降順・タイブレークルール）、等金額配分、スコア加重配分（スコア総和が 0 の場合は等金額にフォールバック）を実装。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算ロジック（risk_based, equal, score）を実装。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash によるスケールダウン）、cost_buffer を考慮した保守的な推定を実装。
    - スケールダウン時の端数処理（lot 単位で残差順に追加配分）を実装し再現性を考慮。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有のセクターエクスポージャー算出、上限超過セクターから候補を除外）。"unknown" セクターは除外対象外。
    - 市場レジームに対する投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear に対して 1.0/0.7/0.3、未知は警告後 1.0 フォールバック）。

- 研究（Research）
  - research/factor_research.py
    - モメンタム、ボラティリティ（ATR/出来高/出来高比率）、バリュー（PER/ROE）等のファクターを DuckDB 上の prices_daily / raw_financials を使って計算する関数を実装。
    - 各関数は target_date に対する銘柄別結果リストを返す（date, code を含む）。
    - 長期 MA / ATR 等の窓サイズとスキャン範囲に関する設計上のバッファを導入（営業日→カレンダー日換算の安全余裕）。
  - research/feature_exploration.py
    - 将来リターン（複数ホライズン）の一括算出、IC（Spearman）計算、ランク付け（同順位は平均ランク）、ファクター統計サマリーを実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research/__init__.py
    - 主要 API をエクスポート（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize）。

- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news を OpenAI API (gpt-4o-mini) でバッチ分析して銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む機能を実装（設計方針・処理フローを実装）。
    - ニュース集計ウィンドウ（JST 指定 → UTC 変換）の算出ユーティリティを実装。
    - API キー解決、バッチサイズ・トークン肥大対策（記事数/文字数のトリム）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）などを備えた堅牢設計。
    - レスポンスのバリデーション、スコアのクリップ、DB 書き込み時の部分置換（特定コードのみ更新）などの安全策を導入。

- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームなプロセス優先度設定ユーティリティを追加（Windows / POSIX に差分吸収）。nice 値・Windows 優先度クラスをラップ。
    - CPU affinity 設定ユーティリティ（最初の N コアに固定）を実装。権限不足や未対応 API の場合は警告を出してフォールバック。

### 変更 (Changed)
- n/a（初回リリースのため変更履歴はありません）

### 修正 (Fixed)
- n/a（初回リリースのため修正履歴はありません）

### 削除 (Removed)
- n/a

### 非推奨 (Deprecated)
- n/a

### セキュリティ (Security)
- OpenAI API キーや機密情報は Settings / 環境変数経由で扱う設計。ローカル .env 自動読み込みは無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を用意。

---

注記:
- 本 CHANGELOG は与えられたコードベースから実装内容を推測して作成しています。実際の履歴や目的に応じて項目の追加・修正を行ってください。
- 今後のリリースでは Unreleased セクションを用い、機能追加・改善・バグ修正ごとにエントリを追記してください。