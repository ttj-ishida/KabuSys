# CHANGELOG

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
（コードベースの内容から推測して作成しています）

すべての変更は後方互換性を考慮して実装されていますが、実運用時の環境変数設定や DB パスには注意してください。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-13
初回リリース — 日本株自動売買フレームワークの基礎機能群を追加。

### Added
- 実行エントリ・監視
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。
    - 環境に応じてブローカークライアントを生成（paper_trading 時は MockBroker を用いる想定）。
    - paper_trading 環境では paper_trading 用 SQLite DB（data/paper_trading.db）を使用し、本番 DB と分離。
    - 起動時にプロセス優先度を High に設定。
    - 依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立ててセッション実行。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視プロセスは環境に関係なく本番 sqlite_path を参照して監視情報を記録。
    - 起動時にプロセス優先度を High に設定。

- 設定 / 環境変数管理
  - config.py: .env 自動読み込みと設定管理を導入。
    - プロジェクトルートを .git または pyproject.toml から自動検出し、.env/.env.local を読み込む（OS 環境変数が優先）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途）。
    - 複雑な .env 行（export プレフィックス、クォート、エスケープ、インラインコメント等）に対応するパーサを実装。
    - Settings クラスを導入し、J-Quants / kabu API / LINE / DB パス /監視閾値 / 環境種別などのプロパティを提供。
    - env や log_level、paper_fill_mode 等に対するバリデーションを実装（不正値は ValueError）。

- モニタリング DB 初期化
  - monitoring_db 初期化を起動時に行う（冪等）よう run_execution/run_monitoring に組み込み。

- ユーティリティ
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でプロセス優先度と CPU affinity を設定するユーティリティを追加。
    - set_process_priority(level): high/normal/low をサポート。権限不足等は警告でスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数へのピン留めをサポート。未対応プラットフォームや権限不足は警告でスキップ。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順・タイブレーク付きで選別。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア比率配分（スコアが全て 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中を判定し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは警告の上 1.0 にフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method("risk_based"/"equal"/"score") に基づく発注株数決定を実装。
    - 単元株（lot_size）対応、1銘柄上限・aggregate cap（available_cash に基づくスケーリング）、cost_buffer を用いた保守的見積り、スケール後の端数配分ロジックを実装。
    - price が欠損する場合のスキップ処理やログ出力を実装。

- リサーチ / ファクター計算
  - research/factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を算出（直近財務レコードの取得ロジックを含む）。
    - DuckDB を用いた SQL ベースの実装で、prices_daily / raw_financials を参照。
  - research/feature_exploration.py:
    - calc_forward_returns: 各ホライズンの将来リターンを計算（horizons 検証あり）。
    - calc_ic: Spearman ランク相関（IC）の計算（欠損やデータ不足を考慮して None を返す場合あり）。
    - factor_summary / rank: 基本統計量・ランク変換ユーティリティを提供。
  - research/__init__.py: 主要関数をパブリックにエクスポート。

- AI / ニュース NLP
  - ai/news_nlp.py:
    - raw_news を集約して OpenAI (gpt-4o-mini) に送信し、センチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む処理を実装。
    - ニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）算出ユーティリティを提供。
    - バッチ処理（最大 20 銘柄/コール）、記事文字数上限、記事数上限、スコアクリップ、リトライ（429/5xx/タイムアウト）等のエラーハンドリングを実装。
    - OpenAI の API キー未設定時は ValueError を発生させる。
    - API レスポンス検証と部分更新（成功コードのみ置換）により部分失敗時の保護を考慮。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成スクリプトを追加（コマンドライン実行可）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を出力。
    - データが存在しない場合の安全な処理（OperationalError キャッチ）を実装。
    - P95 計算、日付フィルタ、出力フォーマットを提供。

- パッケージ情報
  - __init__.py: パッケージバージョン __version__ = "0.1.0" を設定。

### Changed
- 設計上の方針・実装ノート（ドキュメント的な追記）
  - 多くの純粋関数（ポートフォリオ構築、リスク調整、ポジションサイジング、リサーチ）は DB を参照せずメモリ内計算に限定（テスト容易性向上）。
  - DuckDB を分析用クエリ基盤として採用（prices_daily / raw_financials / raw_news / ai_scores など）。
  - 起動スクリプトは開始直後にプロセス優先度設定を行うように統一。

### Fixed
- なし（初回リリースのためバグ修正履歴はなし）。  
  ※コード中に権限不足やデータ欠損に対する防御的なハンドリング（警告・スキップ等）が多数実装されています。

### Known issues / Notes
- apply_sector_cap の価格欠損時の扱い:
  - price が 0.0 の場合にエクスポージャーが過小評価され得る旨の TODO コメントあり。将来的に前日終値や取得原価でのフォールバックが検討対象。
- position_sizing の lot_size:
  - 現在は全銘柄共通の単元数（デフォルト 100）。将来的には銘柄別 lot_map を受け取る設計への拡張が想定されている。
- DuckDB executemany:
  - ai/news_nlp や他処理で executemany 前に params が空でないことを確認する必要がある旨の注意がある（DuckDB 0.10 の制約）。
- ai/news_nlp.py は大きなネットワーク依存処理を含むため、API レート制限やコストに注意。部分失敗時のロールバックは限定的（成功コードのみ置換）である点に留意。
- process_priority / set_cpu_affinity:
  - 実行環境の権限やプラットフォームにより設定が適用されない場合があり、その際はログで警告となる。

### Security
- セキュリティに関する変更は特に無し。  
  - ただし、環境変数（API キー等）の取り扱いに依存するため、運用時は環境変数管理に注意すること。

---

今後の予定（想定）
- 単体テスト・統合テストの追加（特に DuckDB/SQLite 周り、AI API 呼び出しのモック化）
- logging レベルや出力先の構成強化（設定から制御可能に）
- per-stock lot_size マッピング、価格フォールバックロジックの追加
- news_nlp の冗長性向上（部分失敗時の再試行ポリシー改善、バックアップストレージ）
- 実行監視・デプロイ用の systemd 等ユニットファイルサンプルの追加

（以上）