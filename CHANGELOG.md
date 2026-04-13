Keep a Changelog 準拠 — 変更履歴 (日本語)
※コードベースの内容から推測して作成しています。実装コメントや docstring に基づく説明を含みます。

Unreleased
- ドキュメント / 仕様メモ
  - いくつかの箇所に TODO コメントあり（例: price フォールバック、将来的な lot_size 拡張）。
  - ai/news_nlp.py の処理は堅牢なエラーハンドリングを備えているが、運用上の監視やレート制御の追加検討推奨。

[0.1.0] - 2026-04-13
Added
- 基本パッケージ情報
  - パッケージ初期化: kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 環境設定・ロード機能 (src/kabusys/config.py)
  - .env / .env.local の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - .env ファイルの柔軟なパーサ実装（export 構文、引用符・エスケープ、インラインコメントの取り扱い）。
  - 環境変数保護機構（OS 環境変数は上書きされない）。
  - Settings クラスを提供し、J-Quants / kabu API トークン、LINE トークン、DB パス、監視設定、閾値、環境判定（development / paper_trading / live）などのプロパティを公開。
  - 値検証を追加（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の不正値は例外を送出）。

- 実行エントリ (src/kabusys/run_execution.py, src/kabusys/run_monitoring.py)
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite DB（data/paper_trading.db 等）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアント生成。OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine.run_session() を呼び出す。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義し、初期ポートフォリオ値に broker.get_available_cash() を利用。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - プロセス優先度を起動時に "high" に設定。

- 監視 DB 初期化
  - init_monitoring_db を呼んで監視テーブルの存在を保証（冪等動作）。

- DuckDB 統合
  - DuckDB 接続（duckdb.connect）をデータ分析・研究モジュールや ai モジュールで利用。

- ユーティリティ (src/kabusys/utils/process_priority.py)
  - set_process_priority(level) を実装（Windows / POSIX の差を吸収）。
  - set_cpu_affinity(cpu_count) を実装（最初の N コアに固定、権限不足や未対応環境は警告ログでスキップ）。
  - アクセス権限・未サポート API の例外は警告で扱い、失敗時に処理を継続するフェイルセーフ仕様。

- ポートフォリオ構築 (src/kabusys/portfolio/*.py)
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順でソート、上位 N を選定（同点は signal_rank でブレーク）。
    - calc_equal_weights / calc_score_weights: 等配分とスコア加重配分を実装。全スコアが 0 の場合は等配分にフォールバック（WARNING）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct）を適用して候補を除外。既存保有からセクター別エクスポージャーを算出。unknown セクターは上限適用対象外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告して 1.0 を返す。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算を実装。
    - 単元株（lot_size）丸め、max_position_pct による per-stock 上限、aggregate cap によるスケールダウン（cost_buffer を利用して保守的に見積もり）、スケール時の残差処理（lot_size 単位での再配分）を実装。
    - 価格欠損時はスキップし、ログ出力で理由を示す。

- 研究・ファクター計算 (src/kabusys/research/*.py)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算（DuckDB 上で窓関数を利用）。データ不足時は None を返す。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を慎重に扱う実装。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズンの将来リターンを一括取得（LEAD を使用）。horizons の入力検証を実装。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。レコード不足や定数分散の場合は None を返す。
    - factor_summary / rank: 基本統計量とランク変換（同順位は平均ランク）を実装。
  - DuckDB のみに依存し、実運用口座や外部 API にはアクセスしない方針を採用。

- AI / ニュース NLP (src/kabusys/ai/news_nlp.py)
  - raw_news テーブルを対象に OpenAI（gpt-4o-mini）を用いたセンチメントスコアリングを実装。
  - 処理概要:
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）で記事を抽出（UTC 変換）。
    - 銘柄ごとに記事を集約（最大記事数・最大文字数でトリム）。
    - 最大 20 銘柄ずつバッチ送信（JSON Mode を期待）。
    - 429・ネットワーク・5xx に対して指数バックオフでリトライ。
    - レスポンス検証・スコアの ±1.0 クリップ。
    - 部分失敗を考慮し、対象コードのみを置換する形で ai_scores テーブルを更新（DELETE→INSERT の形で安全に書き換え）。
  - 実装上の配慮:
    - datetime.today()/date.today() を参照せず、target_date を明示的に受け取る（ルックアヘッドバイアス防止）。
    - API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を発生。

- ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading 検証レポート生成スクリプトを追加（CLI）。
  - 指標:
    - 稼働率（uptime）・総ポーリング数・エラー数
    - 注文成功率（Filled / Created）・送信率（Sent / Created）
    - P95 レイテンシ、平均・最大レイテンシ
    - リスク却下数（risk_logs）
  - P95 計算や日付フィルタ、DB 存在チェック、OperationalError 発生時のフォールバック処理を実装。
  - デフォルト閾値を定義（稼働率 >=99%、注文成功率 >=90% 等）し、PASS/FAIL を判定して出力。

Changed
- ログ設定
  - 各実行スクリプトで logging.basicConfig(level=logging.INFO) を採用（起動時のデフォルトログレベルは INFO）。
- DB 接続方針
  - 監視用スクリプトは環境にかかわらず本番用 sqlite_path を参照（paper_trading のみ例外で paper_sqlite_path を使用する run_execution）。

Fixed
- 環境変数の不正値処理
  - MONITOR_POLL_INTERVAL が不正（0 以下や非整数）の場合、警告ログを出してデフォルト値にフォールバック。
  - PAPER_FILL_MODE の不正値検出と例外送出。
  - KABUSYS_ENV / LOG_LEVEL の不正値検出。

Known issues / Notes
- sector_exposure の計算において price が欠損（0.0）の場合、エクスポージャーが過小評価されてブロックが外れる可能性あり。コメントに将来のフォールバック価格採用案あり。
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別拡張を検討）。
- news_nlp の OpenAI 呼び出しは運用負荷（API コスト・レート制限）に注意。ログ・再試行設定はあるが、運用監視の整備を推奨。
- DuckDB の executemany に関する制約（空パラメータ禁止）へ注意する実装配慮あり。
- 一部の箇所に機能拡張の TODO（例: price fallback, 銘柄別 lot_size）が残る。

セマンティックバージョニングの方針
- 0.1.0 は初期リリース（主要機能実装）。今後の互換性破壊変更はメジャーバージョンで管理する予定。

参考
- Keep a Changelog: https://keepachangelog.com/ja/1.0.0/ (形式に準拠して分類・記載しています)

もし特定のコミットや日付、またはより詳細な変更単位（ファイル毎に分けた履歴）が必要であれば、該当情報（コミットログ等）を提供してください。コードから推測した点や未実装の TODO についても追加で注記できます。