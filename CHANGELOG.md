# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
日付はコードベース内の参照（例: 2026 年）および現在の想定リリース日を基にしています。コードの内容から推測して記載しており、実際のコミット履歴ではありません。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-17
最初の公開リリース。システム監視、Execution エンジン起動、ポートフォリオ構築、研究用ファクター計算、ニュース NLP などの主要機能を含む。

### 追加 (Added)
- コアパッケージ初期実装
  - パッケージ名: kabusys、バージョン 0.1.0
  - エントリーポイントやモジュールのパブリック API を __all__ で定義。

- 実行 / 監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV が paper_trading の場合は paper_trading 用 DB を使用し MockBrokerClient を利用して本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）と pid ファイルの取り扱いを実装。
  - 両スクリプトで起動時にプロセス優先度を設定（set_process_priority("high")）。

- 設定管理
  - config.py: .env/.env.local の自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。フォーマットに柔軟に対応するパーサを実装（export プレフィックス、クォート、インラインコメント等に対応）。
  - Settings クラスを通して各種環境変数を型・値チェック付きで提供。主な設定:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - PAPER_FILL_MODE（instant/partial/never/reject の検証）
    - 各種 DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
    - 監視・しきい値設定（cpu/memory/disk 等）
    - PID / kill flag 関連設定

- DB 初期化 / 接続
  - monitoring_db.init_monitoring_db を用いて監視テーブルの冪等な初期化を保証。
  - SQLite（monitoring / paper_trading）および DuckDB を併用する設計を導入（分析は DuckDB、運用ログは SQLite）。

- ポートフォリオ構築（純粋関数）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順＋signal_rank で候補選定
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重（スコア全0 の場合は等配分へフォールバック）
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（sell_codes を除外可能、"unknown" セクターは無視）
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull/neutral/bear をマップ、未知は警告して 1.0 フォールバック）
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数算出。単元株（lot_size）丸め、per-stock 上限・aggregate cap のスケールダウン、cost_buffer を考慮した保守的見積り、残差処理による追加配分ロジックを実装。

- 研究用モジュール（DuckDB ベース）
  - research.factor_research:
    - calc_momentum, calc_volatility, calc_value を実装（DuckDB のウィンドウ関数を活用）。
    - 欠損データの扱いやウィンドウサイズに関する注意を文書化。
  - research.feature_exploration:
    - calc_forward_returns: 将来リターンを一度のクエリで取得（ホライズン検証あり）。
    - calc_ic: スピアマンランク相関（IC）計算。十分なサンプルがない場合は None。
    - factor_summary / rank: 基本統計量・ランク変換（同順位は平均ランク）を提供。
  - research.__init__: zscore_normalize の公開（kabusys.data.stats から）。

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等の指標を集計・判定し標準出力に出力。閾値（PASS/FAIL 基準）を定義。

- ニュース NLP（AI 統合）
  - ai.news_nlp:
    - raw_news を集約して OpenAI（gpt-4o-mini）にバッチ送信し銘柄ごとの ai_score を ai_scores テーブルへ書き込むフローを実装。
    - タイムウィンドウ計算（JST→UTC 変換）、バッチサイズ・文字数上限、スコアクリップ（±1.0）、再試行（429/5xx/ネットワーク/タイムアウトで指数バックオフ）などの設計を導入。
    - 出力 JSON のバリデーションと部分置換（DELETE/INSERT）による部分失敗時の保護を考慮。
    - OpenAI API キー未設定時は ValueError を送出。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority: Windows/POSIX の差分を吸収してプロセス優先度設定を提供。権限不足時は警告してスキップ。
    - set_cpu_affinity: 指定コア数への CPU affinity 固定（権限不足 / 未対応環境は警告してスキップ）。

### 変更 (Changed)
- (初期リリースのため履歴上の変更はなし。設計上の注意事項をドキュメント化)
  - .env の自動ロード順序を OS 環境変数 > .env.local > .env として、OS 側の既存変数は保護する実装。
  - monitor 実行時は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明示（監視データを本番 DB へ記録する設計決定）。

### 修正 (Fixed)
- （初期リリースに含まれる既知の耐障害性実装）
  - run_monitoring のポーリング間隔環境変数の不正値対策（0 以下や非整数はログ警告後デフォルトにフォールバック）。
  - .env ファイル読み込み失敗時に警告を出すようにしてプロセスが停止しないようにした。

### 注意事項 / 既知の制約 (Known issues / Notes)
- ai.news_nlp モジュールは複雑な外部 API 依存を含むため、OpenAI API キーの設定とネットワーク環境に依存する。API レート制限やコストに注意。
- position_sizing の価格フォールバックは未実装。price_map に欠損 (0.0) があるとエクスポージャーが過少見積もられる可能性がある旨をコメントに記載。将来の拡張で前日終値等をフォールバック価格として利用することを想定。
- run_monitoring は監視ログを production sqlite_path に記録する仕様のため、テスト実行時に data/monitoring.db が上書きされる点に注意。
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされる。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

### セキュリティ (Security)
- 機密情報（API トークン・パスワード等）は環境変数で扱う設計。Settings の _require により必須環境変数未設定時は明示的にエラーを投げる。

--- 

今後のリリースで追加検討すべき点（提案）
- ニュース NLP の完全なエラーハンドリングとテストカバレッジ強化。
- position_sizing の価格フォールバック実装（前日終値 / 取得コスト）。
- モニタリングとエンジンのメトリクスをより詳細にエクスポートするための Prometheus / サイドカー連携。
- DuckDB スキーマのバージョン管理とマイグレーション機能。