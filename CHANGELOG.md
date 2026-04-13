# Changelog

すべての注目すべき変更点をこのファイルに記録します。
このプロジェクトは Keep a Changelog の方針に従ってバージョニングしています。  

フォーマット: https://keepachangelog.com/（日本語訳に準拠）

## [Unreleased]
- なし

## [0.1.0] - 2026-04-13
最初の公開リリース。自動売買システムのコア機能群を実装しています。

### 追加 (Added)
- 全体
  - パッケージ初期リリース。モジュール構成（data, strategy, execution, monitoring, portfolio, research, ai, tools, utils）を提供。
  - バージョン情報を __version__ = "0.1.0" として定義。

- 実行・監視
  - run_execution: ExecutionEngine 起動スクリプトを追加。ブローカークライアント生成、OrderManager / OrderRepository / RiskManager / Reconciler の組立て、セッション実行を行う。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
  - プロセス優先度設定ユーティリティを実行開始時に呼び出し（高優先度へ設定）。

- 設定管理
  - kabusys.config: .env 自動読み込み機能（プロジェクトルート検出 .git / pyproject.toml ベース）を実装。.env と .env.local の読み込み順・上書きルールを実装。
  - .env パーサーは export 構文、クォート文字列、行末コメント等に対応する堅牢な実装。
  - Settings クラスを提供し、環境変数のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）と各種パス（duckdb/sqlite/paper_sqlite/pid/kill flag）を取得可能に。

- 実行系（Execution）
  - BrokerClientFactory 経由で paper_trading 環境では MockBroker を利用し、Paper Trading 用の専用 SQLite（デフォルト: data/paper_trading.db）へ完全に分離して記録する設計を追加。
  - RiskManager に対する RiskConfig 設定を導入（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）。
  - ExecutionEngine に EngineConfig（target_date）と reconciler, pid_file を渡してセッション実行する仕組みを実装。

- 監視・モニタリング
  - monitoring_db の初期化呼び出しを両スクリプトで行い、監視テーブルの存在を冪等に保証。
  - run_monitoring は環境に依らず本番 sqlite_path を使用して監視データを記録する旨を明示。

- ポートフォリオ構築
  - portfolio.portfolio_builder: 候補選定(select_candidates)、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights) を実装。スコア全て０時のフォールバックを実装。
  - portfolio.risk_adjustment: セクター集中制限適用(apply_sector_cap)、市場レジームに基づく投下資金乗数(calc_regime_multiplier) を実装。
  - portfolio.position_sizing: position sizing ロジックを実装（risk_based / equal / score の配分、単元株丸め、aggregate cap によるスケールダウン、cost_buffer 対応）。

- リサーチ（研究用）
  - research.factor_research: Momentum / Volatility / Value ファクター計算を DuckDB 経由で実装（prices_daily / raw_financials を参照）。MA200 や ATR、1M/3M/6M リターン等を計算。
  - research.feature_exploration: 将来リターン計算(calc_forward_returns)、IC (Spearman) 計算(calc_ic)、ファクター統計サマリ(factor_summary)、ランク変換(rank) を実装。
  - research.__init__ で zscore_normalize をエクスポート（kabusys.data.stats 依存）。

- AI / ニュース解析
  - ai.news_nlp: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）でセンチメントスコアを算出し、ai_scores テーブルへ書き戻す処理を実装。
  - バッチ処理（最大 20 銘柄/コール）、記事数/文字数トリム、429/ネットワーク/5xx に対する指数バックオフ再試行、レスポンスの厳密な JSON バリデーション、スコアの ±1.0 クリップ、部分更新戦略（成功したコードのみ置換）などの堅牢化を導入。
  - API キー未設定時に ValueError を送出する仕様。

- ユーティリティ
  - utils.process_priority: Windows / POSIX の差を吸収するプロセス優先度設定（high/normal/low）と CPU affinity 固定機能を追加。アクセス権限や未対応環境では警告でスキップする安全設計。
  - 例外ハンドリングやログ出力（warning/debug）を各所で整備。

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数を集計し、PASS/FAIL 判定を行う。コマンドライン引数で期間指定可能。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 各種フォールバックと入力検証を強化:
  - MONITOR_POLL_INTERVAL の不正値（0 以下や整数以外）を検出してデフォルト値（60 秒）へフォールバックし、警告ログを出すように。
  - .env を読み込む際に OS 環境変数を保護（protected）して上書きによる意図しない環境汚染を防止。
  - DuckDB executemany 周りの制約に配慮した実装（空 params チェック等がコメントで明記）。

### 非推奨 (Deprecated)
- なし

### セキュリティ (Security)
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で必須。未設定時は明示的にエラーとなる（フェイルセーフにより無音でキーなしで進めることはしない）。
- .env 自動ロードはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。OS 環境変数は上書きされない設計。

### 既知の制約・今後の改善メモ (Notes / TODO)
- position_sizing: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があるため、将来的に前日終値や取得原価でのフォールバックを検討。
- 単元株数 lot_size は現状グローバル固定（デフォルト 100）。将来的には銘柄毎の lot_map を導入して拡張予定。
- news_nlp の OpenAI 呼び出しはモデル・API 仕様変更に依存するため、レスポンスバリデーションとリトライロジックの保守が必要。
- research モジュールは DuckDB 内のテーブル構造（prices_daily, raw_financials）に依存。データ品質によっては None が多く返る可能性あり。

---

参考: この CHANGELOG はソースコード内のコメント・実装から推測して作成しています。実際の変更履歴（コミットログ）に基づくものではないため、公開履歴と差異が生じる可能性があります。必要であればコミット単位の履歴に基づいた詳細な CHANGLEOG 作成も対応します。