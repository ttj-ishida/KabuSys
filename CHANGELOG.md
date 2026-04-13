CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に準拠しています。日付はコード中の実装や想定リリース日に基づいて推測しています。

## [Unreleased]
- 今後の変更予定やマイナー修正をここに記載します。

## [0.1.0] - 2026-04-13
初回リリース。日本株自動売買システム「KabuSys」の主要コンポーネントを実装しました。以下はコードベースから推測した主要な機能・修正点のまとめです。

### Added
- 全体
  - パッケージ初版を公開（バージョン: 0.1.0）。
  - モジュールを整理し、kabusys パッケージとしてエクスポート（__all__）。

- 設定管理 (src/kabusys/config.py)
  - .env 自動読み込み機能をプロジェクトルート（.git または pyproject.toml）から実行。
  - .env / .env.local の読み込み順序と上書きルールを実装（OS環境変数保護）。
  - export 形式やクォート、インラインコメント、エスケープ文字付き値などに対応した .env パーサを実装。
  - 必須環境変数チェック用のヘルパー実装（_require）。
  - 各種設定プロパティを実装（J-Quants / kabu API / LINE API / DBパス / PID/kill flag /閾値等）。
  - 環境種別チェック（development / paper_trading / live）とログレベル検証を追加。
  - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START 等の Paper Trading 向け設定を追加。

- 実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時に paper_trading 用の専用 SQLite DB を参照（data/paper_trading.db がデフォルト）し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成を導入（MockBrokerClient を利用する想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine を起動。
    - プロセス優先度を起動時に "high" に設定する処理を追加。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する仕様を明示。

- 監視 DB 初期化
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）を起動スクリプトで呼び出し、監視用テーブルの存在を保証（冪等）。

- ユーティリティ (src/kabusys/utils/process_priority.py)
  - set_process_priority(level) を実装し、Windows / POSIX の差を吸収してプロセス優先度を設定。
  - set_cpu_affinity(cpu_count) を実装し、プロセスを最初の N コアに固定可能に。
  - アクセス権限や未対応 OS の場合は警告を出してスキップするフェイルセーフ実装。

- ポートフォリオ構築 (src/kabusys/portfolio/*)
  - portfolio_builder: シグナル選定（select_candidates）と配分重み計算（calc_equal_weights, calc_score_weights）を実装。
  - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
  - position_sizing: position サイズ計算（calc_position_sizes）を実装。リスクベース配分、等配分/スコア配分に対応し、単元株（lot_size）丸め、aggregate cap スケーリング、cost_buffer を考慮した保守的推定を行う。

- リサーチ (src/kabusys/research/*)
  - factor_research: Momentum / Volatility / Value のファクター計算（calc_momentum, calc_volatility, calc_value）を DuckDB SQL を用いて実装。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC (Spearman rank) 計算（calc_ic）、ランク付け (rank)、ファクター統計サマリー (factor_summary) を実装。
  - research パッケージの __all__ に主要関数を公開。

- AI ニュース NLP (src/kabusys/ai/news_nlp.py)
  - raw_news を OpenAI（gpt-4o-mini）でセンチメントスコア化し、ai_scores テーブルへ書き込む score_news を実装。
  - ニュース収集ウィンドウの定義（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を実装（calc_news_window）。
  - バッチ処理（最大 20 銘柄/コール）、記事数/文字数上限、429/5xx/タイムアウト等に対する指数バックオフリトライを実装。
  - レスポンスのバリデーション、スコアの ±1.0 クリッピング、部分失敗時の既存スコア保護（削除 → 挿入をコード単位で限定）などのフェイルセーフ設計。

- ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading 向け検証レポート生成スクリプトを実装。
  - 稼働率（uptime）、注文成功率（fill rate）、送信率、レイテンシ（平均/最大/P95）、リスク却下数の集計と基準値比較（PASS/FAIL 判定）を出力。
  - CLI オプション --from/--to/--db をサポートし、デフォルトは data/paper_trading.db。

### Changed
- （初回リリースのため該当なし）ライブラリ構造はモジュール単位で分離し、DuckDB を解析処理のメイン DB として採用。

### Fixed / Hardened behaviours
- .env パーサはクォートやエスケープ、コメントの取り扱いを精密に実装し、誤った .env 設定による誤読を低減。
- position_sizing のスケーリング処理や余剰配分（lot 単位での追加配分）において、安全弁（_max_per_stock）や端数処理を考慮して再現性を確保。
- プロセス設定（優先度 / CPU affinity）の失敗時に例外を投げずログ警告でフォールバックするように変更（権限不足や未対応プラットフォーム対策）。
- Paper Trading 用 DB と本番 DB を分離し、テスト/検証環境でのデータ混入を防止。

### Notes / Usage
- 環境変数の自動ロードはプロジェクトルートが特定できない場合や KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されている場合はスキップされます。
- 主要な環境変数とデフォルト:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - SQLITE_PATH: data/monitoring.db（監視用本番 DB）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
  - DUCKDB_PATH: data/kabusys.duckdb
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60。1 未満の値は無効）
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
  - OPENAI_API_KEY: ai/news_nlp の利用に必要
- run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定しようとします。権限がない場合は警告が出力され、処理は継続します。
- AI ニューススコアリングは外部 API（OpenAI）に依存するため、API 利用制限やキー設定に注意してください。

### Known limitations / TODO（コード内コメントより）
- position_sizing: 銘柄ごとの lot_size を銘柄マスタから取る拡張を予定。
- apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過小評価される可能性があり、前日終値などのフォールバック価格導入を検討中。
- research モジュールは DuckDB のテーブル構成（prices_daily / raw_financials 等）に依存するため、データ品質が低い場合は一部計算が None を返す。
- ai/news_nlp: API レスポンスの完全性や JSON パース失敗時のハンドリングは堅牢化余地あり（現状はフェイルセーフでスキップ）。

---

今後のリリースでは、テストカバレッジの追加、パフォーマンス最適化、エラーメトリクスの強化、銘柄マスタ連携や単元株対応の拡張などが考えられます。必要であれば、この CHANGELOG をより細かいコミット単位で分割したり、実際のリリース日や変更者情報を追加できます。どのように改訂したいか指示してください。