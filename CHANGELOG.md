# CHANGELOG

すべての変更は「Keep a Changelog」形式に準拠します。  
（言語: 日本語）

## [Unreleased]
- 今後の変更予定。

## [0.1.0] - 2026-04-12
初回リリース。以下の主要機能・コンポーネントを実装しました。

### 追加 (Added)
- 全般
  - パッケージ初期バージョンを `0.1.0` として公開。
  - DuckDB / SQLite を利用したデータ処理基盤を導入（設定経由でパス指定可能）。
  - ロギングを標準化し、各コマンドラインや長時間プロセスのログ出力を有効化。

- 設定管理 (kabusys.config)
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を探索）。
  - .env / .env.local の読み込み順序を定義（OS 環境変数を保護する protected 機構を採用）。
  - export 形式やクォート付き値、インラインコメントに対応した .env パーサ実装。
  - Settings クラスを追加し、環境変数から各種設定値（DB パス、API トークン、しきい値、環境種別など）を取得・検証するプロパティを提供。
  - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL のバリデーションを実装。

- 実行系 (Execution)
  - ExecutionEngine 起動スクリプト（run_execution.py）を追加。
    - 起動時にプロセス優先度を高に設定する仕組みを導入。
    - KABUSYS_ENV が `paper_trading` の場合、Paper Trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててセッションを実行。
    - RiskManager の初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）を導入。
    - DuckDB 接続を ExecutionEngine に渡す設計。

- 監視系 (Monitoring)
  - SystemMonitor 起動スクリプト（run_monitoring.py）を追加。
    - デフォルトポーリング間隔 60 秒、環境変数 `MONITOR_POLL_INTERVAL` により上書き可能（不正値はデフォルトへフォールバック）。
    - 監視用 DB テーブルの初期化を行う init_monitoring_db を呼び出し、DuckDB / SQLite 接続を確立。
    - 監視は環境に関係なく本番の sqlite_path を使用する挙動を明示（監視データを本番 DB に記録）。

- ユーティリティ (kabusys.utils)
  - プロセス優先度と CPU affinity を設定するユーティリティ（process_priority.py）を実装。
    - Windows / POSIX 系（Linux / macOS / FreeBSD）を考慮した抽象化を提供。
    - 権限不足や未対応プラットフォーム時は警告を出して安全にスキップ。
    - CPU コア数制限（set_cpu_affinity）機能を実装。

- ポートフォリオ構築 (kabusys.portfolio)
  - 銘柄選定・重み付け（portfolio_builder.py）
    - select_candidates（スコア降順 + signal_rank タイブレーク）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア正規化配分、スコア全0時にフォールバック）
  - セクター制約・レジーム乗数（risk_adjustment.py）
    - apply_sector_cap（既存保有をもとにセクター上限をチェックして候補を除外）
    - calc_regime_multiplier（bull/neutral/bear に対する乗数、未知レジームは警告して 1.0 にフォールバック）
  - 取引数量決定（position_sizing.py）
    - risk_based / equal / score の allocation_method をサポート。
    - 単元株（lot_size）丸め、max_position 上限、available_cash に基づく aggregate-cap スケールダウンを実装。
    - cost_buffer による手数料/スリッページ保守的見積りと残差分のロット配分ロジックを実装。

- リサーチ（kabusys.research）
  - ファクター計算（factor_research.py）
    - モメンタム（1M/3M/6M リターン、MA200 乖離率）
    - ボラティリティ（20日 ATR、ATR 比率、20日平均売買代金、出来高比）
    - バリュー（PER・ROE。raw_financials から最新レコードを取得）
    - DuckDB を用いた SQL ベースの実装（prices_daily / raw_financials 参照）
  - 特徴量探索（feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）
    - IC（Information Coefficient）計算、ランク関数（rank）
    - factor_summary による統計要約（count/mean/std/min/max/median）
  - リサーチ API を package export でまとめて公開。

- AI / NLP（kabusys.ai）
  - ニュース NLP スコアリング（news_nlp.py）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）でセンチメント（-1.0～1.0）を算出して ai_scores テーブルへ反映。
    - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）、トークン肥大化対策（記事数・文字数上限）、スコアクリップ（±1.0）を実装。
    - 429・ネットワーク・5xx 等は指数バックオフでリトライ（上限あり）。
    - API キー未設定時は ValueError を送出。

- ツール（kabusys.tools）
  - paper_verification_report.py を追加
    - Paper Trading DB（デフォルト: data/paper_trading.db）を解析して稼働率、注文成功率、送信率、レイテンシ（P95 など）、リスク却下数を集計・表示。
    - 合否判定（PASS/FAIL）を導入し、閾値はソース内定義（例: 稼働率 >= 99%、P95 <= 200ms 等）。
    - コマンドライン引数で日付範囲と DB パスを指定可能（--from/--to/--db）。

### 変更 (Changed)
- None（初期リリースのため過去のバージョンからの変更点はありません）。

### 修正 (Fixed)
- .env パーサ
  - export 形式、クォート付き値内のバックスラッシュエスケープ、インラインコメントの解釈などを想定した堅牢な実装を提供。
- ポートフォリオ計算
  - スケールダウン時のロット丸めと残差配分ロジックを実装し、aggregate cap 超過時の配分を保守的かつ再現性ある方式で行うよう改善。
- 監視ループ
  - `MONITOR_POLL_INTERVAL` の不正値に対するフォールバック（警告ログ出力）を実装し、time.sleep に渡す不正値による例外発生を防止。

### 既知の制限 (Known issues)
- price_map に価格が欠損（0.0）の場合、apply_sector_cap のエクスポージャーが過小見積りされる可能性があり、その結果ブロック判定が甘くなる旨をソース内に注記（将来的にフォールバック価格の導入を検討）。
- news_nlp の実装は OpenAI API に依存するため、API の利用制限やコストに注意が必要。部分失敗時は他銘柄の既存スコア保護を行うが、完全なトランザクション保証はない。
- set_cpu_affinity は環境/権限に依存し、失敗した場合は警告を出してスキップする設計。

---

著者:
- KabuSys 開発チーム

注: 本 CHANGELOG はリポジトリ内のソースコードから機能・設計を推測して作成しています。実際のコミット履歴や外部ドキュメントと差異がある可能性があります。