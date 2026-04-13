CHANGELOG
=========

すべての変更は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に準拠して記載しています。

[0.1.0] - 2026-04-13
-------------------

Added
- 初回リリース。KabuSys のコア機能を実装。
- 実行/監視関連
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成を実装。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine.run_session() を実行。
    - プロセス起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py: システム監視ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバック）。
    - Monitoring は実行環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視データを記録。
    - プロセス優先度を "high" に設定して起動。
- 設定/環境
  - config.py: 環境変数管理モジュールを追加。
    - プロジェクトルート探索（.git / pyproject.toml を基準）に基づく .env 自動ロード（.env → .env.local、OS 環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env の行パーサは export プレフィックス・クォート文字・エスケープ・インラインコメント等に対応。
    - Settings クラスで多数のプロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視・閾値 / 環境判定等）。
    - PAPER_FILL_MODE のバリデーション（instant|partial|never|reject）。
    - PID / KILL flag 関連のパス設定や CPU/MEM/DISK のしきい値を環境変数から取得。
- 監視データベース
  - init_monitoring_db 呼び出しにより監視用テーブルの初期化を保証（冪等）。
  - DuckDB と SQLite を両方利用する設計を採用（データ処理・分析に DuckDB を活用）。
- ポートフォリオ構築
  - portfolio モジュールを追加。
    - portfolio_builder: 候補選定（score/ signal_rank によるソート）、等金額配分、スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）。
    - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジーム乗数（calc_regime_multiplier）。unknown セクターは制限対象外。
    - position_sizing: 株数決定ロジック（risk_based / equal / score）、単元株丸め、max position / aggregate cap のスケーリング、cost_buffer（手数料・スリッページ見積り）考慮。
- 研究用モジュール（Research）
  - research.factor_research: Momentum / Volatility / Value ファクター計算を実装（DuckDB 経由で prices_daily / raw_financials を参照）。
    - モメンタム: 1M/3M/6M リターン、MA200 乖離率（200行未満は None）。
    - ボラティリティ: ATR20、ATR%（ATR/close）、20日平均売買代金、出来高比率。
    - バリュー: PER（EPS が 0/欠損時は None）、ROE。
  - research.feature_exploration: 将来リターン計算（複数ホライズン一括取得）、IC（Spearman の ρ）計算、ランク変換、ファクター統計サマリー。
    - 外部依存を最小化（標準ライブラリのみ）。
- AI（ニュース NLP）
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でスコアリングし ai_scores に書き込む機能を追加。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST 相当）による記事抽出。
    - 銘柄ごとに記事を集約し、1銘柄あたり記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 最大 20 銘柄 / バッチで API コール、429/ネットワーク/5xx に対して指数バックオフでリトライ。
    - レスポンスの厳密な JSON バリデーション（results 配列・型チェック）、スコアを ±1.0 にクリップ。
    - 部分失敗時に既存スコアを保護するため、更新対象コードを限定して DELETE → INSERT（原子ではないが被害最小化の設計）。
- ユーティリティ
  - utils.process_priority: プロセス優先度設定と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX (Linux, Darwin, FreeBSD) を吸収する実装。失敗時は警告でスキップ。
    - set_cpu_affinity により最初 N コアにピンニング可能（検証・失敗時は警告でスキップ）。
- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成 CLI を追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL を判定する閾値を定義（デフォルト閾値をソース内に記載）。
    - --from / --to / --db オプション対応。DB が存在しない場合のエラーメッセージを整備。

Changed
- ロギング初期設定はスクリプト実行時に INFO レベルで basicConfig を設定（run_* スクリプト）。

Fixed
- N/A（初回リリース）

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を発生させ明示的に通知。

Notes / Implementation details
- データベース
  - DuckDB を分析用に利用、SQLite を運用データ（監視・paper_trading）に使用するハイブリッド設計。
- フォールバック/フェイルセーフ
  - 環境変数・外部 API 呼び出しの失敗は基本的にログ出力してスキップする方針（監視・実行の継続性重視）。
  - .env パーシングは幅広い表現（export、シングル/ダブルクォート、エスケープ、コメント）に対応。
- ドキュメント参照
  - 各モジュールの docstring に設計方針や参照ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）への言及あり。

今後の予定（非包括的）
- 単元株ごとの lot_size を銘柄マスタから得る拡張。
- ai.news_nlp の API エラーハンドリング強化（部分成功時のより原子的な DB 更新）。
- research/feature_exploration の高速化・大規模データ向け最適化。
- 単体テスト・統合テストの拡充。

変更点の要約が必要、もしくは特定ファイルについてリリースノートに追記したい箇所がある場合は、対象を指定して下さい。