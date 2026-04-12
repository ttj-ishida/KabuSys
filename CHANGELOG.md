# CHANGELOG

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」形式に準拠しています。  

現在のリリース日付は 2026-04-12 です（コードベースから推測して作成）。

## [Unreleased]
- (なし)

## [0.1.0] - 2026-04-12

### Added
- 基本的な日本株自動売買システム「KabuSys」の初期実装を追加。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。

- 実行・監視用エントリポイントを追加。
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。  
    - 環境変数 `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を利用し、paper trading 用に分離された SQLite DB（デフォルト: `data/paper_trading.db`）へ記録する実装。
    - broker/リポジトリ/リスク管理/オーダーマネージャ/再調整（Reconciler）等の依存コンポーネントを組み立ててセッション実行。
    - duckdb を利用した分析用コネクションを渡す設計。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。  
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト: 60 秒）。不正な値（0 以下・非整数）はデフォルトにフォールバックして警告を出す。
    - 監視処理は環境に関わらず本番用の sqlite_path を使用する（監視 DB の一貫性確保）。
    - 起動時にプロセス優先度を "high" に設定する処理を組み込む。

- 設定管理モジュール（kabusys.config）を追加。
  - .env / .env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml）を提供。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効にできる。
  - 環境変数読み取り用の Settings クラスを提供（多くの設定プロパティをラップ）。
  - 必須変数未設定時には `_require` が ValueError を投げることで早期検出。
  - 各種デフォルトパス（`DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH` など）を定義。
  - `PAPER_FILL_MODE` と `KABUSYS_ENV`、`LOG_LEVEL` 等に対するバリデーション実装（不正値は ValueError）。

- 監視 / モニタリング関連
  - monitoring_db 初期化の呼び出しを実装（冪等なテーブル作成）。
  - SystemMonitor と監視用 DB（SQLite）・DuckDB 接続の統合。

- ポートフォリオ構築関連（純粋関数群、DB 参照なし）
  - portfolio_builder:
    - buy シグナルの候補選定（スコア降順、同点は signal_rank でタイブレーク）。
    - 等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。全スコアが 0 の場合は等金額にフォールバックして警告を出す。
  - risk_adjustment:
    - セクター集中制限適用関数 apply_sector_cap（既存保有を考慮して当日新規候補を除外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear に対応、未知はフォールバックして警告）。
  - position_sizing:
    - 複数の配分方式（risk_based / equal / score）に対応した発注株数計算。
    - lot_size（単元株）丸め、単銘柄上限・全体上限（aggregate cap）スケールダウンロジック、手数料・スリッページ見積りの cost_buffer 反映。
    - aggregate キャップ適用時の端数再配分ロジック（残差に基づく lot 単位での追加配分）を実装。
    - 価格欠損や price<=0 の取り扱いでスキップする安全処理を追加。
    - TODO: 銘柄別 lot_size や価格フォールバックの注記あり（将来的拡張）。

- 研究 / ファクター計算モジュール
  - research.factor_research:
    - Momentum, Volatility, Value ファクター計算関数 (calc_momentum, calc_volatility, calc_value) を DuckDB SQL で実装。
    - 各種ウィンドウ長（1M/3M/6M、MA200、ATR20 等）の定義。
    - データ不足時の None の扱い、集計の SQL ウィンドウ関数利用により効率的に計算。
  - research.feature_exploration:
    - 将来リターン計算 calc_forward_returns（柔軟な horizons 対応、入力検証あり）。
    - スピアマンランク相関（IC）計算 calc_ic（ランク作成時に ties は平均ランクで処理）。
    - factor_summary（count/mean/std/min/max/median）などの統計ユーティリティ。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- AI ニュース NLP（ニュースセンチメントスコアリング）
  - ai.news_nlp:
    - raw_news と news_symbols を集約して OpenAI API（モデル: gpt-4o-mini, JSON モード想定）へバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む実装。
    - バッチサイズ、トークン制御（記事数・最大文字数トリム）、最大リトライ回数・指数バックオフ、429/5xx/ネットワークエラーへの耐性を実装。
    - レスポンスのバリデーションとスコアの ±1.0 クリッピング、部分失敗時の既存スコア保護（対象 code のみ削除→挿入）を実装。
    - target_date ベースのニュースウィンドウ計算を提供（ルックアヘッドバイアス防止のため datetime.today() を参照しない設計）。
    - OPENAI_API_KEY が未設定のときは ValueError を送出する明示的エラーチェック。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 用 SQLite DB から稼働率、注文成功率、送信率、P95 レイテンシ等を集計して検証レポートを標準出力に出力する CLI を追加。
    - 日付範囲指定（--from / --to）、--db オプション、デフォルト DB パス `data/paper_trading.db` をサポート。
    - Pass/Fail 基準を定義（稼働率 99% など）し、欠損データに対するフォールバックを考慮。
    - P95 の算出ユーティリティや各種クエリにおける NULL/データ不足時の安全ハンドリングを実装。

- ユーティリティ
  - utils.process_priority:
    - Windows / POSIX(Linux/Darwin/FreeBSD) を意識したプロセス優先度設定（nice / HIGH_PRIORITY_CLASS 等）の抽象化ユーティリティを追加。
    - CPU Affinity を最初の N コアに固定する set_cpu_affinity を提供（アクセス権限がない場合は警告してスキップ）。
    - 許容レベル: "high" / "normal" / "low"。無効な値は ValueError。

### Changed
- なし（初期リリースのため新規追加のみ）。

### Fixed
- なし（初期リリース）。

### Removed
- なし。

### Deprecated
- なし。

### Security
- OpenAI API キーの未設定時に早期にエラーを出すことで誤った API 呼び出しや鍵漏洩リスクを低減する設計を採用。

### Notes / Known issues / TODO
- .env 自動読み込み:
  - プロジェクトルート検出に .git または pyproject.toml を使用するため、配布パッケージ化後にプロジェクトルートが見つからない場合は自動ロードがスキップされる点に注意。
  - 自動ロードを無効にするための `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。
- process_priority / set_cpu_affinity:
  - 実行環境の権限やプラットフォーム差により設定が失敗する可能性がある（失敗時は警告ログでスキップ）。
- position_sizing / apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過小見積りされる懸念あり。将来的に前日終値や取得原価をフォールバック価格として導入することを想定（TODO コメントあり）。
- DuckDB の executemany に関する注意:
  - ai.news_nlp の実装方針コメントで DuckDB 0.10 の executemany の制約を意識した実装が示されている（params が空でないことを事前確認する等）。
- Monitoring:
  - run_monitoring は監視 DB に本番 sqlite_path を使用する（意図的な設計）。paper_trading 環境でも監視は本番 DB に接続する点に注意。
- Paper Trading:
  - run_execution は paper_trading 環境で DB を分離するが、本番 DB と完全に隔離されていることを運用で確認すること。

---

今後のリリースでは、以下のような改善項目が想定されます:
- 銘柄別 lot_size のサポート、価格フォールバック実装
- テストカバレッジ拡充と CI ワークフロー化
- ai.news_nlp のエラーハンドリング強化（部分失敗リトライ戦略の拡張）
- DuckDB ベースのバッチ処理最適化

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートがある場合はそちらに合わせて調整してください。）