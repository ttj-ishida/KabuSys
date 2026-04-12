# CHANGELOG

すべての変更は Keep a Changelog 形式に従って記載しています。  
日付: 2026-04-12

## [0.1.0] - 2026-04-12

初回リリース（ベース実装）。主要な機能追加と設計方針は以下の通りです。

### 追加 (Added)
- 全体
  - KabuSys パッケージの初版を追加。バージョンは `0.1.0`。
  - プロジェクトルートの自動検出機能を実装（.git または pyproject.toml を探索）。
  - .env ファイル読み込みユーティリティを実装（.env, .env.local の順序で読み込み）。既存 OS 環境変数は保護される（protected 機構）。
  - 自動 .env ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。

- 設定管理 (kabusys.config.Settings)
  - 環境変数からの設定取得をカプセル化した `Settings` クラスを実装。
  - 各種設定プロパティを提供: J-Quants / kabu API トークン、LINE トークン、DB パス、PID/KILL フラグパス、監視閾値、環境判定（development / paper_trading / live）など。
  - 入力検証を導入（例: `KABUSYS_ENV` / `LOG_LEVEL` の許容値検査、`PAPER_FILL_MODE` の許容値検査）。不正な値は `ValueError` を送出。

- 実行系 / 監視ランナー
  - `run_execution.py`: ExecutionEngine の起動スクリプトを追加。`KABUSYS_ENV=paper_trading` の場合は paper_trading 専用 SQLite DB を使用し、MockBrokerClient により本番 DB と分離して動作する設計。
  - `run_monitoring.py`: SystemMonitor のポーリングループ起動スクリプトを追加。環境にかかわらず監視は本番の sqlite_path を使用する旨を明記。
  - 両スクリプトとも起動時にプロセス優先度を High に設定（`set_process_priority("high")` を呼び出し）。

- DB 初期化
  - 監視用 DB 初期化呼び出し (`init_monitoring_db`) を実行前に呼ぶことで監視テーブルの存在を保証（冪等）。

- ユーティリティ (kabusys.utils.process_priority)
  - プロセス優先度設定ユーティリティを実装（Windows / POSIX の差分を吸収）。
  - CPU affinity 固定機能 `set_cpu_affinity` を追加。
  - 権限制約や未対応プラットフォームに対し安全にフォールバックして警告を出す設計。

- ポートフォリオ構築 (kabusys.portfolio)
  - 候補選定・重み計算: `select_candidates`, `calc_equal_weights`, `calc_score_weights` を実装（スコア降順、同点タイブレーク等の仕様あり）。
  - セクター集中制限・レジーム乗数: `apply_sector_cap`, `calc_regime_multiplier` を実装（unknown セクターは上限適用除外、レジームに応じた資金乗数）。
  - 株数決定・ラウンド・リスク制限: `calc_position_sizes` を実装（risk_based / equal / score の割当方式、lot_size による丸め、aggregate cap によるスケーリング、cost_buffer 反映、スケールダウン時の端数配分ロジック）。

- リサーチ / ファクター算出 (kabusys.research)
  - ファクター計算: `calc_momentum`, `calc_volatility`, `calc_value` を実装（DuckDB 接続を受け prices_daily / raw_financials を参照）。
    - Momentum: 1M/3M/6M リターン、MA200 乖離率（必要データ不足時は None）。
    - Volatility: ATR20, ATR/price, 20日平均売買代金、出来高比率（欠損値の取り扱いに注意）。
    - Value: PER, ROE（target_date 以前の最新財務データを使用）。
  - 特徴量探索: 将来リターン計算 `calc_forward_returns`（任意ホライズン対応）、IC 計算 `calc_ic`（Spearman ランク相関、有効レコード 3 未満で None）、統計要約 `factor_summary`、ランク変換 `rank` を実装。
  - 実装方針として外部ライブラリ未依存（標準ライブラリ + DuckDB）の設計を採用。

- AI ニューススコアリング (kabusys.ai.news_nlp)
  - OpenAI (gpt-4o-mini) を用いたニュースセンチメントスコアリングを実装。
  - 処理フロー: 対象タイムウィンドウの算出、raw_news と news_symbols の集約、1チャンクあたり最大 20 銘柄で API 呼び出し、JSON Mode + 厳密なレスポンス検証、スコアを ±1.0 にクリップ、取得後 ai_scores テーブルへ銘柄ごとに置換（DELETE→INSERT の手法で部分失敗耐性）。
  - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ（上限あり）。
  - OpenAI API キーは引数または環境変数 `OPENAI_API_KEY` から解決。未設定の場合は `ValueError`。

- ツール (kabusys.tools.paper_verification_report)
  - Paper Trading 検証レポート生成スクリプトを追加（CLI 実行可能）。
  - 指標: 稼働率、注文成功率(Fill Rate)、送信率(Send Rate)、リスク却下数、API レイテンシ（avg/max/P95）。
  - P95 計算実装、期間フィルタ（ISO8601 UTC 文字列での比較）、出力フォーマットと簡易 PASS/FAIL 判定を実装。
  - デフォルト DB パスは `data/paper_trading.db`。CLI オプション `--from`, `--to`, `--db` をサポート。

### 変更 (Changed)
- なし（初回リリースのため既存からの変更はありません）。

### 修正 (Fixed)
- なし（初回リリース）。

### 注意事項 / 実装上の考慮点（ドキュメント的メモ）
- .env パーサはクォート内のバックスラッシュエスケープやインラインコメントの扱いを考慮した実装。`export KEY=val` 形式にも対応。
- .env の上書きルール:
  - .env は OS 環境変数を優先（override=False）で読み込む。
  - .env.local は override=True のため OS 環境変数を保護しつつ既定値を上書き可能。
- Settings の一部プロパティは不正値で `ValueError` を投げるため、起動時に環境変数の検証エラーが発生する可能性があります（例: `PAPER_FILL_MODE`, `KABUSYS_ENV`, `LOG_LEVEL`）。
- `run_monitoring.py` のポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバックして警告を出す。
- 監視は常に Settings の本番 sqlite_path を使用する（監視 DB は環境に依存しない扱い）。
- `run_execution.py` は paper_trading 環境時に paper 専用 DB を使用し、本番 DB と完全分離することを明示的に行っている。
- process priority / cpu affinity の設定はプラットフォームと権限に依存するため、失敗時は警告を出して続行するフェイルセーフ実装。
- DuckDB への SQL 実行ではスキャン範囲を限定（計算ホライズンのカレンダーバッファ）するなどパフォーマンス配慮があるが、大規模データでの運用時は更なる最適化が推奨される。
- news_nlp の API 呼び出しはバッチ化や最大文字数制限（1銘柄あたり最大記事数 / 文字数）を行ってトークン肥大化を抑制する設計。

### 将来の改善候補（ToDo / Notes）
- position_sizing: 銘柄毎の単元（lot_size）を stocks マスタで保持し、個別 lot_map を受け取る設計への拡張。
- apply_sector_cap: 価格欠損時のフォールバック（前日終値や取得原価）を導入して露出計算の精度を向上。
- news_nlp: API 失敗時の部分再試行やメトリクス収集、より詳細なロギング強化。
- リサーチ系: heavy な集計用途での性能改善（インデックス・パーティション戦略の採用検討）。

------------------------------------------------------------
この CHANGELOG はコードベースから推測して作成した初回リリースの要約です。細かな実装差分や追加ファイルがある場合は適宜追記してください。