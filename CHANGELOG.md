# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- 現在未リリースの作業はありません。

## [0.1.0] - 2026-04-17
初回公開リリース。

### Added
- 実行・監視用エントリポイントを追加
  - run_execution.py: ExecutionEngine を起動するためのスクリプトを追加。paper_trading 環境では専用の SQLite (data/paper_trading.db など) と MockBrokerClient を使用することで本番 DB と完全に分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視処理は環境に依らず本番の sqlite_path を使用する設計。
  - 両スクリプトとも停止フラグ（data/stop_requested.flag 等）と PID ファイルの扱いを実装し、プロセス優先度を起動時に設定する。

- 設定管理モジュールを追加
  - config.py: .env / .env.local の自動読み込み機能（プロジェクトルート検出、OS 環境変数保護、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）を実装。複雑な .env パース（クォート、エスケープ、インラインコメント処理）に対応。
  - Settings クラスを導入して環境変数を型安全に取得するプロパティを提供（DB パス、API トークン、監視閾値、環境判定等）。
  - PAPER_FILL_MODE の厳密チェック、PAPER_TRADING_SQLITE_PATH、PID/KILL フラグ設定などをサポート。

- ポートフォリオ構築モジュールを追加（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順で BUY 候補抽出（signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装。スコア全0 の場合は警告して等配分フォールバック。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct）を計算して候補をフィルタ（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供、未知レジームは警告してフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: risk_based / equal / score の配分方式を実装。単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash 超過時のスケーリング）、cost_buffer を考慮した保守的見積り、残差に対する lot 単位での再配分ロジックなどを実装。

- 研究・リサーチ機能（DuckDB ベース）
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算（データ不足時は None）。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新財務レコードの取得ロジックを含む）。
  - research.feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得（horizons 検証・最大ホライズンに基づくスキャン範囲）。
    - calc_ic / rank / factor_summary: Spearman ランク相関（IC）計算、ランク付け（同順位は平均ランク）、ファクター統計サマリを提供。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research.__init__ で主要関数をエクスポート（zscore_normalize は data.stats からインポート）。

- AI ニュース NLP モジュールを追加（OpenAI 統合）
  - ai.news_nlp:
    - ニュース記事の銘柄別集約、OpenAI（gpt-4o-mini）へのバッチ送信、JSON レスポンス検証、スコアの ±1.0 でクリップ、ai_scores テーブルへの部分置換（DELETE → INSERT）を設計。
    - API キー解決、ニュース取得ウィンドウ（JST に基づく UTC 変換）や最大記事数・文字数トリムなどトークン肥大化対策を含む。
    - 429/ネットワーク/5xx 等に対するエクスポネンシャルバックオフリトライ、フェイルセーフ方針を記載。
    - （注）処理の一部がファイル末尾で途切れている（実装途中の可能性あり）。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 向けの検証レポート生成ツールを追加。CLI オプション（--from/--to/--db）を提供し、system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシなどを集約して PASS/FAIL 判定（しきい値: uptime 99%、fill_rate 90%、send_rate 95%、P95 latency 200 ms）を出力。
    - レポートは DB 存在チェック、SQL の例外耐性を考慮して実装。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority: Windows と POSIX（Linux/Mac/FreeBSD）両対応でプロセス優先度を設定するユーティリティを追加。アクセス権限不足や未対応 OS 時は警告してスキップ。
    - set_cpu_affinity: 指定コア数への CPU affinity 固定機能を追加（例外ハンドリングあり）。

- DB/モニタリング
  - monitoring.monitoring_db の初期化呼び出しを run_* スクリプトに追加し、監視テーブルの存在を保証する（冪等性）。
  - DuckDB 接続を研究・AI モジュールや実行エンジンに逐次注入する設計を採用（duckdb_path 設定経由）。

### Changed
- 設定読み込みの挙動改善
  - .env のパースを強化（export プレフィックス、クォート・エスケープ・インラインコメントの取り扱い、既存 OS 環境変数の保護）。
  - 読み込み優先度を OS 環境 > .env.local > .env に明示。

- 実行/監視プロセスの運用性向上
  - 起動時にプロセス優先度を上げる処理を追加（set_process_priority("high")）。
  - 停止フラグ確認ロジックや PID ファイルパスの扱いを統一。

- ポートフォリオ関連の現実運用配慮を追加
  - 単元株丸め・コストバッファ・max_utilization による aggregate cap スケールダウン処理など、実運用での端数・コストを考慮した実装に変更。

### Fixed
- env パーサーの不具合回避
  - .env のクォート内におけるバックスラッシュエスケープやインラインコメント誤認を解消する処理を導入して、環境変数読み込みの信頼性を向上。

### Known issues / Notes
- ai/news_nlp.py の末尾が途中で切れており、記事取得（_fetch_articles）や API 呼び出し部分の詳細実装が未完の可能性があります。動作させる前に実装の続きとテストが必要です。
- run_monitoring は監視用 DB に常に本番 sqlite_path を使用します。意図しない環境での挙動を避けるため、環境変数設定の確認を推奨します。
- position_sizing の価格フォールバックは現状未実装（price_map 欠損時の挙動に TODO が残っています）。

---

この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴や設計ドキュメントがある場合は、それらを参照して差分を補完してください。