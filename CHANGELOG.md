# CHANGELOG

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) の形式に準拠しています。

## [Unreleased]
- 現状なし。

## [0.1.0] - 2026-04-17
初回公開リリース。主要な機能群（監視・実行エンジン・設定管理・ポートフォリオ構築・リサーチ・ニュースNLP・ユーティリティ・ツール）を実装しました。

### Added
- アプリケーションの基本パッケージを追加
  - パッケージ情報: src/kabusys/__init__.py にてバージョンを "0.1.0" として定義。

- 実行用スクリプトを追加
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視は本番 sqlite_path を環境にかかわらず使用する実装。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を利用）。
    - 停止フラグ（data/stop_requested.flag）検知による安全終了。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB を使用し MockBrokerClient を利用して本番と完全分離。
    - ExecutionEngine の依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler）を組み立てて起動。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止、pid ファイルの取り扱い。

- 設定・環境変数管理を追加
  - src/kabusys/config.py
    - プロジェクトルート自動検出（.git / pyproject.toml 基準）と .env / .env.local の自動読み込み機能を追加。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
    - .env パーサを堅牢化（export 形式対応、クォート内のバックスラッシュエスケープ処理、インラインコメント処理、既存 OS 環境変数保護）。
    - Settings クラスを提供し、各種設定値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス、paper_trading 関連、監視閾値、ログレベル、環境種別判定等）をプロパティで取得可能に。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）や KABUSYS_ENV の検証ロジックを実装。

- ポートフォリオ構築モジュールを追加
  - portfolio_builder.py
    - select_candidates: BUY シグナルのスコアで上位 N 選択（タイブレークに signal_rank を利用）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。スコア全てが 0 の場合は警告して等分配にフォールバック。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中制限ロジック（既存保有比率に基づき新規候補を除外）。"unknown" セクターは制限適用外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を実装（bull/neutral/bear、未知レジームはフォールバック）。
  - position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数計算。損切り率・リスク率・単元株丸め・lot_size を考慮。aggregate cap 超過時のスケーリングと端数分配アルゴリズムを実装。
    - cost_buffer により手数料／スリッページを保守的に見積もる。

- リサーチ（因子・特徴量）モジュールを追加
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率を DuckDB SQL ベースで計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播制御を実装。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（最新財務レコードの取得は ROW_NUMBER ベース）。
  - research/feature_exploration.py
    - calc_forward_returns: 複数ホライズンの将来リターンを一括クエリで取得。horizons の入力検証あり。
    - calc_ic: スピアマンのランク相関（IC）を実装。データ不足時は None を返す。
    - factor_summary / rank: 基本統計量サマリとランク付けユーティリティを実装。
  - research/__init__.py で主要関数をエクスポート。

- ニュース NLP スコアリング機能を追加（初期実装）
  - ai/news_nlp.py
    - raw_news と news_symbols を集約し、OpenAI (gpt-4o-mini) を用いて銘柄ごとのセンチメントスコア（-1.0〜1.0）を ai_scores テーブルへ書き込む処理を実装（バッチ・リトライ・レスポンス検証・クリッピングを含む設計）。
    - ニュース収集ウィンドウ計算（JST ベースから UTC へ変換）を提供。
    - API キーは引数または環境変数 OPENAI_API_KEY で解決。未設定時は ValueError を投げる。
    - （注）実装ファイルはフェイルセーフ設計やトークン肥大化対策を含むが、コード断片が途中で切れている箇所があります（今後の補完予定）。

- 監視/検証ツールを追加
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシなどを集計し、閾値（稼働率 99% 等）に基づいて PASS/FAIL 判定を行う。
    - CLI: python -m kabusys.tools.paper_verification_report (--from/--to/--db)。

- DB 初期化ユーティリティ呼び出し
  - 複数スクリプトから monitoring テーブルの初期化（init_monitoring_db）を呼び出すことで、監視テーブルの存在を冪等に保証。

- ユーティリティを追加
  - utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定（Windows: HIGH_PRIORITY_CLASS / POSIX: nice 値）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未サポート環境に対する安全なフォールバック（警告ログ）を実装。

### Changed
- DB 関連の分離ポリシーを明確化
  - monitoring（run_monitoring）は環境にかかわらず本番 sqlite_path を使用する仕様に明示。
  - 実行エンジン（run_execution）は paper_trading 環境時に専用の paper_sqlite_path を使用して本番 DB と分離。

- .env 読み込み優先順位
  - OS 環境変数 > .env.local > .env の優先順で読み込む実装に変更（.env.local は上書き可能）。

### Fixed
- .env パースの堅牢化
  - export 句・クォート内のバックスラッシュエスケープ・インラインコメントの扱い等、一般的な .env 記述のパターンに対応（破壊的な値取り込みを回避）。

### Known issues / Notes (既知の注意点)
- ai/news_nlp.py がファイル末尾で途中で切れている箇所があり、記事取得後の処理フローの一部が未完です。OpenAI へのリクエスト送信や DB 書き込み部分は既存の設計に従って補完が必要です。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があるため、price フォールバック（前日終値や取得原価）の導入が TODO として残っています。
  - 単元株（lot_size）に関しては将来的に銘柄別対応に拡張する旨の注記あり。
- run_monitoring と run_execution は起動時にプロセス優先度を上げようと試みますが、権限や実行環境によっては失敗し警告ログにフォールバックします。

### Migration / 環境変数メモ
- 新規に使用／期待される主な環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY
  - KABUSYS_ENV (development | paper_trading | live)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading の振る舞い選択
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
  - KABYSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読込無効化（1 で無効）
  - LOG_LEVEL 等（詳細は Settings プロパティ参照）
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基に行われます。CI / テスト時に自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

### Security
- 現時点で重大なセキュリティ修正は含まれていません。API キーやパスワード等の秘匿情報は環境変数経由で管理する設計です。

---

今後の予定:
- ai/news_nlp.py の未完部分の実装完了（API 呼び出し／DB 書き込みの確定処理・部分失敗時の保護ロジックの追加）。
- position_sizing の価格フォールバック実装（前日終値等）。
- 単元株 size（lot_size）の銘柄別対応（stocks マスタ導入）。
- さらに詳細なテストケースとドキュメントの追加。