# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。

## [0.1.0] - 2026-04-13

### 追加 (Added)
- 基本リリースとして以下の主要コンポーネントを導入しました。
  - 実行系
    - run_execution.py: ExecutionEngine の起動エントリポイント。環境に応じて Paper/Live を切り替え、BrokerClient を生成してセッションを実行します。
    - Paper Trading 環境では専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離します。
  - 監視系
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視処理は環境にかかわらず本番 sqlite_path を使用します。
  - 設定管理
    - config.Settings: 環境変数/.env/.env.local の読み込みロジックを導入。プロジェクトルート自動検出(.git または pyproject.toml)に基づく .env 自動読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。多数の設定プロパティ（DB パス、PID / kill-flag パス、閾値、環境種別判定等）を提供。
    - .env パーサーはクォート・エスケープ・export 形式・インラインコメントに対応。
  - ポートフォリオ構築 (portfolio)
    - portfolio_builder: シグナルのソート/候補選定 (select_candidates)、等配分・スコア加重の重み計算 (calc_equal_weights, calc_score_weights) を提供。
    - risk_adjustment: セクター上限フィルタ (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。
    - position_sizing: 発注株数算出ロジック (calc_position_sizes)。risk_based / equal / score の割当方式、単元株丸め (lot_size)、コストバッファ、aggregate cap によるスケールダウンと端数処理を含む。
  - 研究・因子計算 (research)
    - factor_research: DuckDB を直接参照するファクター計算を実装（calc_momentum, calc_volatility, calc_value）。200日移動平均、ATR、出来高指標、PER/ROE 等を算出。
    - feature_exploration: 将来リターン計算 (calc_forward_returns)、IC（Spearman rank）算出 (calc_ic)、ファクター統計サマリ (factor_summary)、ランク関数 (rank) を追加。外部ライブラリに依存せずに実装。
  - AI ニュース NLP (ai)
    - news_nlp.score_news: raw_news を OpenAI（デフォルトモデル gpt-4o-mini）でバッチ評価し、銘柄ごとの ai_scores を書き込む機能を追加。バッチ処理、トークン肥大化対策（記事数・文字数制限）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアクリップ（±1.0）を実装。
  - ツール
    - tools.paper_verification_report: Paper Trading 用の検証レポート生成 CLI を追加。期間指定（--from / --to / --db）に対応し、稼働率・注文成功率・送信率・レイテンシ（P95）などを算出して判定（PASS/FAIL）します。
  - ユーティリティ
    - utils.process_priority: プラットフォームに依存しないプロセス優先度設定 (set_process_priority) と CPU affinity 設定 (set_cpu_affinity) を提供。Windows / POSIX の差分を吸収し、権限不足時は警告を出してスキップします。

### 変更 (Changed)
- 環境・DB の扱い
  - 監視プロセスは環境変数 KABUSYS_ENV に関係なく常に本番 sqlite_path を使用するように明示（run_monitoring.py）。
  - 実行プロセスは KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して paper_trading DB と完全に分離されるように実装（run_execution.py）。
- Settings: 細かな検証追加
  - env / log_level / paper_fill_mode に対する入力検証を追加。不正な値は ValueError を送出します。
  - PAPER_FILL_MODE の有効値 ("instant", "partial", "never", "reject") を厳格に検査。
- position_sizing: 集計上限超過時のスケールダウンアルゴリズムを導入（cost_buffer を考慮した保守的見積り、lot 単位での追加配分）し、端数の取り扱いを安定化。
- ai.news_nlp:
  - ニュース対象ウィンドウの計算とバッチ処理、部分失敗時に既存スコアを保護する部分置換戦略（対象コードに絞って DELETE→INSERT）を導入。
- research モジュール: DuckDB SQL を活用した一括取得によりパフォーマンスを考慮した実装に変更。

### 修正 (Fixed)
- .env 読み込みの堅牢化
  - ファイル読み込み失敗時に warnings.warn で通知して処理を継続するように改善。
  - export KEY=val 形式、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなど様々な .env 形式に対応。
- process_priority: 未対応 OS や権限不足での例外をキャッチして警告を出すようにし、プロセスがクラッシュしないように修正。
- paper_verification_report:
  - P95 の計算およびレポート出力の整形を改善し、DB が存在しない場合のエラーメッセージを明確化。
  - DB 内のテーブルが存在しない場合に sqlite3.OperationalError を捕捉してフェイルセーフに動作するようにした。

### 互換性に関する注意 (Breaking Changes / Notes)
- run_monitoring.py の挙動:
  - 監視は常に本番用 sqlite_path を参照します。もし監視を paper_trading 用 DB に向けたい場合は手動で SQLITE_PATH を差し替える必要があります。
- 環境変数自動読み込み:
  - デフォルトでプロジェクトルートの .env / .env.local を自動でロードします。自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Settings の検証追加により、不正な環境変数値がある場合に起動時に例外を投げる可能性があります。デプロイ前に .env の値を確認してください。

### セキュリティ (Security)
- OpenAI API キーは環境変数 OPENAI_API_KEY または score_news の api_key 引数から取得します。キーが未設定の場合は ValueError を送出して処理を停止します（明示的な失敗によりキー漏洩リスクを低減）。

---

今後の予定/未解決事項（参考）
- position_sizing: 銘柄別 lot_size をサポートするための拡張（stocks マスタの lot_map 受け取り）。
- apply_sector_cap: price 欠損時のフォールバックロジック（前日終値や取得原価）の追加検討。
- ai.news_nlp: API 結果の更なる型検証・スキーマ検証強化や非同期化によるスループット改善。

ご不明点や追記希望があればお知らせください。