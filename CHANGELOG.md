# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠しています。  
各バージョンの記載はコードベースから推測して作成しています。

## [Unreleased]

（現時点で未リリースの変更はありません）

---

## 0.1.0 - 2026-04-17

初期リリース（コードベースから推測）。自動売買システム「KabuSys」のコア機能群を実装しています。以下は主要な追加点・仕様・注意点の概要です。

### Added（追加）
- 全体
  - パッケージ初期バージョンを追加（kabusys.__version__ = 0.1.0）。
  - ロギングを広く利用するように実装（各モジュールで logger を利用）。
  - DuckDB / SQLite を用いたデータ処理基盤を導入。

- 設定・環境変数管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env のパースを強化（export プレフィックス対応、クォート内のエスケープ、インラインコメント処理）。
  - 環境変数上書きの振る舞いを制御可能（override / protected 機能）。
  - Settings クラスを追加し、アプリ全体で利用する設定プロパティを提供（DBパス、APIキー、閾値等）。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証を追加。無効値は ValueError。

- 実行・監視スクリプト
  - 実行エンジン起動スクリプト（run_execution.py）
    - ExecutionEngine を起動するためのエントリポイントを実装。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path を用いて本番 DB と完全分離（Paper Trading 専用 DB: data/paper_trading.db をデフォルト）。
    - BrokerClientFactory を利用して本番/モックブローカーの切り替えを実現。
    - ExecutionEngine はデーモンスレッドで run_session を実行し、外部停止フラグ（data/stop_requested.flag）検知で安全停止。
    - エンジン用 PID ファイル（data/execution.pid）をサポート。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec 等）を組み込み。

  - 監視ループ起動スクリプト（run_monitoring.py）
    - SystemMonitor のポーリングループを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト: 60 秒）。無効値はログ警告後デフォルトにフォールバック。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用（常に監視対象 DB を固定）。
    - 起動時にプロセス優先度を High に設定する処理を追加（utils.process_priority を利用）。
    - 停止フラグ検知でループを終了し、DB 接続のクローズを保証。

- ポートフォリオ構築（kabusys.portfolio）
  - 銘柄選定（portfolio_builder.select_candidates）
    - BUY シグナルをスコア降順にソートし上位 N を取得。タイブレークは signal_rank で制御。
  - 配分重み計算（calc_equal_weights, calc_score_weights）
    - 等金額配分およびスコア正規化配分を実装。スコア合計が 0 の場合は等配分へフォールバック（警告ログ）。
  - リスク補正（risk_adjustment.apply_sector_cap, calc_regime_multiplier）
    - セクター別上限（max_sector_pct）を超える場合に候補を除外するロジックを実装。sell_codes を考慮して当日売却予定銘柄を除外可能。
    - regime に応じた投下資金乗数（bull/neutral/bear）を返すユーティリティ実装（未知レジームは警告後 1.0 でフォールバック）。
  - ポジションサイジング（position_sizing.calc_position_sizes）
    - allocation_method（risk_based / equal / score）に基づき銘柄ごとの発注株数を計算。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、合計投下上限（available_cash）によるスケールダウン（スケーリング）を実装。
    - cost_buffer（手数料・スリッページの保守的見積り）を考慮した aggregate cap ロジックを実装。
    - 価格欠損時のスキップやデバッグログを実装。

- リサーチ / ファクター計算（kabusys.research）
  - ファクター計算モジュール（factor_research）
    - Momentum（1M/3M/6M、MA200乖離）、Volatility（ATR20、相対ATR、出来高比率）、Value（PER, ROE）を DuckDB SQL ベースで実装。
    - データ不足時の None ハンドリングを明示。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（複数ホライズン）、IC（Spearman ランク相関）計算、ファクター統計サマリーを標準ライブラリのみで実装。
    - ランク計算は同順位の平均ランク対応（round による ties 対策）を実装。

- ツール（kabusys.tools）
  - Paper Trading 検証レポート生成ツール（paper_verification_report.py）
    - CLI から paper_trading DB を解析し、稼働率、注文成功率、送信率、P95 レイテンシ等のメトリクスを出力。
    - パス/フェイルの閾値（稼働率 99%、成立率 90%、送信率 95%、P95 <= 200 ms）を定義。
    - DB が存在しない場合やテーブル欠損（OperationalError）への耐性を持たせた実装。

- ユーティリティ（kabusys.utils.process_priority）
  - プロセス優先度設定ユーティリティを追加（Windows / POSIX を吸収）。psutil を利用。
  - CPU affinity を最初の N コアに固定する set_cpu_affinity 関数を追加（アクセス権限により失敗時は警告でスキップ）。

- AI ニューススコアリング（kabusys.ai.news_nlp）
  - raw_news を OpenAI（gpt-4o-mini）でセンチメントスコア化し ai_scores に格納する処理を実装（バッチ、トリミング、リトライ、JSON バリデーション等）。
  - ニュース収集ウィンドウ計算、API キー解決、スコアクリップ、最大記事数/文字数の制限などを備える。
  - （注）ファイル末尾が途中で切れているため一部処理は未完または切り出し途中の可能性あり（処理の続きが存在する想定）。

### Changed（変更）
- 監視動作
  - 監視スクリプト（run_monitoring）は「環境にかかわらず本番 sqlite_path を使用」するように明示的に実装（監視対象 DB を固定化）。

- .env の読み込み優先度
  - 自動読み込み順は OS 環境変数 > .env.local > .env。既存 OS 環境変数は protected として上書きを防止。

### Fixed（修正）
- 環境変数パースの堅牢化
  - クォート内のバックスラッシュエスケープの処理、export プレフィックス対応、コメント認識の改善により .env の誤読を防止。

### Known issues / Notes（既知の注意点）
- ai.news_nlp.py はファイル末尾が切れているように見え、score_news の続き実装やエラーハンドリングの一部が未表示の可能性があります。実行前に該当モジュールの完全実装を確認してください。
- position_sizing の価格欠損（price が 0.0）によりセーフティが過少評価されるケースがある旨コメントで記載（将来的なフォールバック価格導入の TODO）。
- process_priority の設定や CPU affinity の適用は環境によって権限不足で失敗する場合があり、その場合は警告ログを出力して処理をスキップします。
- calc_forward_returns の horizons は 1〜252 の範囲で検証され、無効値は ValueError を投げます。
- run_execution では ExecutionEngine の run_session が別スレッドで実行され、外部ファイル (stop_requested.flag) を使った停止制御を行う方式。適切にフラグファイルを管理してください。

---

今後のリリースで期待される改善点（例）
- ai.news_nlp の完全実装とユニットテスト追加
- 各モジュール（特に ExecutionEngine / SystemMonitor / BrokerClientFactory 周り）の統合テスト・エンドツーエンドテスト
- position_sizing の銘柄別 lot_size 対応（TODO に記載の拡張）
- DuckDB / SQLite のスキーマ変更時のマイグレーション機構導入

（以上）