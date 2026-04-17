# CHANGELOG

すべての重要な変更をこのファイルに記録します。フォーマットは "Keep a Changelog" の慣例に従っています。

全般:
- バージョン番号はパッケージの __version__ に合わせています。
- 日付はリリース日（ローカル）を使用しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-17
初回公開リリース。本リリースでは自動売買システム KabuSys のコア機能群（設定管理、実行エンジン起動スクリプト、監視、ポートフォリオ構築、リスク調整、銘柄サイズ算出、リサーチ用ファクター計算・統計、Paper Trading 用検証ツール、ニュースNLP スコアリング基盤、プロセス優先度ユーティリティ等）を追加しました。

### Added
- 基本パッケージ情報
  - パッケージ初期バージョンを追加（kabusys.__init__.__version__ = "0.1.0"）。
  - パッケージ公開用の __all__ を定義。

- 設定・環境変数管理
  - 環境変数 / .env ファイル読み込み機能を追加（kabusys.config）。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）。
    - .env / .env.local の読み込み順序を実装（OS 環境変数を保護）。
    - export 形式・クォート・エスケープ・インラインコメント対応の robust なパーサを実装。
    - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを追加し、各種設定（API トークン、DB パス、Paper Trading 設定、監視閾値、環境判定など）をプロパティとして提供。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証。

- 実行・監視ランナー
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立ててセッション実行。
    - 停止フラグ（data/stop_requested.flag）を監視し、フラグ検知時に安全停止。
    - PID ファイル（data/execution.pid）指定対応。
    - RiskManager のデフォルトパラメータ（max_position_pct 等）を設定し、初期ポートフォリオ値はブローカーから取得。
  - 監視（SystemMonitor）ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視データは一元管理）。
    - stop flag による停止制御・例外保護・KeyboardInterrupt ハンドリング。
    - DuckDB 接続サポート（統計的集計用途など向け）。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - CLI 実行可能（python -m kabusys.tools.paper_verification_report）。
    - 指定期間の system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ等を計算して人間向けレポートを出力。
    - 判定基準（閾値）を定義（稼働率 99% 等）し、PASS/FAIL を表示。
    - DB パスは --db または PAPER_TRADING_SQLITE_PATH で指定可能。
    - P95 の計算、欠損データの扱い、SQL 実行時の OperationalError の安全ハンドリングを実装。

- ポートフォリオ構築関連（純粋関数群）
  - 銘柄選定・重み計算（kabusys.portfolio.portfolio_builder）
    - select_candidates（score 降順 + tie-breaker）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重配分、全スコア = 0 の場合は等金額へフォールバック）
  - セクター集中制限・レジーム乗数（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap（既存保有比率に基づいて新規候補を除外。unknown セクターは制限対象外）
    - calc_regime_multiplier（regime に応じた資金乗数: bull/neutral/bear のデフォルトマップ、未知値は警告とフォールバック）
  - 株数決定・単元丸め・投下資金スケーリング（kabusys.portfolio.position_sizing）
    - calc_position_sizes（allocation_method: risk_based / equal / score をサポート）
    - 単元（lot_size）丸め、per-position / aggregate cap、cost_buffer（手数料・スリッページ見積り）考慮、スケールダウンおよび端数配分ロジックを実装。
    - TODO コメントとして将来の銘柄別 lot_size サポートを記載。

- リサーチ（DuckDB ベース）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - calc_volatility（ATR20、ATR%・20日平均売買代金・出来高比率）
    - calc_value（PER・ROE を raw_financials と prices_daily から算出）
    - 各関数は target_date を受け取り、DuckDB 接続を利用して高速に集計を実行。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns（複数ホライズンの将来リターンを LEAD を用いて一度に算出。horizons 検証あり）
    - calc_ic（Spearman 相関に準じたランク相関を実装、必要レコード数チェック）
    - rank（同順位は平均ランク方式で安定したランク付け）
    - factor_summary（count/mean/std/min/max/median を計算）
  - research パッケージのエクスポートを整理（zscore_normalize を含む）。

- AI ニュース NLP（基盤）
  - ニュースのセンチメントを OpenAI API（gpt-4o-mini）でスコアリングする基盤を追加（kabusys.ai.news_nlp）。
    - ニュース収集ウィンドウ計算（JST を基準とした UTC 変換）。
    - バッチング、トークン肥大化対策（記事数・文字数制限）、レスポンス検証、スコアクリップ、リトライ戦略（429/ネットワーク/5xx）設計を記載。
    - OpenAI API キーの解決ロジック（引数 > 環境変数）。
    - ai_scores へ部分更新（DELETE + INSERT）する戦略を設計（部分失敗時の保護）。
    - 実装は処理フローと多くの保護機構を整備（ただしファイル末尾で実装が途中の箇所あり、詳細は Known issues を参照）。

- プロセス制御ユーティリティ
  - process_priority（kabusys.utils.process_priority）を追加。
    - Windows / POSIX の差異を吸収して nice / HIGH_PRIORITY_CLASS を設定。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を実装。
    - 権限不足や未対応 OS の場合は警告ログを出してスキップ。

### Changed
- 初回リリースのため、既存コードの大枠を初期実装として追加。設計コメントや TODO を含めて将来の改善ポイントを明示。

### Fixed
- N/A（初回リリース）

### Known issues / Notes / TODO
- ai/news_nlp.py の末尾が現状途中で切れており、記事集約フェーズ以降の実装が未完です。API 呼び出し・レスポンス処理・DB 書き込みの最終部分は今後実装予定。
- position_sizing.calc_position_sizes の価格欠損（price が 0.0）の取り扱いに関して TODO コメントあり。フェールセーフとしてスキップするが、将来的に前日終値等へのフォールバックを検討。
- risk_adjustment.apply_sector_cap は "unknown" セクターを制限対象外とする設計だが、運用上のポリシーに応じた変更が必要な場合がある。
- DuckDB の executemany に関する注意（tools 内のコメント）: params が空のまま executemany を呼ばないよう保護が必要。
- process_priority/set_cpu_affinity は権限が必要な場合に失敗する可能性があり、失敗時はログに記録してスキップする設計です。
- run_monitoring は監視用 DB を本番 sqlite_path に固定で接続するため、監視データを分離したい場合は設定を見直してください。
- Settings は一部プロパティで環境変数の妥当性チェックを行います。運用環境で値が不正な場合は起動時に ValueError が発生します。

### Security
- 環境変数に API キー等の秘密情報を期待するため、.env ファイルの取扱いと保護に注意してください（.env.local は上書きされる設計）。
- OPENAI_API_KEY 等のキーは環境変数で設定することを推奨します。

---

今後の予定（例）
- ai/news_nlp の残実装と統合テスト
- ExecutionEngine / RiskManager の追加ユニットテスト
- DuckDB ベースのバッチ計算最適化
- portfolio モジュールのパフォーマンス・境界ケースの強化

---
  
参考:
- 実装に記載された設計文書（コメント）や TODO を優先的に参照して改善を進めてください。