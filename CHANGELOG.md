# Changelog

すべての変更は「Keep a Changelog」フォーマットに準拠しています。  
バージョン番号はパッケージ定義 (kabusys.__version__) に合わせています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

初回リリース。日本株自動売買システム「KabuSys」のコア機能群をまとめて追加しました。
以下はコードベースから読み取れる主要な追加点・設計方針・注意点の要約です。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として追加。

- 設定管理
  - `kabusys.config.Settings` を導入。環境変数をラップしたプロパティ群を提供（J-Quants / kabuAPI / LINE / DB / 監視閾値 / 実行環境など）。
  - .env 自動読み込み機能を実装（プロジェクトルート自動検出: .git または pyproject.toml を基準）。
  - `.env` / `.env.local` の読み込み順序をサポート。OS 環境変数の保護（上書き禁止）を実装。
  - .env パーサーはクォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメント等に対応。

- 実行・監視スクリプト
  - `run_execution.py`：ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV により paper_trading を選べる（paper_trading 時は専用 SQLite DB に記録して本番 DB と分離）。
    - プロセス優先度を起動時に設定（デフォルトで "high" を設定）。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository／OrderManager／RiskManager／Reconciler の組み立てと ExecutionEngine の起動を実装。
    - 停止フラグ（data/stop_requested.flag）を監視し、フラグ有効時は安全に停止。
  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視モジュールは KABUSYS_ENV にかかわらず本番 `sqlite_path` を使用する設計（監視データは production DB を参照/保存）。
    - 例外ハンドリング、停止フラグ検出、終了時の DB クローズ処理を実装。

- 監視 DB 初期化ユーティリティ
  - `monitoring.monitoring_db.init_monitoring_db`（呼び出しのみを確認。監視テーブルの冪等な初期化を保証）。

- ユーティリティ
  - `kabusys.utils.process_priority`：プラットフォーム依存差分を吸収するプロセス優先度設定ユーティリティを追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）に対応。
    - `set_process_priority(level: "high"|"normal"|"low")`、`set_cpu_affinity(cpu_count: int|None)` を提供。
    - 権限不足や未サポート環境では警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`：
    - 候補選定 `select_candidates`（スコア降順、同点は signal_rank でタイブレーク）。
    - 重み算出 `calc_equal_weights`, `calc_score_weights`（全スコアが 0 の場合は警告して等配分にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`：
    - セクター集中上限を適用する `apply_sector_cap`。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier`（"bull"/"neutral"/"bear" のマップ、未知レジームは 1.0 でフォールバック）。
  - `kabusys.portfolio.position_sizing`：
    - 各銘柄の発注株数を決定する `calc_position_sizes`（allocation_method により "risk_based" / "equal" / "score" をサポート）。
    - 単元株（lot_size）丸め、1銘柄上限／aggregate cap（利用可能現金超過時の縮小）、cost_buffer（手数料・スリッページの保守的見積）を考慮。
    - price 欠損時のスキップ、将来的な拡張（銘柄別 lot_size）用の TODO コメントあり。

- 研究（Research）モジュール
  - `kabusys.research.factor_research`：
    - Momentum, Volatility, Value ファクター計算（DuckDB 上の prices_daily / raw_financials を参照）。
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）、calc_volatility（ATR20, 相対ATR, 平均売買代金, 出来高比率）、calc_value（PER, ROE）。
    - 計算窓や欠損値処理、パフォーマンスを考えたスキャン範囲設計を含む。
  - `kabusys.research.feature_exploration`：
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク関数（rank）、統計サマリー（factor_summary）。
    - 外部ライブラリに依存せず、標準ライブラリ + DuckDB のみで実装。
  - `kabusys.research.__init__` で主要関数を公開。

- ツール
  - `kabusys.tools.paper_verification_report`：
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率（fill_rate）、送信率、P95 レイテンシなどを算出して PASS/FAIL 判定を出力。
    - CLI 引数で期間指定（--from, --to）と DB パス指定（--db）をサポート。
    - P95 計算、期間フィルタ、DB 存在チェック、欠損テーブルへの耐性を実装。

- AI ニュース NLP
  - `kabusys.ai.news_nlp`：
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini + JSON Mode）へバッチ送信し、銘柄ごとのセンチメントスコア（-1.0〜1.0）を算出して ai_scores テーブルへ書き込むフローを実装。
    - バッチサイズ、記事数/文字数上限、時間ウィンドウ（JST→UTC 変換）を定義。
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）に対する指数バックオフ、レスポンスバリデーション、スコアクリップを実装。
    - API キー未指定時は ValueError を送出して明示的に失敗させる設計（安全側）。
    - 実装ノート: 実行時のルックアヘッドバイアスを防ぐため内部で日付を参照しない方針を採用。

### Changed / Design Decisions
- DB 分離方針
  - paper_trading 環境では paper_trading 用の SQLite DB (`PAPER_TRADING_SQLITE_PATH` / default: data/paper_trading.db) を使用し、本番用 DB と記録を完全に分離。
  - ただし監視（run_monitoring）は KABUSYS_ENV にかかわらず本番の `sqlite_path` を使用する設計（監視データは production DB を参照）。

- 環境変数の取り扱い
  - OS 環境変数は保護され `.env.local` による上書きでも上書き不可。
  - 自動ロードを無効にするために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使用可能。

- デフォルト値、検証
  - 多くの設定にデフォルト値と入力検証を追加（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL など）。不正な値は ValueError を発生させて早期検出。

### Fixed / Robustness
- 入力パースとエラーハンドリングの強化
  - .env のパースはクォート・エスケープ・コメントを正しく扱うよう改善。
  - run_monitoring/run_execution は停止フラグ・KeyboardInterrupt を正しく扱い、DB 接続を finally でクローズ。
  - process_priority/set_cpu_affinity は権限不足で失敗した場合にワーニングを出して安全に処理を継続。

### Known TODO / Limitations
- position_sizing の価格フォールバック
  - price が欠損（0.0）の場合にエクスポージャーが過少評価される問題が TODO コメントとして残っています（前日終値や取得原価でのフォールバックを検討）。
- 銘柄別 lot_size の将来的対応
  - 現状は全銘柄共通の lot_size（デフォルト 100）を想定。将来的に銘柄マスタ経由で lot_size を持たせる余地あり。
- News NLP 周りは大規模 API 呼び出しを行うため、運用時には OpenAI API のコストとレート制限に注意してください。

### Security
- OpenAI API キーなどの機密情報は環境変数経由で取り扱う想定。`.env` 自動ロード機能は OS 環境変数を上書きしない仕様により安全性を考慮。

---

注: 上記は提供されたコードベースの内容から推測して作成した CHANGELOG です。実際のコミット履歴や差分が存在する場合は、コミットメッセージや PR の説明に基づいて追補・修正してください。