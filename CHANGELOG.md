Changelog
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、安定的なリリース履歴を日本語で記載しています。

[Unreleased]
------------

- 開発中（次回リリース用のメモをここに記載してください）。

[0.1.0] - 2026-04-16
-------------------

Added
- 基本機能の初期実装（初回リリース相当）。
  - CLI 起動スクリプトを追加
    - run_monitoring.py：SystemMonitor をポーリング実行するループ。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグファイル検出で安全に終了。監視処理は環境に関わらず本番 sqlite_path を使用する設計。
    - run_execution.py：ExecutionEngine 起動スクリプト。paper_trading 環境時は専用の Paper Trading DB を利用して本番 DB と分離。BrokerClientFactory によるブローカー抽象化、ExecutionEngine を別スレッドで実行して停止フラグで停止可能。
  - 設定管理
    - config.py：.env 自動ロード機能（.env → .env.local の順、OS 環境変数を保護）、.env の行パーサ（コメント、export プレフィックス、シングル/ダブルクォート・エスケープ対応）、必須環境変数取得ヘルパ、Settings クラス（各種環境変数の明示的プロパティ化とバリデーション）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder: select_candidates（スコア降順で候補選定）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等比率へフォールバック）。
    - portfolio.risk_adjustment: apply_sector_cap（セクター集中制限。unknown セクターは制限対象外）、calc_regime_multiplier（市場レジームに基づく乗数、未知レジームは 1.0 でフォールバック）。
    - portfolio.position_sizing: calc_position_sizes（リスクベース／等分配／スコア配分に対応、単元株丸め、ポートフォリオ・集計上限によりスケールダウンするロジックを実装）。cost_buffer、lot_size、max_utilization 等のパラメータサポート。
  - リサーチ（DuckDB を使ったファクター計算）
    - research.factor_research: calc_momentum、calc_volatility、calc_value（prices_daily / raw_financials を参照してファクターを計算）。
    - research.feature_exploration: calc_forward_returns（任意ホライズン）、calc_ic（Spearman ランク相関の IC 計算）、factor_summary、rank（同順位は平均ランク）。
    - research パッケージは zscore_normalize を data.stats から再エクスポートする設計。
  - AI ニュース NLP
    - ai.news_nlp: raw_news を OpenAI API（gpt-4o-mini 想定）でバッチセンチメント解析して ai_scores テーブルへ書き込むための骨格。ウィンドウ判定、記事トリム（記事数・文字数上限）、API キー解決、リトライ（429/タイムアウト/5xx の再試行）やレスポンス検証、スコアクリッピング（±1.0）、部分書き換え（該当コードのみ置換）といった設計方針を明文化。
  - ツール
    - tools.paper_verification_report：Paper Trading 用検証レポート生成ツール（CLI）。稼働率・注文成功率・送信率・P95 レイテンシ等の指標算出と PASS/FAIL 判定ロジック、日付フィルタ、DB 存在チェック、堅牢な SQL 実行（テーブル欠如時のフォールバック）を提供。
  - ユーティリティ
    - utils.process_priority: プロセス優先度設定と CPU affinity のユーティリティ。Windows / POSIX を吸収し、アクセス権限エラー等は警告に落とすように安全設計。

Changed
- ログ・挙動に関する設計決定を明記
  - run_monitoring/run_execution: 起動直後にプロセス優先度を "high" に設定する処理を追加（set_process_priority を使用）。これにより運用環境での優先度調整を簡素化。
  - run_execution: paper_trading 環境では paper_sqlite_path を用いて DB を完全に分離する設計とした（本番テーブルに影響を与えない）。
  - config._load_env_file: .env の読み込み順と上書きルール（OS 環境変数保護）を明確化。読み込み失敗時は警告を出して継続。
  - portfolio.position_sizing: aggregate cap / スケーリング処理を実装し、残余キャッシュで端数（lot 単位）を追加配分するアルゴリズムを導入（再現性のため安定ソート順を使用）。
  - research.feature_exploration.calc_forward_returns: horizons のバリデーションを追加（正の整数かつ <= 252）。
  - ai.news_nlp: スコアリング処理の堅牢化方針（チャンク送信、トークン肥大化対策、フェイルセーフ設計、部分置換）を明示。

Fixed
- .env パーサの改善
  - コメント処理・クォート内のエスケープ、export プレフィックス対応などを実装し、より多様な .env 形式に対応。
- Settings のバリデーション強化
  - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の値検査を追加し、不正な値は ValueError を送出して早期検出するようにした。
- DB 周りの堅牢性向上
  - tools.paper_verification_report: 該当テーブルが存在しない場合に sqlite3.OperationalError を捕捉してデフォルト値でレポートを生成（ツールが異常終了しないように保護）。

Notes / Implementation details
- プラットフォーム差異吸収
  - utils.process_priority は Windows と POSIX（Linux, macOS, FreeBSD）を考慮し、対応外 OS は警告でスキップ。権限不足などの例外は警告に落とす設計。
- 安全停止メカニズム
  - run_monitoring/run_execution はプロジェクト直下 data/stop_requested.flag (および実行用 PID ファイル path) を用いたファイルベースの停止指示に対応。これにより外部から安全にプロセスを停止できる。
- Paper Trading の分離
  - paper_trading 環境向けに PAPER_TRADING_SQLITE_PATH と PAPER_FILL_MODE を導入し、挙動やデータを本番と明確に切り分け可能にしている。
- DuckDB / SQLite の共存
  - 解析用途（research, ai）は DuckDB を利用し、高速な分析クエリを想定。runtime/監視用データは SQLite（monitoring / paper_trading）を使用する設計。

今後の予定（案）
- ai.news_nlp の API 呼び出し・レスポンス処理の実装完了（ファインチューニング、冪等性・一貫性の更なる強化）。
- ExecutionEngine 周り（EngineConfig / Reconciler / RiskManager）の詳細ユニットテスト追加。
- portfolio の lot_size 銘柄別対応（stocks マスタからの取得）や手数料推定ロジックの導入。
- DuckDB への書き込み/マイグレーション戦略の明確化（バージョン管理とバックアップ方針）。

License
-------
（ライセンス情報をここに記載してください）

----

この CHANGELOG はコードベースからの推測に基づき作成しています。追加のコミット履歴やバージョン計画があれば、適宜更新してください。