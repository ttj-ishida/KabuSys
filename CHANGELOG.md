# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
このファイルはコードベースから推測可能な機能追加・改善点・既知の制約をまとめたもので、実際のコミット履歴と完全に一致しない場合があります。

---

## [Unreleased]

### 追加
- news_nlp モジュール（OpenAI を用いたニュースセンチメントスコアリング）の実装を追加（バッチ処理・スコアクリップ・API リトライ方針などの設計を含む）。
- 各種内部ユーティリティ・純粋関数群の拡充（ポートフォリオ構築 / リスク調整 / ポジションサイジング / 研究用ファクター計算・統計等）。

### 変更
- 環境変数読み込みロジックの強化:
  - `.env` / `.env.local` の自動読み込み（OS 環境変数を保護する protected 機能、.env.local が .env を上書き）。
  - `export KEY=val` 形式やクォート文字列（バックスラッシュエスケープ含む）、インラインコメントの扱いに対応。
  - 自動ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` フラグを追加。

### 既知の制約 / TODO
- news_nlp の記事取得部分（内部ヘルパー _fetch_articles の実装）がスナップショットで途中までしか確認できないため、完全実装が未完の可能性あり。
- apply_sector_cap 内で price が欠損（0.0）時のフォールバックは TODO コメントあり（将来的な改善予定）。
- position_sizing の lot_size は現状グローバル固定（将来的には銘柄別単元対応を想定）。

---

## [0.1.0] - 2026-04-17

最初の公開バージョン（推定）。以下を含む主要機能群を実装。

### 追加
- コアアプリケーション構成
  - `kabusys.config.Settings` クラスにより、環境変数ベースの設定管理を提供。
    - 多数の設定をプロパティ経由で取得（J-Quants / kabu API / LINE / DB パス / 監視しきい値 / 実行環境フラグ等）。
    - 値検証を行い、不正な設定値は ValueError を発生させる（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。
  - パッケージメタ情報: `__version__ = "0.1.0"`。

- 実行関連スクリプト
  - run_execution:
    - ExecutionEngine を起動するエントリポイント。
    - Paper Trading 環境（KABUSYS_ENV=paper_trading）では専用の SQLite（`data/paper_trading.db` / 環境変数 `PAPER_TRADING_SQLITE_PATH`）と MockBrokerClient を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てとデフォルトリスク設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
    - 停止フラグ（data/stop_requested.flag）と PID 管理（data/execution.pid）をサポート。
  - run_monitoring:
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒、0 以下や不正値はフォールバックして警告）。
    - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する旨の設計（明示的に意図された挙動）。
    - 停止フラグの検出でグレースフルにループを抜ける。

- 監視 / DB 初期化
  - `monitoring.monitoring_db.init_monitoring_db` 呼び出しにより、起動時に監視テーブルが存在することを保証（冪等）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights, calc_score_weights: 等配分 / スコア加重配分（全スコアが 0 の場合は等分へフォールバックし警告）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存ポジションをセクター別に集計し、上限超過セクターの新規候補を除外。unknown セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた乗数（bull/neutral/bear をマップ、未知値は 1.0 でフォールバックして警告）。
  - portfolio.position_sizing:
    - calc_position_sizes: 重み・候補・現金・既存ポジション・価格などを元に発注株数計算を実装。
    - risk_based / equal / score の allocation_method をサポート。
    - 単元丸め（lot_size）・1 銘柄上限・aggregate cap（現金に収まるようスケールダウン）・残差処理ロジック実装。

- 研究（research）モジュール
  - research.factor_research:
    - calc_momentum / calc_volatility / calc_value: DuckDB を用いた SQL ベースのファクター計算（MA200, ATR20, 各種モメンタム, PER/ROE 等）。
    - データ不足時は None を返す安全設計。
  - research.feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。入力検証（horizons の範囲）。
    - calc_ic: スピアマンランク相関（IC）実装。レコード数が少なければ None を返す。
    - rank, factor_summary: ランク付け（同順位は平均ランク）・基本統計量計算（count/mean/std/min/max/median）を標準ライブラリのみで実装。

- AI / ニューススコアリング
  - ai.news_nlp:
    - raw_news を銘柄ごとに集約して OpenAI（gpt-4o-mini）でセンチメント評価し、ai_scores テーブルへ書き込む設計。
    - バッチサイズ、最大記事数・文字数トリム、API リトライ（429/ネットワーク/5xx）、結果バリデーション、スコアクリップ（±1.0）等の堅牢化方針を実装。
    - ニュース窓（JST ベースの前日 15:00 ～ 当日 08:30）を UTC に変換するユーティリティを提供。

- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成スクリプト（コマンドライン実行: python -m kabusys.tools.paper_verification_report）。
    - 稼働率 / 注文成功率 / 送信率 / レイテンシ（P95）などの指標を算出し、閾値による PASS/FAIL 判定を実施。
    - DB のテーブル欠損時やデータ不足時に安全に N/A を出力する設計。

- ユーティリティ
  - utils.process_priority:
    - Windows と POSIX を吸収するプロセス優先度設定（set_process_priority）。
    - CPU affinity を固定する set_cpu_affinity を追加。
    - 権限不足や未サポート属性に対して警告を出してスキップする堅牢性。

### 変更（実装・設計上の注目点）
- DB 関連:
  - DuckDB（解析用）と SQLite（状態・トランザクション用）を併用する設計。duckdb_path / sqlite_path / paper_sqlite_path のデフォルトパスを設定。
- ログとエラーハンドリング:
  - 各起動スクリプトでは logging.basicConfig(level=logging.INFO) を設定し、重大な例外は logger.exception で記録してループ継続を保証。
- セキュリティ/安全設計:
  - OpenAI API キー未設定の場合は明示的に ValueError を投げる（news_nlp）。
  - 実行中の停止はファイルフラグ（data/stop_requested.flag）で検知する単純かつ確実な手法を採用。

### 修正（バグフィックス等）
- run_monitoring のポーリング間隔取得で不正値（0 や文字列）に対して警告を出しデフォルトにフォールバックするよう修正（time.sleep に不正値を渡して ValueError を発生させないため）。
- calc_score_weights: 全スコアが 0 の場合、等金額配分にフォールバックして警告を出す挙動を導入（分母 0 回避）。

### 既知の制約
- news_nlp の一部処理が断片的（スナップショットが途中で切れている）ため、完全な動作確認が必要。
- DuckDB executemany に関する注意（空パラメータでの実行制約）に対するコメントがあり、実行時に注意が必要。
- 一部の TODO コメント（価格フォールバック、銘柄別 lot_size 等）が残存。

---

## 参考 / 注記
- 本 CHANGELOG はソースコードを元に推測して作成しています。実際のコミットメッセージやリリースノートが存在する場合はそちらを優先してください。
- 将来的に以下の点が改善候補として確認できます:
  - price フォールバックロジックの実装（前日終値・取得原価等）。
  - 銘柄別 lot_size 対応。
  - news_nlp の完全実装とエンドツーエンドテスト。
  - 実行時の詳細なログレベル設定（Settings.log_level を反映した起動処理）。
  - テストカバレッジ拡充（特にリスク/サイジングアルゴリズム、DuckDB クエリ結果の境界条件）。

--- 

（終）