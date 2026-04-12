# CHANGELOG

すべての重要な変更履歴はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

なお、内容はリポジトリ内のソースコードから推測して記載しています（コミット履歴そのままではありません）。

## [Unreleased]

- 今後の改善予定（ソース内コメントに基づく）
  - 銘柄ごとの単元株数(lot_size)を stocks マスタから取得する拡張。
  - apply_sector_cap 内で価格欠損時のフォールバック（前日終値や取得原価など）を導入してエクスポージャ計算を堅牢化。
  - news_nlp のスコア取得失敗時のログ/部分リトライや詳細なエラーハンドリング強化。
  - DuckDB に対する一部操作での空パラメータ対策・パフォーマンスチューニング。

---

## [0.1.0] - 2026-04-12

### Added
- 基本アプリケーションの初期実装を追加（KabuSys v0.1.0）。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
- 実行・監視用エントリポイントを追加。
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。環境に応じて paper_trading 用 DB を分離し、BrokerClientFactory により実ブローカ / MockBroker を切替え。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。監視処理は環境にかかわらず本番 sqlite_path を使用する設計。
- 設定管理モジュールを追加（src/kabusys/config.py）。
  - .env ファイルの自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env パーサの実装（クォート・エスケープ・export 形式・インラインコメント処理に対応）。
  - 環境変数保護: OS 環境変数を上書きしない/保護する仕組み。
  - 多数の設定プロパティを提供（DB パス、API トークン、PID/kill flag パス、閾値、環境種別判定等）と入力検証（有効値チェック）。
  - 自動ロードを無効にする KABUSYS_DISABLE_AUTO_ENV_LOAD サポート。
- 監視 DB 初期化ユーティリティ（init_monitoring_db）との統合を追加。
- Execution 関連コンポーネントの組立てと起動処理を実装。
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み合わせで run_session を実行。
  - RiskManager に対する RiskConfig のデフォルト値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を導入。
- Portfolio 構築ライブラリを追加（純粋関数群、DB 参照なし）。
  - portfolio_builder: シグナル選択 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。全スコアが 0 の場合は等配分へフォールバックし警告を出力。
  - risk_adjustment: セクター集中上限適用 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier)。未知レジームはフォールバック 1.0 として警告を出す設計。
  - position_sizing: 株数決定ロジック (calc_position_sizes) を実装。allocation_method として "risk_based", "equal", "score" をサポート。単元株丸め、per-stock 上限、aggregate キャップ（available_cash に対するスケーリング）、cost_buffer を考慮した保守的評価を実装。スケーリング時に残差を lot 単位で配分するアルゴリズムを実装。
- 研究 (research) モジュールを追加（DuckDB 接続を受ける設計）。
  - factor_research: Momentum / Volatility / Value のファクター計算を実装（MA200 乖離、ATR20、avg turnover、PER/ROE 等）。スキャン範囲やウィンドウの定義はコメントと実装で明示。
  - feature_exploration: 将来リターン計算 (calc_forward_returns)、IC（Spearman）計算 (calc_ic)、ランク関数 (rank)、ファクター統計サマリ (factor_summary) を実装。ties の扱い（平均ランク）、丸めによる ties 検出漏れ防止等に配慮した実装。
  - research.__init__ で zscore_normalize を再エクスポート。
- AI ニュース NLP モジュールを追加（news_nlp）。
  - raw_news と news_symbols から記事を集約し、OpenAI (gpt-4o-mini) を用いて銘柄ごとのセンチメントスコアを ai_scores に書き込む処理を実装。バッチ処理（最大 20 銘柄）、トークン肥大対策（記事数・文字数制限）、429/ネットワーク/5xx のリトライ（指数バックオフ）などを考慮。
  - スコアは ±1.0 にクリップ、レスポンス検証と部分書き換え（影響コードのみ DELETE→INSERT）により部分失敗時の既存データ保護を行う設計。
  - ニュース対象ウィンドウ計算ユーティリティ (calc_news_window) を実装（JST 基準、UTC 変換）。
- ユーティリティを追加。
  - process_priority: set_process_priority / set_cpu_affinity を実装。Windows / POSIX/Linux/Mac の差分吸収、権限不足や未対応 OS での警告ハンドリングを実装。
- Tools を追加。
  - paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（avg/max/P95）などを算出し、閾値に基づく PASS/FAIL 判定を行う。デフォルト DB は data/paper_trading.db。P95 算出や日付フィルタの扱いを実装。
- DuckDB と SQLite の併用を導入。
  - duckdb を analytics / research 用の高速列ストアとして利用し、SQLite を監視 / 発注ログ保存用に採用。

### Changed
- 自動読み込みする .env の優先順位を明確化（OS 環境 > .env.local > .env）。.env.local は上書き許可。
- paper_trading 環境では SQLite を分離（settings.paper_sqlite_path を使用）することで本番 DB と完全分離。

### Fixed
- .env パーサ: export キーワード、クォート内のバックスラッシュエスケープ、インラインコメント処理、空行・コメント行のスキップ等を正しく処理するよう改良。
- MULTI-platform のプロセス優先度設定において、権限がない場合でも例外をキャッチして警告ログを出し処理を継続するように改善。

### Security
- API キーや重要なトークンは Settings を通じ環境変数から取得し、未設定の場合は明確に ValueError を送出することで起動前に安全性を担保。

### Known limitations / Notes
- apply_sector_cap 内の price 欠損時の扱いについて注記あり（現状 price=0.0 で過少評価になる可能性があるため将来的にフォールバック価格を検討する TODO）。
- position_sizing は現状全銘柄共通の lot_size を想定。将来的に銘柄別 lot_map を受け付ける設計に拡張予定。
- news_nlp 内での最終的な DB 書込周りはチャンク単位での部分置換を行う設計だが、大規模失敗時の詳細リトライ戦略は今後改善予定。
- DuckDB の executemany に関する注意（空パラメータを送らないようにするなど）がコメントに含まれている。

---

（以降のリリースは本 CHANGELOG に追記してください）