# CHANGELOG

すべての注目すべき変更はここに記録します。  
このファイルは Keep a Changelog の形式に準拠し、セマンティックバージョニング (SemVer) に従います。

## [0.1.0] - 2026-04-13

### Added
- 初期公開: KabuSys コードベースの主要コンポーネントを追加しました。
  - パッケージメタ情報
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
  - 設定管理
    - src/kabusys/config.py
      - .env 自動読み込み（プロジェクトルートの .env / .env.local）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いをサポート。
      - 必須環境変数検査用の _require()、各種設定プロパティ（DBパス、PID ファイル、監視閾値、PAPER_FILL_MODE 等）を提供。
      - KABUSYS_ENV / LOG_LEVEL の値検証を実装（不正値は例外を送出）。
  - 実行スクリプト
    - src/kabusys/run_execution.py
      - ExecutionEngine を起動する CLI スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db）を利用して本番 DB と分離。
      - ブローカークライアントを BrokerClientFactory で生成し、OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて engine.run_session() を実行。
      - 起動時にプロセス優先度を "high" に設定。
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正な値はデフォルトにフォールバック）。
      - Monitoring は環境にかかわらず本番 sqlite_path を使用（監視データは常に統合）。
      - init_monitoring_db を呼び出して監視用テーブルの存在を保証。
  - ユーティリティ
    - src/kabusys/utils/process_priority.py
      - Windows / POSIX を吸収するプロセス優先度設定ユーティリティを追加（set_process_priority）。
      - CPU affinity 設定用 set_cpu_affinity を提供。
      - 権限不足や未サポート OS を安全にスキップする実装。
  - ポートフォリオ構築（純粋関数群）
    - src/kabusys/portfolio/portfolio_builder.py
      - select_candidates: スコア降順ソート（同点は signal_rank でタイブレーク）。
      - calc_equal_weights, calc_score_weights（全スコアが 0 の場合は等配分にフォールバックし警告を出力）。
    - src/kabusys/portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中上限チェック（当日売却予定の銘柄を除外可能、unknown セクターは上限適用しない）。
      - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear をサポート、未知は 1.0 にフォールバックして警告）。
    - src/kabusys/portfolio/position_sizing.py
      - calc_position_sizes: risk_based / equal / score の各配分方式を実装。単元株（lot_size）で丸め、1銘柄上限・aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積りをサポート。
  - リサーチ / ファクター計算
    - src/kabusys/research/factor_research.py
      - calc_momentum, calc_volatility, calc_value を実装。DuckDB の SQL を活用して prices_daily / raw_financials を参照。
      - 各関数はデータ不足時に None を返す設計、計算範囲にバッファを取る実装。
    - src/kabusys/research/feature_exploration.py
      - calc_forward_returns（複数ホライズン対応）、calc_ic（スピアマンランク相関）、factor_summary、rank を実装。外部ライブラリに依存せず純粋 Python で動作。
    - src/kabusys/research/__init__.py
      - 主要関数群と zscore_normalize をエクスポート。
  - AI ニュース NLP
    - src/kabusys/ai/news_nlp.py
      - raw_news から銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini）でセンチメント（-1.0〜1.0）を算出し ai_scores テーブルへ書き込む機能を追加。
      - 処理はバッチ（最大 20 銘柄/コール）、記事数・文字数上限、レスポンス JSON 検証、スコアを ±1.0 にクリップする等の頑健化を実装。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ実装。
      - API キーは引数または環境変数 OPENAI_API_KEY で指定（未設定時は ValueError）。
  - ツール
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading の検証レポート生成スクリプトを追加。期間指定（--from, --to）や DB パス指定 (--db) に対応。
      - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計して PASS/FAIL 判定（しきい値はソース内定義）。
      - SQLite が欠けているテーブルや DB の存在に対して堅牢性を確保（OperationalError を捕捉して N/A を返す）。
  - パッケージ初期化
    - src/kabusys/portfolio/__init__.py, src/kabusys/research/__init__.py, src/kabusys/tools/__init__.py, src/kabusys/utils/__init__.py を追加してモジュールを整理・公開。

### Changed
- アプリケーション設計上の方針・注意点を多くの docstring に明記。
  - リサーチ / AI モジュールは本番口座・発注 API にアクセスしないこと、ルックアヘッドバイアス対策（datetime.today() を直接参照しない等）を明示。
  - DuckDB を中心に SQL + Python で多くの集計を行う設計に統一。
- 環境変数の優先順位を明確化（OS 環境 > .env.local > .env）。既存 OS 環境変数は保護される実装。

### Fixed / Robustness
- run_monitoring.py
  - MONITOR_POLL_INTERVAL の不正値（負・0・非整数）に対して警告しデフォルト（60 秒）にフォールバックするように修正し、time.sleep に ValueError が伝播しないようにした。
  - 監視ループ内で monitor.check_once() が例外を投げてもループを継続し、例外をログに出力して次のポーリングへ移行するように堅牢化。
- run_execution.py
  - paper_trading 用 DB を分離し、監視テーブルの初期化 (init_monitoring_db) を冪等に呼ぶことで本番監視テーブルを壊さないようにした。
- config.py
  - .env パーサーでのクォート・エスケープ・コメント処理を改善し、実環境での誤読み込みを軽減。
  - PAPER_FILL_MODE の検証を追加（無効値は ValueError）。
- portfolio.calc_score_weights
  - 全銘柄のスコア合計が 0 の場合に等金額配分へフォールバックし warn ログを出力するように改善。
- position_sizing.calc_position_sizes
  - aggregate cap 超過時に再スケーリングして lot 単位で丸めるアルゴリズムを導入。残余キャッシュを用いた追加割当てロジックを実装して分配の再現性と保守性を向上。
- risk_adjustment.apply_sector_cap
  - unknown セクターの取り扱いを明確化（既存保有の unknown セクターは cap の対象外）。
- utils.process_priority
  - 未サポート OS、権限不足、属性未実装のケースを捕捉し、失敗時に警告ログを出して処理を継続するように変更。
- ai/news_nlp.py
  - OpenAI API 呼び出しのリトライ・バッチ処理・レスポンス検証を追加して実運用での耐障害性を高めた。
  - 空のスコア集合時は慎重に扱い（書き込みをしない・ログ出力）して部分失敗時でも既存スコアを不必要に上書きしない保護策を備えた。

### Notes / Known limitations
- DuckDB / SQLite のスキーマやテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, trade_logs, system_status, risk_logs など）は本 CHANGELOG に含まれない。ツール・モジュールはこれらのテーブルが想定どおり存在することを前提としている。
- position_sizing の lot_size は現状グローバル共通（デフォルト 100）。将来的には銘柄別ロット対応に拡張予定（TODO コメントあり）。
- news_nlp の JSON 出力は厳密に検証するため、OpenAI 側のプロンプト／モデル応答仕様の変更には注意が必要。
- 一部の機能（ExecutionEngine 本体、SystemMonitor 実装の詳細、BrokerClientFactory の具体的な実装など）は本リリースでの記述からは省略されているが、呼び出しインターフェースを用意済み。

---

将来的なリリースでは、テストカバレッジの拡充、設定のドキュメント化、銘柄別 lot_size 対応、より詳細な運用監視ダッシュボード連携などを計画しています。