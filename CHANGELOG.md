# CHANGELOG

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

全般ルール:
- バージョンはパッケージの __version__ を基準にしています。
- 日付は本リリースの作成日です。

## [0.1.0] - 2026-04-13

### 追加 (Added)
- 基本アプリケーション構成
  - パッケージ初期バージョンを追加（__version__ = 0.1.0）。
  - Settings クラスを実装し、.env/.env.local および環境変数から設定値を読み込み可能に。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行う。
    - .env パーサは export 形式、クォート、インラインコメント、エスケープを考慮している。

- 実行用エントリポイント
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db など）を使用して本番 DB と完全に分離。
    - ブローカークライアントは BrokerClientFactory 経由で生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を実行。
    - RiskConfig のデフォルトパラメータ（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit breaker 等）を定義。
    - Execution 起動前に監視用テーブルの初期化を行う（init_monitoring_db）。
    - duckdb 接続を利用。

  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 例外発生時にもログを残して次のポーリングに継続するフォールトトレラントなループ。

- プロセス制御ユーティリティ
  - utils.process_priority: プロセス優先度 (high/normal/low) 設定と CPU affinity 設定関数を実装。
    - Windows と POSIX (Linux/Mac/FreeBSD) の差分を吸収。
    - 権限不足や未サポート環境では警告を出して安全にスキップ。

- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder:
    - select_candidates: シグナルのスコア降順で候補抽出（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額／スコア加重の重み計算（全スコア 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限に基づく候補フィルタリング（売却予定銘柄の除外等対応）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームはフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: 等配分 / スコア配分 / リスクベースの株数計算。lot 単位丸め、max_position_pct・max_utilization・cost_buffer を考慮した aggregate cap のスケーリングおよび端数補正ロジックを実装。

- リサーチ / ファクター計算
  - research.factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials テーブルを参照してファクターを計算。
    - モメンタム（1/3/6ヶ月リターン、MA200乖離）、ATR、平均売買代金、PER/ROE 等を算出。データ不足時は None を返す設計。
  - research.feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターンを計算（ホライズンチェックあり）。
    - calc_ic, rank, factor_summary: IC（Spearman ρ）計算、ランク付け、統計サマリを提供。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージは zscore_normalize をエクスポート（kabusys.data.stats から利用）。

- AI ニュース NLP モジュール
  - ai.news_nlp: raw_news を OpenAI (gpt-4o-mini) へ送って銘柄別センチメントスコアを ai_scores に保存するフローを実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST 相当）を計算する calc_news_window。
    - 銘柄ごとに記事を集約し、1銘柄あたり記事数と文字数を制限（トークン肥大対策）。
    - 最大 20 銘柄／バッチで API 呼び出し、429/ネットワーク/5xx 等はエクスポネンシャルバックオフでリトライ。
    - レスポンスを厳密な JSON として検証し、スコアを ±1.0 にクリップ。
    - 部分失敗に備え、更新は対象コードだけを置換する安全な書き込み戦略（DELETE→INSERT）を採用。
    - API キーは引数で渡すか環境変数 OPENAI_API_KEY を利用。未設定時は ValueError を送出。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 用検証レポート生成スクリプトを追加（CLI）。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を集計し、閾値（稼働率99%、成功率90%、送信率95%、P95<=200ms）で PASS/FAIL を判定。
    - 日付フィルタ (--from / --to) と --db オプション対応。DB 不在やテーブル欠損に対して堅牢に N/A を扱う。

- モジュール公開
  - kabusys.portfolio、kabusys.research 等で主要関数を __all__ 経由でエクスポート。

### 変更 (Changed)
- 設定の扱い
  - Settings は多数のプロパティを提供（DB パス、paper_trading 切替、各種閾値、PID/KILL ファイルパス、LOG_LEVEL の検証など）。
  - PAPER_FILL_MODE のバリデーションを追加（instant/partial/never/reject のみ有効）。

- DB 接続方針
  - 監視（run_monitoring）は常に本番 sqlite_path を使う設計（環境に依存しない監視を想定）。
  - run_execution は paper_trading 環境時に専用 SQLite を使用して本番データと分離。

### 修正 (Fixed)
- 環境ファイルパーサの堅牢性向上
  - export プレフィックス・クォート文字列内のバックスラッシュエスケープ・コメント処理を適切にハンドリングすることで .env の誤読を減少。

- プロセス優先度周りの例外処理
  - set_process_priority / set_cpu_affinity は権限エラーや未実装 API に対して警告ログを出し安全にスキップするように改善。

### 仕様上の注意点 (Notes)
- AI モジュールは OpenAI API を利用します。API キーと通信環境が必須です。API 呼び出し失敗時はフェイルセーフでスキップする設計ですが、スコアが取得できない日のデータは欠落します。
- paper_trading モードでは本番 DB には一切書き込まないよう分離設計されています（PAPER_TRADING_SQLITE_PATH）。
- run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL（秒）で調整可能。整数以外や 0 以下を指定するとデフォルト 60 秒にフォールバックして警告を出します。
- calc_position_sizes 等の関数は lot_size や price 欠損時の挙動に関する TODO コメントを含み、今後の拡張余地があります。
- datetime.today() 等の直接参照を避け、ルックアヘッドバイアス対策が考慮されている箇所があります（特に ai.news_nlp）。

### 既知の制限 (Known issues)
- price が欠損（0.0）の場合にセクターエクスポージャーが過少見積りされ得る箇所があり、将来的にフォールバック価格（前日終値や取得原価）を導入することが示唆されています（portfolio.risk_adjustment の TODO）。
- DuckDB の executemany に関する制約（空パラメータセットは実行できない）を考慮しているが、部分的な失敗時のロールバック戦略は慎重に運用する必要があります。

---

（今後の変更は Unreleased セクションとして追記してください。）