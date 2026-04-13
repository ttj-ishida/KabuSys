# Changelog

すべての変更は Keep a Changelog の形式に従います。  
タグ付けは [Semantic Versioning](https://semver.org/) に基づきます。

## [0.1.0] - 2026-04-13

### Added
- 初期リリース。KabuSys 自動売買フレームワークのコア機能を追加。
- 実行・監視用エントリポイントスクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は専用の paper_sqlite_path（data/paper_trading.db デフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory を用いて本番 / モックのブローカークライアントを切り替え。
    - ExecutionEngine の起動前に OrderRepository, OrderManager, RiskManager, Reconciler を組み立て。
    - engine.run_session() 実行後に SQLite / DuckDB 接続を確実にクローズ。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒、1 秒未満や不正値はデフォルトにフォールバック）。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視データを常に本番 DB に記録）。
    - 起動時にプロセス優先度を "high" に設定（process_priority ユーティリティを利用）。
    - KeyboardInterrupt を捕捉して安全にループ終了。

- 設定管理
  - config.py:
    - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して決定）。
    - .env パーサの強化（export 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等に対応）。
    - 環境変数保護（OS 環境変数は .env.local で上書き不可にする仕組み）。
    - Settings クラスを提供し、J-Quants / kabuAPI / LINE / DB path / 監視設定 / システム設定等のプロパティを集約。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加。
    - 環境変数値の検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順で候補選定（signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 重み計算（スコア合計が 0 の場合のフォールバックと警告）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限の適用（既存保有を考慮し、売却予定コードは露出計算から除外）。
    - calc_regime_multiplier: 市場レジームに応じた投入資金乗数（bull/neutral/bear のマップ、未知レジームはフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に応じた株数計算。  
      - 単元株丸め、per-stock 上限、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積）対応。
      - 利用可能現金を超える場合のスケールダウンと残差処理（lot 単位で再配分）。

- 研究・ファクター計算
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の計算。
    - calc_volatility: ATR20、ATR 比率、20日平均売買代金、出来高比の計算。
    - calc_value: PER / ROE の計算（raw_financials から最新レコードを取得）。
    - 設計方針: DuckDB 接続を受け、prices_daily/raw_financials のみ参照し外部 API に依存しない。
  - research.feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）計算。horizons の検証（整数かつ 1〜252）。
    - calc_ic / rank / factor_summary: Spearman ランク相関（IC）、ランク付け（同順位は平均ランク）、基本統計量サマリ。
    - pandas 等に依存せず標準ライブラリで実装。

- AI ニュース NLP
  - ai.news_nlp:
    - raw_news と news_symbols を集約し、OpenAI (gpt-4o-mini) を用いて銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込み。
    - バッチ処理（最大 20 銘柄/回）、記事・文字数トリム（最大 10 記事・3000 文字/銘柄）。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、レスポンス検証、スコアを ±1.0 にクリップ。
    - API キー未設定時は ValueError を送出。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない設計（target_date ベース）。
    - 部分失敗時に既存スコアを保護するため、更新は対象コードに限定した DELETE → INSERT の置換方式を採用。

- 運用ツール
  - tools.paper_verification_report:
    - Paper Trading 検証レポート生成スクリプトを追加（コマンドライン実行可能）。--from/--to/--db オプション対応。
    - 指標: 稼働率 (uptime)、注文成功率、送信率、P95 レイテンシ、リスク却下数 等。
    - P95 計算、各種 SQL クエリとフォールバック（テーブル未存在時に安全に N/A 表示）。
    - 基準値を定義し PASS/FAIL 判定を出力。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority(level): Windows / POSIX の差分を吸収して優先度を設定（例外時は警告でスキップ）。
    - set_cpu_affinity(cpu_count): プロセスを最初の N コアにピン留め（権限不足等は警告でスキップ）。

- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を追加。

### Changed
- n/a（初回リリースのため変更履歴は含まれません）

### Fixed
- n/a（初回リリースのため修正履歴は含まれません）

### Security
- ai.news_nlp: OpenAI API キーは引数または環境変数 OPENAI_API_KEY で提供する必要があり、未設定時は明示的なエラーを出すことで不注意な情報漏洩や未認証リクエストを防止。

### Notes / Implementation details / 注意点
- .env 読み込みはプロジェクトルート検出に依存するため、配布後やインストール先で動作させる際は .git / pyproject.toml が無い場合は自動読み込みがスキップされる点に注意。
- run_monitoring は監視データを常に本番 sqlite_path に記録するため、テスト用に監視データを別にしたい場合はプロセス起動前に環境変数や設定を調整する必要があります。
- position_sizing の lot_size は現状グローバル共通の想定（将来的に銘柄別に拡張予定の注釈あり）。
- research モジュールは DuckDB に依存し、prices_daily/raw_financials 等のテーブル構造に依存するためデータ投入側とスキーマ運用を合わせる必要があります。
- ai.news_nlp は API エラー時にリトライするが、最終的にスコア取得が出来ない銘柄はスキップされる設計（フェイルセーフ）。

---

今後のリリースでは、テストカバレッジ、ドキュメント（API・設計書）や運用周りの改善、銘柄ごとの lot_size マスタ対応、より細かなエラーハンドリングやメトリクス出力（Prometheus 等）を予定しています。