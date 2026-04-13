# CHANGELOG

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
注: 以下は提示されたソースコードから機能・修正点・既知事項を推測して作成したリリースノートです。

## [0.1.0] - 2026-04-13

### 追加 (Added)
- 全体
  - 初期リリース相当の機能群を追加。パッケージバージョンを __version__ = "0.1.0" に設定。

- 実行／監視ランナー
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - 環境に応じて paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用する仕組みを導入（KABUSYS_ENV=paper_trading 時）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository／OrderManager／RiskManager／Reconciler の組み立て、ExecutionEngine.run_session の起動を実装。
    - duckdb と sqlite の接続管理（クローズ処理含む）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書きをサポート（デフォルト 60 秒、妥当性チェックあり）。
    - 監視は環境に依らず本番 sqlite_path を参照する設計。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - kabusys.config.Settings を実装。
    - .env/.env.local の自動読み込み（OS 環境変数の保護、読み込み順序: OS > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
    - 各種設定プロパティを提供（J-Quants / Kabu API / LINE / duckdb/sqlite パス / paper_trading 用パス / 監視・閾値設定 / PID/KILL フラグなど）。
    - KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE に対する入力検証を追加。

- ポートフォリオ構築（pure functions）
  - kabusys.portfolio:
    - portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights を追加（スコア順ソート、同点タイブレークなど）。
    - position_sizing: calc_position_sizes を追加（risk_based / equal / score の配分方式、lot_size 単位丸め、aggregate cap スケーリング、cost_buffer 考慮）。
    - risk_adjustment: apply_sector_cap（セクター集中上限の適用）、calc_regime_multiplier（market regime による投下資金乗数）を追加。

- 研究（Research）モジュール
  - kabusys.research:
    - factor_research: calc_momentum, calc_volatility, calc_value を実装（DuckDB を用いた SQL ベースのファクター計算）。
    - feature_exploration: calc_forward_returns, calc_ic（Spearman ランク関係式）, factor_summary, rank を実装。
    - re-export: zscore_normalize を kabusys.data.stats から再エクスポート。
  - 全関数は DuckDB 接続を受け取り prices_daily / raw_financials 等のテーブルを参照する設計（外部 API 依存なし）。

- AI/ニュース NLP
  - kabusys.ai.news_nlp を追加。
    - OpenAI（gpt-4o-mini）を用いてニュース記事を銘柄ごとにセンチメントスコア（-1.0〜1.0）化し、ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST → UTC で範囲化）を提供。
    - 銘柄ごとに記事を集約し、バッチ（最大 20 銘柄）で API に送信、429/ネットワーク/5xx は指数バックオフでリトライ。
    - レスポンスバリデーション、スコアの ±1.0 クリッピング、部分失敗時の既存データ保護（DELETE→INSERT の範囲限定）を組み込み。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で指定。未設定時はエラー。

- ユーティリティ
  - kabusys.utils.process_priority を追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を考慮した set_process_priority（high/normal/low）を実装。権限不足時は警告してスキップ。
    - set_cpu_affinity を実装（最初の N コアに固定、権限不足や未対応 OS は警告してスキップ）。

- ツール
  - kabusys.tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。
    - 稼働率・注文成功率・送信率・P95 レイテンシなどを集計し PASS/FAIL を判定するレポートを標準出力へ出力。
    - 日付フィルタ（--from / --to）と --db オプションをサポート。
    - p95 計算ユーティリティ、各種フォーマット関数を実装。

- DB/監視補助
  - monitoring.monitoring_db.init_monitoring_db をランナーで呼び出して監視用テーブルの存在を保証（冪等）するように統一。

### 変更 (Changed)
- DB の扱い
  - run_monitoring: 監視は環境変数にかかわらず本番 sqlite_path を使用する設計に統一（監視データは本番 DB に記録する想定）。
  - run_execution: paper_trading 環境では paper_sqlite_path を優先して使用し、本番 DB とデータを分離。

- .env 読み込み
  - 自動ロード時に OS 環境変数を保護するため protected set を導入（.env/.env.local の上書きを制御）。
  - export KEY=val 形式、クォート文字列内のバックスラッシュエスケープ、インラインコメント処理等に対応。読み込み失敗時は警告を出すが処理継続。

- エラーハンドリング / フェイルセーフ
  - news_nlp: API 呼び出し失敗はリトライとフェイルセーフ（チャンク単位で失敗しても他チャンクは継続）。
  - run_monitoring: monitor.check_once() 内の例外をキャッチしてログ出力し、次のポーリングへ継続するように変更。
  - paper_verification_report: テーブルが存在しない場合でも各集計は sqlite3.OperationalError を捕捉して N/A 等で扱うように実装。

### 修正 (Fixed)
- 環境パースの堅牢化
  - _parse_env_line において空行・コメント・export プレフィックス・クォート処理・インラインコメントの扱いの不整合を解消。

- ランキング処理の安定化
  - feature_exploration.rank: 同順位の平均ランク処理を round(..., 12) による丸めで浮動小数の ties 漏れを防止するように実装（再現性向上）。

### 注意事項 / 既知の問題 (Notes / Known issues)
- apply_sector_cap
  - price が欠損（0.0）の場合にエクスポージャーを過少見積もる可能性があり、将来的に前日終値や取得原価等のフォールバックを導入する予定（TODO コメントあり）。

- process_priority / set_cpu_affinity
  - 権限不足やプラットフォーム非対応時は設定がスキップされる。ログに警告を出力するのみで処理は継続する。

- news_nlp
  - OpenAI 関連は外部 API 呼出しが発生するため API キー管理、レート制限、コストに注意。
  - JSON Mode のレスポンス強制やバリデーションを行うが、外部 API の挙動変更には脆弱となり得るため運用監視が必要。

- DuckDB executemany
  - DuckDB のバージョン依存の制約への対策（executemany 前に params が空でないことを確認）が導入されているが、実環境での互換性確認が必要。

- 設定の妥当性チェック
  - KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE には厳密なバリデーションを導入しており、不正値は ValueError を送出する。デプロイ前に環境変数の確認を推奨。

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- 特に該当なし。ただし OpenAI API キーや外部サービスの認証情報の取り扱いには注意。

---

もし必要なら、以下の補助情報も作成します:
- リリースノート英語版
- 重要な環境変数一覧（説明付き）
- デプロイ/運用時のチェックリスト（DBパス、OPENAI_API_KEY、KABUSYS_ENV 等）