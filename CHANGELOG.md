# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このプロジェクトはセマンティックバージョニングに従います。

※本 CHANGELOG はリポジトリ内のソースコードから機能・仕様を推測して作成しています。

## [Unreleased]

- 将来の改善・既知の注意点（ソース中の TODO / コメントに基づく）
  - セクターエクスポージャー計算で価格が欠損（0.0）の場合に過少見積もりされる問題に対するフォールバック価格（前日終値や取得原価）の導入検討。
  - 銘柄ごとの単元（lot_size）をマスタに持たせる拡張（現在は全銘柄共通の lot_size を利用）。
  - DuckDB に対する executemany の制約に対する追加の互換性検証。
  - AI（OpenAI）連携周りのオペレーションロギングや部分失敗時のロールバック戦略の強化。
  - 単体テスト・統合テストの整備（現在の実装は設計方針や例外処理に配慮しているが、テスト記述は推測に基づく）。

---

## [0.1.0] - 2026-04-13

### Added
- 初期リリース: KabuSys 0.1.0 を追加。
  - パッケージメタ情報: `__version__ = "0.1.0"` を設定。
- 設定・環境変数管理（kabusys.config）
  - .env/.env.local の自動ロード（プロジェクトルート検出: .git / pyproject.toml）。
  - export 形式・クォート・コメント混在の .env 行パースを実装。
  - 環境変数の必須チェック（_require）と各種設定プロパティ（DB パス、PID / kill flag、監視閾値、KABUSYS_ENV 判定 等）。
  - PAPER_FILL_MODE や KABUSYS_ENV / LOG_LEVEL の値検証ロジックを実装。
- 実行用スクリプト
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（不正値はデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
    - 起動時にプロセス優先度を High に設定（utils のユーティリティを利用）。
    - SQLite / DuckDB の接続初期化とリソースクローズ処理を実装。
    - 例外発生時もログ出力して次ポーリングへ継続するフェイルセーフ挙動。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper 専用 SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading 時は MockBrokerClient 想定）。
    - OrderRepository / OrderManager / Reconciler / RiskManager / ExecutionEngine の組み立てと実行フローを実装。
    - 起動時にプロセス優先度を High に設定。
- 監視周り
  - monitoring_db の初期化ユーティリティを呼び出して監視テーブルを冪等に保証。
- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder: シグナル選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア総和が 0 の場合は等配分にフォールバックし WARNING を出力。
  - risk_adjustment: セクター集中制限 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier) を実装。未知レジームは警告して 1.0 にフォールバック。
  - position_sizing: 発注株数計算ロジック（risk_based / equal / score）、単元丸め、aggregate cap（利用可能現金に合わせてスケールダウン）を実装。手数料・スリッページの概算バッファ（cost_buffer）も考慮。
  - エッジケース（価格欠損時のスキップ等）に対するログ出力を実装。
- リサーチ（kabusys.research）
  - factor_research: Momentum / Volatility / Value ファクター計算を DuckDB SQL で実装（prices_daily / raw_financials 参照）。
    - mom_1m/3m/6m、ma200 乖離、20日 ATR、20日平均売買代金、PER/ROE 等を算出。
    - 着目日付・スキャン範囲に関するバッファ考慮（営業日・カレンダーバッファ）。
  - feature_exploration: 将来リターン計算（複数ホライズン）、IC（Spearman の ρ）計算、ファクター統計サマリ、ランク付けユーティリティを実装。外部ライブラリに依存せず標準ライブラリで実装。
  - research パッケージのエクスポート整備（zscore_normalize などの公開）。
- AI: ニュース NLP スコアリング（kabusys.ai.news_nlp）
  - raw_news を銘柄ごとに集約して OpenAI API（gpt-4o-mini）にバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む処理を実装。
  - バッチサイズ、記事/文字数の上限（トリム）、429/ネットワーク/5xx に対する指数バックオフリトライ、JSON レスポンス検証、スコアの ±1.0 クリップ、部分更新（DELETE→INSERT の範囲絞り）等の堅牢化を実装。
  - API キーの解決ロジック（引数優先、環境変数 OPENAI_API_KEY を参照）と未設定時の ValueError を実装。
  - ニュースウィンドウの算出ユーティリティ（JST→UTC 変換）を提供。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し PASS/FAIL 判定を行う。
    - コマンドライン引数による日付範囲・DB パス指定をサポート。
    - P95 計算、NULL ハンドリング、DB 存在チェック、テーブル存在チェック（OperationalError を許容）を実装。
- ユーティリティ（kabusys.utils）
  - process_priority: Windows / POSIX（Linux / macOS / FreeBSD）差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを実装。アクセス権限や未対応 OS の場合は警告してスキップする。CPU affinity 設定関数も提供。
- 基盤技術
  - DuckDB をデータ処理（リサーチ・AI 集計等）に採用。
  - SQLite を監視・paper_trading 用ログに利用。

### Changed
- 環境変数読み込みの優先順位を明確化: OS 環境 > .env.local > .env。OS 環境変数は protected として自動ロードで上書きされないよう保護。
- run_monitoring: 監視実行は KABUSYS_ENV にかかわらず本番 sqlite_path を使用するよう明示（監視ログは本番 DB を対象）。
- run_execution: paper_trading 環境では SQLite のパスを切り替え、データ分離を徹底。

### Fixed
- MONITOR_POLL_INTERVAL の検証追加: 0 以下や不正値で ValueError を避け、デフォルト値へフォールバックして警告を出すようにした。
- calc_score_weights: 全銘柄のスコア合計が 0 の場合に等金額配分へフォールバックし、警告を出すようにした。
- process_priority / set_cpu_affinity: 未対応 OS や権限不足時に例外で停止しないよう例外を捕捉して警告を出す。cpu_count の引数検証を追加。

### Documentation / Design Notes
- 多くのモジュールに設計方針や注釈コメントを追加（PortfolioConstruction.md / StrategyModel.md 等の参照を想定した説明）。
- DuckDB SQL を多用し、計算ロジックは DB 内で完結させる方針を採用（外部 API への依存を低減）。
- ルックアヘッドバイアス回避のため、API / スコアリング等で datetime.today()/date.today() を直接参照しない設計方針を明記。

### Known issues / Limitations
- apply_sector_cap: price が 0.0 の場合にエクスポージャーが過少見積りされる可能性がある（TODO コメントあり）。
- position_sizing: 現状は全銘柄共通の lot_size（デフォルト 100）を想定。将来的に銘柄別単元対応が望まれる。
- news_nlp: 大量の API コールや部分失敗時の運用フロー（再試行ポリシー・監査ログ）については運用ルール策定が必要。
- DuckDB executemany に関する挙動（バージョン差分）に注意（ソース内コメントあり）。

---

（以上）