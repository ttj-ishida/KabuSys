# Changelog

すべての重要な変更は Keep a Changelog 準拠で記載しています。  
このファイルはコードベースの内容から推測して作成しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- 今後のリリース用の未反映項目はここに記載します。

## [0.1.0] - 2026-04-16
初回リリース想定 — コア機能群を実装。監視・実行・ポートフォリオ構築・リサーチ・AIニューススコアリング等を含む。

### Added
- 全体
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として追加。
  - DuckDB / SQLite を組み合わせたローカル分析・監視用のデータアクセスパターンを導入。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は実行環境にかかわらず本番用の sqlite_path を使用して監視データを記録。
    - ディスク上の停止フラグファイル (`data/stop_requested.flag`) による安全停止機構を実装。
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用の専用 SQLite DB（デフォルト: `data/paper_trading.db`）を使用して本番 DB と分離。
    - BrokerClientFactory を使ったブローカークライアント生成、Engine の別スレッド起動、停止フラグ検出による安全停止を実装。
    - 実行用 PID 管理ファイル (`data/execution.pid`) のサポート。

- 設定/環境変数管理
  - `kabusys.config.Settings` を追加。環境変数や .env ファイルから設定を読み込み、各種プロパティを提供。
  - 自動 `.env` ロード機能を追加（プロジェクトルートを `.git` または `pyproject.toml` で検出）。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動読み込みを無効化可能。
  - `.env` パーサの強化：
    - `export KEY=val` 形式のサポート、引用符付き値のバックスラッシュエスケープ、インラインコメントの扱いなどに対応。
    - `override` / `protected` 機能で OS 環境変数を保護しつつ .env.local を上書きできる仕組みを導入。
  - 各種設定プロパティを実装（J-Quants、kabu API、LINE、DuckDB/SQLite パス、paper trading 関連、監視閾値、環境判定等）。
  - `paper_fill_mode` の検証（有効値: "instant" | "partial" | "never" | "reject"）を追加。

- 監視/データベース初期化
  - `monitoring_db.init_monitoring_db` を呼び出して監視テーブルが存在することを保証（冪等に初期化）。

- ユーティリティ
  - `kabusys.utils.process_priority` を追加。
    - Windows / POSIX（Linux, macOS, FreeBSD）でプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定するユーティリティを追加。
    - 実行環境による例外 (AccessDenied 等) はログ警告で安全にスキップする実装。

- ポートフォリオ構築
  - `kabusys.portfolio` モジュールを追加（純粋関数群）。
    - portfolio_builder:
      - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全体が 0 の場合は等金額へフォールバック。
    - risk_adjustment:
      - セクター集中制限適用 (apply_sector_cap) を実装。既存保有比率に基づく新規候補除外ロジックを提供。
      - 市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を追加（bull/neutral/bear）。
    - position_sizing:
      - 発注株数計算 (calc_position_sizes) を実装。allocation_method として "risk_based", "equal", "score" をサポート。
      - 単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金に応じたスケーリング）、cost_buffer を考慮した保守的見積りを実装。
      - スケールダウン時に残余キャッシュを fractional 残差順で付与する再現性のある配分ロジックを実装。

- リサーチ / ファクタ処理
  - `kabusys.research` を追加。DuckDB 接続を受け取り SQL ベースで計算する設計。
    - factor_research:
      - モメンタム (calc_momentum)、ボラティリティ (calc_volatility)、バリュー (calc_value) を実装。MA200, ATR20、出来高指標、PER/ROE などを計算。
      - データ不足時は None を返す安全設計。
    - feature_exploration:
      - 将来リターン計算 (calc_forward_returns)、IC（スピアマンランク相関）計算 (calc_ic)、ランク変換 (rank)、統計サマリー (factor_summary) を実装。
      - pandas 等に依存せず標準ライブラリで実装。

- AI / ニュース NLP
  - `kabusys.ai.news_nlp` を追加。
    - raw_news と news_symbols を集約して OpenAI API（gpt-4o-mini を想定）で銘柄ごとのセンチメントをスコアリングし、ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（JST 前日 15:00 〜 当日 08:30）に対応した window 計算を実装（calc_news_window）。
    - バッチ処理（最大 20 銘柄/コール）、トークン膨張対策（記事数上限 / 文字数上限）、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコア ±1.0 でのクリップを実装。
    - API キーは引数または環境変数 `OPENAI_API_KEY` から解決。未設定時はエラー。

- ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - Paper Trading 用 DB を読み、システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ (avg/max/P95) などを集計して標準出力にレポート出力。
    - P95 計算、期間フィルタ、各種閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を実装。
    - DB が存在しない場合のエラーメッセージ表示を実装。

### Changed
- なし（初回リリース想定。内部設計上の注意点はコード内コメントとして記述）。

### Fixed
- なし（初回リリース想定。エラー処理・フォールバックは各機能で実装済み）。

### Notes / Implementation details
- DuckDB を分析向けに採用：prices_daily / raw_financials / raw_news 等を SQL で効率的に集計する設計。
- SQLite は監視・paper trading ログ保存に利用。paper_trading モードでは専用 DB に分離して安全にテスト可能。
- 多くの関数は「DB 参照なし」または「DuckDB 接続を受ける」純粋関数として実装されており、ユニットテストや研究用途で再利用しやすい。
- プラットフォーム依存処理（プロセス優先度・CPU affinity）は例外時に警告を出して安全にスキップするため、異なる実行環境での堅牢性を確保。

---

将来のリリースでは以下のような改善が想定されます（コード内 TODO 等に基づく）：
- position_sizing の価格欠損時のフォールバック（前日終値や取得原価の利用）。
- 銘柄別単元株 (lot_size) を銘柄マスタから取得する拡張。
- ニュース NLP の部分的失敗時のトランザクション分割や再実行ロジック強化。
- その他、運用上の観測に基づく閾値やデフォルト設定のチューニング。

（この CHANGELOG はコード内容から推測して作成しています。実際のコミット履歴がある場合はそれに合わせて差し替えてください。）