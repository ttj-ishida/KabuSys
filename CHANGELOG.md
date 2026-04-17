# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを採用しています。

なお、本ファイルはソースコードの内容から機能・修正点を推測して作成しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-17
初回リリース。本バージョンで導入された主要機能と実装上の注意点を列挙します。

### Added
- 基本メタ情報
  - パッケージ識別子 `kabusys`（`__version__ = "0.1.0"`）。

- 設定管理
  - `kabusys.config.Settings` による環境変数/`.env` 読み込み・検証機構。
  - 自動 `.env` ロード機能（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - `.env` パーサーは `export ` プレフィックス、クォート、エスケープ、インラインコメントの取り扱いに対応。
  - 必須環境変数チェック (`_require`) と、`KABUSYS_ENV`・`LOG_LEVEL` 等の値検証を実装。

- 実行/監視用スクリプト
  - `run_execution.py`：ExecutionEngine 起動スクリプト
    - `KABUSYS_ENV=paper_trading` の場合に専用の paper_trading DB (`data/paper_trading.db` 既定) を使用し、本番 DB と分離。
    - ブローカークライアントファクトリ経由の Broker 接続、OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて `ExecutionEngine` を実行（デーモンスレッド）。
    - 停止フラグ `data/stop_requested.flag` を監視して安全に停止。
    - 起動時にプロセス優先度を "high" に設定。
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動スクリプト
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60 秒、無効値はログ警告の上でデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番用の sqlite パス (`Settings.sqlite_path`) を使用。
    - 停止フラグ `data/stop_requested.flag` の検出でループを終了。
    - 起動時にプロセス優先度を "high" に設定。

- 監視 DB 初期化
  - `kabusys.monitoring.monitoring_db.init_monitoring_db` を起動スクリプトから呼び出し、監視テーブルの存在を保証（冪等）。

- ツール
  - `kabusys.tools.paper_verification_report`：Paper Trading の検証レポート生成スクリプト
    - CLI 引数 `--from` / `--to` / `--db` に対応。
    - デフォルト DB: 環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを算出。閾値（PASS/FAIL）を定義。
    - P95 計算、日付フィルタ条件の安全な構築、DB 存在チェック・例外耐性を実装。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - `select_candidates`：スコア降順 + tie-break による候補選定。
    - `calc_equal_weights`：等金額配分。
    - `calc_score_weights`：スコア正規化配分（全銘柄スコアが 0 の場合は等金額にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`
    - `apply_sector_cap`：セクター集中制限。既存ポジションのセクター露出に基づき候補をフィルタ（"unknown" セクターは制限対象外）。売却予定銘柄を露出計算から除外可能。
    - `calc_regime_multiplier`：市場レジームに対する投下資金乗数（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未知レジームは 1.0 にフォールバック）。
  - `kabusys.portfolio.position_sizing`
    - `calc_position_sizes`：複数の配分メソッド（"risk_based", "equal", "score"）に対応して発注株数を計算。
    - 単元（lot）丸め、1 銘柄上限・aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer（手数料・スリッページ見積もり）に対応。
    - リスクベース計算（risk_pct、stop_loss_pct）を実装。
    - aggregate スケーリング時の端数処理で残余キャッシュを利用して lot 単位で追加配分するロジックを実装。

- 研究（Research）モジュール
  - `kabusys.research.factor_research`
    - `calc_momentum`：1M/3M/6M リターン、MA200 乖離率の算出（DuckDB 経由、prices_daily テーブル参照、データ不足考慮）。
    - `calc_volatility`：20日 ATR、相対 ATR、平均売買代金、出来高比率を算出（true_range の NULL 伝播を厳密に扱う）。
    - `calc_value`：最新財務データから PER/ROE を算出（raw_financials と prices_daily を利用）。
  - `kabusys.research.feature_exploration`
    - `calc_forward_returns`：複数ホライズンの将来リターンを一括取得（安全な horizons 検証あり）。
    - `calc_ic`：ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足時は None を返す。
    - `factor_summary`：count/mean/std/min/max/median を計算。
    - `rank`：同順位は平均ランクで扱う堅牢なランク付け関数。
  - `kabusys.research.__init__` で主要関数をエクスポート。

- AI / ニュース NLP
  - `kabusys.ai.news_nlp`：raw_news テーブルを OpenAI API（gpt-4o-mini）でセンチメントスコア化し、ai_scores テーブルへ書き込む処理を設計。
    - 処理ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ `calc_news_window` を追加。
    - バッチサイズ、文字数制限、記事数制限、API 再試行（429/5xx/ネットワーク断に対する指数バックオフ）を設計。
    - レスポンス検証、スコアの ±1.0 クリップ、部分失敗時に既存スコアを保護するためのコード絞り込み DELETE/INSERT 戦略を採用。
    - API キーは引数または環境変数 `OPENAI_API_KEY` から解決。未設定時は ValueError を送出。

- プロセス制御ユーティリティ
  - `kabusys.utils.process_priority`
    - `set_process_priority(level)`：Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収してプロセス優先度を設定。アクセス権限不足時は警告でスキップ。
    - `set_cpu_affinity(cpu_count)`：最初の N コアに固定する機能。権限不足や未サポート環境は警告でスキップ。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （現時点でなし）

### Removed
- （現時点でなし）

### Security
- OpenAI API キーを引数または環境変数で明示的に扱うようにし、未設定時は例外（漏洩等の防止策として明示的失敗）を採用。

### Notes / Known limitations / TODOs
- 一部モジュールに将来的な改善点や TODO コメントあり（例: price 欠損時のフォールバック価格、銘柄別 lot_size 管理の拡張など）。
- `ai.news_nlp` 実装は堅牢な設計を行っているが、API レスポンスのスキーマやレート制限状況に依存するため、本番運用前に実際の API 呼び出しによる検証が必要。
- `.env` 自動ロードはプロジェクトルート検出に依存するため、配布後の環境では `.env` を明示的に配置するか、`KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定して明示的に環境変数を与える運用が推奨される。
- `run_monitoring` は監視データベースとして常に本番 sqlite パスを参照する設計（意図的）。テスト時は環境変数やコード上で別 DB を指定すること。

---

この CHANGELOG はソースコードから推測して作成しています。差分や追加のリリースノートを反映する場合は、対応するコミット/変更点に基づいて更新してください。