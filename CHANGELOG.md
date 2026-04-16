# Changelog

すべての重要な変更点を記載します。フォーマットは Keep a Changelog に準拠しています。

現在のバージョン: 0.1.0 — 2026-04-16

## [Unreleased]
（今後のリリース向け予定／推測）
### Added
- ai/news_nlp の処理完了・部分的テストカバレッジの追加予定
  - OpenAI API 呼び出しのレスポンス検証と部分ロールバックを保証する仕組み導入予定
- モニタリング・実行の起動スクリプトに対する systemd / コンテナ向けのユーティリティ改善予定（PID 管理、ログレベル制御など）
- portfolio モジュールに対する追加の配分アルゴリズム（銘柄別 lot_size サポート等）

### Changed
- ドキュメント整備、関数引数の型注釈や docstring の改善予定

### Fixed
- 小数点や None の扱いに関する境界ケースの継続的な修正予定

---

## [0.1.0] - 2026-04-16
初回公開リリース。本リポジトリから推測される主要な機能追加・修正をまとめています。

### Added
- 全体
  - 初期パッケージ化: kabusys パッケージを提供（__version__ = 0.1.0）。
  - 設定管理モジュール（kabusys.config.Settings）
    - .env / .env.local の自動読み込み（プロジェクトルート検出を行い OS 環境変数優先で読み込む）
    - 複雑な .env のパースに対応（export プレフィックス、クォート内のエスケープ、インラインコメントの扱い等）
    - 環境変数未設定時に明確なエラーを返す _require() を提供
    - 各種設定プロパティ（J-Quants / kabu API / DB パス /監視閾値 /環境判定 etc.）
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD サポート
  - 起動スクリプト
    - run_execution.py: 実取引エンジン起動スクリプト
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用して本番 DB から分離
      - BrokerClientFactory を用いた Broker クライアント生成
      - ExecutionEngine の起動と停止フロー管理（stop flag / PID ファイル利用）
      - RiskManager, OrderManager, Reconciler 等の組み立て処理
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔指定可能（デフォルト 60 秒）
      - 監視は環境にかかわらず本番 sqlite_path を使用（監視データは一元管理）
      - 停止フラグファイル検知による優雅な終了、例外保護によるループ継続
  - データベース統合
    - DuckDB と SQLite の両方を利用する設計（duckdb_path / sqlite_path を設定から取得）
    - 監視用 DB スキーマ初期化ユーティリティ init_monitoring_db の呼び出しを起動時に実施（冪等）
  - utils
    - process_priority モジュール
      - プラットフォーム差分を吸収した set_process_priority(level) を提供（Windows と POSIX 対応）
      - set_cpu_affinity(cpu_count) による CPU affinity 設定関数を追加
      - アクセス権限不足等の例外をハンドルしてワーニングでフォールバック
  - portfolio モジュール（銘柄選定・重み付け・枚数算出）
    - portfolio_builder
      - select_candidates: スコア降順かつ tie-breaker に signal_rank を利用
      - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア全0 時のフォールバック）
    - risk_adjustment
      - apply_sector_cap: セクター集中を防ぐため既存ポジション比率に基づいて候補を除外
      - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear）
    - position_sizing
      - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算
      - 単元株（lot_size）対応、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap スケーリング実装
      - 価格欠損時には銘柄をスキップする安全策
  - research モジュール（ファクター計算・特徴量探索）
    - factor_research
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の計算（window、欠損値ハンドリング）
      - calc_volatility: ATR20、相対 ATR、平均売買代金、出来高比率など
      - calc_value: raw_financials と株価から PER / ROE を算出（target_date 以前の最新財務レコードを取得）
    - feature_exploration
      - calc_forward_returns: 将来リターン（任意ホライズン）の一括取得（効率的な SQL 実装）
      - calc_ic / rank / factor_summary: IC（Spearman ρ）計算、ランク付け、統計サマリ機能
    - research.__init__ で zscore_normalize（kabusys.data.stats）をエクスポート
  - tools
    - paper_verification_report: Paper Trading 用検証レポート生成スクリプト
      - 稼働率・注文成功率・送信率・P95 レイテンシ等の集計と PASS/FAIL 判定（閾値を明示）
      - DB の存在チェック、期間フィルタ、N/A を扱うフォールバック実装
  - ai
    - news_nlp: ニュース記事を OpenAI（gpt-4o-mini）でスコアリングし ai_scores に書き込む設計を実装
      - 時間ウィンドウ計算（JST ベース → UTC 変換）
      - バッチ（最大 20 銘柄）での API 呼び出し、トークン肥大化対策（記事数・文字数制限）
      - 429 / ネットワーク / 5xx に対する指数バックオフリトライ戦略
      - レスポンスバリデーション、スコア ±1.0 のクリップ、部分成功時の更新方法（DELETE→INSERT の限定更新）
      - API キー未設定時は明示的なエラー

### Changed
- .env パースの強化
  - export プレフィックス、シングル/ダブルクォート内部のバックスラッシュエスケープ処理、インラインコメントの取り扱いを実装
  - override フラグと protected セットにより OS 環境変数の保護を実現
- run_monitoring/run_execution におけるプロセス優先度設定を起動直後に行うことで起動時負荷を優先的に制御
- Monitoring は環境（KABUSYS_ENV）に依存せず本番 sqlite_path を使用する仕様に変更（監視データは一元化）
- run_execution は paper_trading 環境で paper_trading 用 DB と MockBroker を用いる分離設計を採用

### Fixed
- 多くの箇所で欠損値（NULL / None / 空リスト）に対する堅牢な処理を追加
  - factor/research のウィンドウ不足時に None を返す、レポート側で N/A 表示する等
  - P95 計算で空リストを扱う際に None を返す実装
- calc_score_weights: 全スコアが 0 の場合にゼロ除算を防ぎ、等金額配分へフォールバックするよう修正
- .env ファイル読み込みでファイルオープン失敗時に警告を出し続行するよう変更（ワーニングでフォールバック）

### Security
- OpenAI API キー未設定時は明示的に ValueError を送出し、不正な呼び出しを防止

---

注記:
- 上記はリポジトリ内のソースコード（docstring、関数名、実装の防御的処理）から推測して作成した変更履歴です。実際のコミット履歴やタグと完全には一致しない場合があります。必要であれば、実際の git ログやリリースノートに合わせて調整します。