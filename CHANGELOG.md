# Changelog

すべての変更は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に準拠しています。  
このファイルはソースコードの内容から推測して作成した変更履歴です。

## [Unreleased]

- ドキュメント・注記の追加
  - モジュールごとの設計方針・注意事項（look-ahead バイアス回避、将来の拡張 TODO 等）をドキュメント文字列に追記。
  - 一部関数に挙動や入力検証に関する説明を強化。

- テスト・運用上の改善（予定）
  - .env 自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を用いた環境制御の確認。
  - OpenAI API 呼び出しのリトライ・バックオフ挙動の負荷試験。

---

## [0.1.0] - 2026-04-12

### Added
- 基本機能の初期実装（初期リリース）
  - パッケージメタ情報: kabusys v0.1.0 を導入。
- 実行エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - BrokerClientFactory を用いたブローカークライアント生成（paper_trading 時は MockBroker を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - Paper Trading 用に本番 DB と分離された SQLite パス（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用。
    - デフォルトの RiskConfig を定義（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - config.Settings: 環境変数と .env/.env.local の自動読み込み機能を実装。
    - プロジェクトルートを .git または pyproject.toml から探索して .env を自動ロード（必要に応じて無効化可）。
    - .env のパースを強化（export に対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理など）。
    - 各種環境変数の検証とデフォルトを定義（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
    - データベース・監視関連パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH）をプロパティで提供。
- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder: 候補選定（select_candidates）・等配分（calc_equal_weights）・スコア加重（calc_score_weights）。
    - スコア全0 の場合は等配分にフォールバックし WARN を出力。
  - portfolio.risk_adjustment: セクターキャップ適用（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）。
    - regimemap による乗数（bull=1.0, neutral=0.7, bear=0.3）、未知レジームは警告の上 1.0 にフォールバック。
  - portfolio.position_sizing: 発注株数計算（calc_position_sizes）。
    - allocation_method に "risk_based"/"equal"/"score" をサポート。
    - 単元株（lot_size）での丸め、1 銘柄上限・aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的算出、残差を用いた追加配分ロジックを実装。
- 研究・リサーチ機能（DuckDB ベース）
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200乖離の計算を DuckDB SQL で実装。
    - calc_volatility: ATR20、相対ATR、20日平均売買代金、出来高比の計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を算出。
    - いずれもデータ不足時は None を返す安全設計。
  - research.feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）を効率的に一括取得。
    - calc_ic: Spearman ランク相関（IC）を実装。サンプル数不足（<3）の場合は None。
    - rank / factor_summary: ランク付け（同順位は平均ランク）・基本統計量算出を実装。外部ライブラリに依存しない純粋実装。
  - research パッケージは zscore_normalize を data.stats からエクスポート。
- AI ニュース NLP
  - ai.news_nlp: OpenAI（gpt-4o-mini）を使ったニュースのセンチメントスコアリング機能を追加。
    - ニュースの時間ウィンドウ（前日15:00 JST〜当日08:30 JST）を厳密に計算（look-ahead バイアス回避のため datetime.today() を参照しない方針）。
    - 記事を銘柄ごとに集約し、1銘柄あたりの文字数/記事数上限（トークン肥大化対策）を実装。
    - バッチ（最大 _BATCH_SIZE=20）で API へ送信、429/ネットワーク/5xx に対して指数バックオフでリトライ。
    - レスポンスのスキーマ検証、スコアの ±1.0 クリップ、部分成功時に既存スコアを保護する UPDATE/DELETE の方針。
- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成 CLI を追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出して PASS/FAIL 判定を出力。
    - DB 存在チェック、SQLite の OperationalError を考慮したフォールバック処理を実装。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority(level) により Windows / POSIX の差分を吸収してプロセス優先度を設定。失敗時は警告を出して安全にスキップ。
    - set_cpu_affinity(cpu_count) を追加（NULL 安全、利用可能コア数超過時のフォールバック処理、権限エラー時は警告でスキップ）。

### Changed
- 設定読み込みの挙動
  - .env/.env.local の読み込み順と上書きルールを明確化（OS 環境変数を保護する protected キーの導入）。
  - .env パーサに export プレフィックスやクォート・エスケープ処理を追加して互換性を向上。
- DB/環境分離
  - Paper Trading 実行時に使用する SQLite を本番 DB と完全分離（settings.paper_sqlite_path を利用）。
  - 監視プロセスは意図的に本番 sqlite_path を使用する仕様を明示。
- ロギング／エラーハンドリング
  - run_monitoring.run のチェックループで check_once() が例外を出してもループを継続し、例外情報をログ出力して次のポーリングへ移行するよう変更。
  - OpenAI 呼び出し周り・DuckDB クエリ周りでの例外を捕捉してフォールバックやスキップを行うフェイルセーフ設計を採用。
- 算出ロジックの堅牢化
  - position_sizing のスケーリング処理において lot_size 単位での丸め・残差配分を行い、総投資額が available_cash を超える場合のスケールダウン処理を改善。
  - factor_research / feature_exploration の SQL で NULL やデータ不足を適切に扱うように変更（count 条件で None を返す等）。

### Fixed
- 環境変数のバリデーション
  - MONITOR_POLL_INTERVAL が 0 以下や非整数の場合にログ警告してデフォルトにフォールバックするよう修正（time.sleep に不正値を渡さない対策）。
  - PAPER_FILL_MODE の無効値に対して明確なエラーを投げるように検証を強化。
  - KABUSYS_ENV / LOG_LEVEL の許容値検証を追加し、不正な値で ValueError を送出するようにした。
- クロスプラットフォーム対応
  - process_priority の呼び出しで AccessDenied や未実装例外をキャッチして警告を出すように変更（運用環境でのクラッシュ回避）。
- レポート生成の堅牢化
  - tools.paper_verification_report が DB にテーブルがない場合でも例外で止まらず、該当指標を N/A として処理するように改善。
- ニュース NLP の安全性
  - OpenAI API キー未設定時に明確な ValueError を発生させるようにした。
  - スコア計算後は必ずスコアを ±1.0 にクリップして異常値を防止。

### Security
- ai.news_nlp において、スコア生成ロジックは内部で datetime.today()/date.today() に依存しない設計を採用（look-ahead バイアス対策）。  
- .env 読み込みで OS 環境変数を保護する仕組みを導入（意図しない上書きを防止）。

### Documentation
- 各モジュールに詳細な docstring を追加。使用方法、想定入力/出力、注意点（例: price 欠損時の挙動や将来の拡張点）を明記。

---

今後の予定（予定・未実装の改善点）
- position_sizing: 銘柄別の lot_size をサポートするための拡張（stocks マスタ参照）を検討中。
- ニュース NLP: API レスポンスの堅牢な部分更新ロジック・失敗時のリトライ戦略の更なる洗練化。
- モニタリング / 実行の運用監視（PID/kill flag 周り）と自動回復機能の追加検討。
- 単体テスト・統合テストの整備（DuckDB を用いた CI テスト等）。

もし特定の変更点（ファイル・関数単位）をさらに詳しく記載してほしい場合は、対象箇所を指定してください。