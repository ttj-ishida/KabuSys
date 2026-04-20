# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、重要度の高い順に整理しています。

各バージョンは逆時系列（最新が上）で記載しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-20
初回リリース — KabuSys の基礎機能を実装しました。以下の主要な機能追加・設計方針を含みます。

### Added
- 全体
  - パッケージ初期版を公開（__version__ = "0.1.0"）。
  - DuckDB / SQLite を用いたデータ永続化と解析基盤の導入（デフォルトパス: data/kabusys.duckdb, data/monitoring.db）。
- 設定・環境
  - Settings クラスを実装し、環境変数経由で各種設定を提供（KABUSYS_ENV、LOG_LEVEL、DB パス等）。
  - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env パースの堅牢化: export プレフィックス、クォート付き値のバックスラッシュエスケープ、行内コメントの扱い等に対応。
  - config_setup: 対話式ウィザードで .env を生成・更新する CLI（各項目の説明・シークレット入力・デフォルト値サポート）。
  - validate_config: 起動前に .env と config/*.yaml の整合性を検査する CLI（--strict オプションで警告も失敗扱い）。
- 実行/監視ランナー
  - run_execution: ExecutionEngine の起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading 時は paper 用 SQLite を使用し、MockBroker を利用する等の本番分離を実現。
    - 停止フラグ（data/stop_requested.flag）検知により安全停止。PID ファイル出力をサポート。
    - スレッド化されたエンジン起動・監視ループ実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。不正値はデフォルトにフォールバック。
    - 監視は常に本番用 sqlite_path を使用して監視データを記録。
    - 停止フラグ検知でループを終了し、リソースをクローズ。
- ロギング / プロセス制御
  - setup_logging ユーティリティを追加。
    - stdout へ StreamHandler、日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - set_process_priority / set_cpu_affinity ユーティリティを追加（psutil を用い、Windows / POSIX の差を吸収）。
    - 起動スクリプトは起動直後にプロセス優先度を "high" に設定するように変更。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: シグナルをスコア降順でソートして候補を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（スコア総和が 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中を抑えるための候補除外処理（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear のマッピング、未知レジームは警告して 1.0 フォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数決定、単元株（lot_size）丸め、単銘柄上限・アグリゲートキャップ・スケールダウン・残余の端数処理を実装。
    - cost_buffer により手数料・スリッページを保守的に見積もるロジックを追加。
- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成 CLI を実装（PAPER_TRADING_SQLITE_PATH を使用）。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）などを計算し、定義済みの閾値に基づいて PASS/FAIL を判定。
    - P95 計算、日付フィルタ対応、DB 存在チェックを実装。
- 研究モジュール（骨組み）
  - research.factor_research: DuckDB を用いたファクター計算モジュール（モメンタム・MA200乖離・ATR・流動性等の設計と一部実装）。設計に基づく関数群の導入。

### Changed
- DB 初期化
  - 監視テーブルの初期化（init_monitoring_db）を実行時に呼び出し、存在を保証（冪等な初期化）。
- 実行環境分離
  - paper_trading 環境は paper 用 SQLite（デフォルト: data/paper_trading.db）を使用するように明確化し、本番 DB との完全分離を確保。

### Fixed / Robustness
- 環境変数パーサの堅牢化（config._parse_env_line）
  - export プレフィックス、クォート付きのエスケープ、行内コメント処理などを正しく扱うよう修正。
- MONITOR_POLL_INTERVAL の扱いを堅牢化
  - 非整数・負数・0 の値を検出してログに警告を出し、デフォルト値にフォールバック。
- ロギング周りの障害耐性強化
  - ログディレクトリ作成やファイルハンドラ作成に失敗しても、ストリーム出力のみで継続するように安全化。
- process_priority / cpu_affinity のエラー処理
  - 権限不足や未実装ケースを捕捉し、警告ログを出力して処理をスキップするように変更。
- ポートフォリオ計算のエッジケース対応
  - スコア合計が 0 の場合のフォールバック、価格欠損時のスキップ、lot_size 切り捨て後の残差処理および安全弁を実装。
- Paper verification report の空データ耐性
  - テーブルが存在しない / データ不足の場合に OperationalError を補助的に捕捉して N/A 表示にフォールバック。

### Documentation / CLI messages
- 各 CLI（config_setup / validate_config / tools.paper_verification_report / run_*）に利用方法や注意書きを追加し、ユーザー向けメッセージを充実。

### Security
- .env ファイルは生成時に「絶対に Git にコミットしないこと」と明記。
- シークレット項目は UI 上でマスク表示（config_setup）し、表示を制限。

---

注記:
- 本リリースは初期実装のため、将来的に以下の点を改善・拡張予定です:
  - position_sizing の銘柄別 lot_size 対応（stocks マスタ参照など）。
  - price 欠損時のフォールバック（前日終値や取得原価）実装。
  - research.factor_research の完全実装とテスト。
  - より詳細な単体テスト・統合テストの追加。

この CHANGELOG はコードベースから推定して作成しています。実装詳細や API 仕様の正確な文章化が必要な場合は該当モジュールのドキュメントや docstrings を参照してください。