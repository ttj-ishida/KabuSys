# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
頻繁にリリースする場合は、Unreleased セクションを先頭に置いてください。

## [Unreleased]

## [0.1.0] - 2026-04-13

初回公開リリース。システム全体のコア機能を実装しました。主に以下の領域を含みます。

### Added
- 全体
  - パッケージ初期バージョンを導入（kabusys v0.1.0）。
  - DuckDB / SQLite を用いたデータ基盤を利用する設計と初期実装。
- 実行・監視
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。
    - BrokerClientFactory を利用して実行環境に応じたブローカークライアントを生成（paper_trading 環境では専用の paper DB と MockBrokerClient を利用する想定）。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと実行フローを実装。
    - 実行中にプロセス優先度を "high" に設定する処理を組み込み。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - SystemMonitor を初期化してポーリングループで定期的に check_once() を呼び出す。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL でオーバーライド可能（デフォルト 60 秒）。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する仕様。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - 環境変数自動ロード機能を実装（src/kabusys/config.py）。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込み。OS 環境変数が優先され、.env.local は .env を上書き可能。
    - .env の行パーサは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントに対応。
    - Settings クラスを導入し、アプリケーションで使用する設定値をプロパティとして提供（DB パス、PID ファイル、閾値、環境種別など）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト向け）。
- ポートフォリオ構築
  - 銘柄選定・重み付け関数群（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates（スコア順で候補選定）
    - calc_equal_weights / calc_score_weights（等金額・スコア加重）
  - セクター上限適用・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap（既存ポジションに基づくセクター集中制限）
    - calc_regime_multiplier（bull/neutral/bear に基づく投下資金乗数）
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method ("risk_based", "equal", "score") に対応した株数決定ロジック
    - lot_size（単元）丸め、aggregate cap によるスケールダウン、cost_buffer による保守的見積り
- 監視・ユーティリティ
  - process priority / CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収し、nice / HIGH_PRIORITY_CLASS を利用して優先度設定を行う。
    - cpu_affinity を最初の N コアにピン留めする機能を提供。アクセス権限や未対応 OS の場合は警告を出して安全にスキップ。
- 研究（Research）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）。
    - Momentum（1M/3M/6M、MA200乖離）、Volatility（ATR20、出来高指標）、Value（PER、ROE）等の計算を DuckDB SQL で実装。
  - 特徴量探索モジュール（src/kabusys/research/feature_exploration.py）。
    - 将来リターン計算（複数ホライズン）、IC（Spearman rank）計算、ファクター統計サマリー、ランク付けユーティリティを実装。外部依存を用いず標準ライブラリのみで実装。
  - research パッケージの __all__ を整備して主要関数をエクスポート。
- AI（ニュースNLP）
  - ニュースセンチメント集計・スコアリング処理（src/kabusys/ai/news_nlp.py）。
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのスコアを ai_scores に保存する設計を実装。
    - バッチサイズ制御、記事/文字数トリム、429/ネットワーク/5xx のリトライ（指数バックオフ）、レスポンスの構造検証、スコアを ±1.0 にクリップ、部分的な書換（対象コードに限定した DELETE→INSERT）によるフェイルセーフ処理。
    - ニュース収集ウィンドウ（JST 基準）計算ユーティリティを実装（target_date に対する前日 15:00 ～ 当日 08:30 JST の範囲を UTC に変換）。
- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）。
    - 指定期間内の system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ等を集計し、閾値に基づく PASS/FAIL レポートを標準出力に出力。
    - P95 計算、日付フィルタ、DB 存在チェック、しきい値はファイル内定数として定義（稼働率 99%、等）。
- パッケージ初期化
  - kabusys パッケージの __init__ にバージョン情報（0.1.0）と主要サブパッケージを定義。

### Changed
- 設定挙動・デフォルト
  - 環境変数の既定値や取得方法を明示化（例: DUCKDB_PATH / SQLITE_PATH のデフォルトパス、LOG_LEVEL の検証）。
  - PAPER_TRADING 環境での SQLite DB 分離（paper_trading 用の専用 DB を使用）。
- モジュールの分割と責務明確化
  - ポートフォリオ構築、リスク調整、ポジションサイズ計算、研究・特徴量モジュールを分離して純粋関数（副作用なし）で実装。

### Fixed
- 環境変数パーサの堅牢性向上（config._parse_env_line）
  - export プレフィックス、クォート・エスケープ、インラインコメントの正しい扱いを追加。無効行は無視。
- MONITOR_POLL_INTERVAL の取り扱い
  - 0 以下や不正な値を入力した場合に警告を出してデフォルトにフォールバックする安全策を追加（run_monitoring._get_poll_interval）。
- PAPER_FILL_MODE の検証
  - 無効な PAPER_FILL_MODE が指定された場合に ValueError を投げるようにして早期検出を実現。
- process priority / affinity の例外ハンドリング
  - 権限不足や未実装 API に対する例外を捕捉し、警告ログでスキップするようにして起動失敗を防止。

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY から解決する実装。未設定時は ValueError を発生させて誤った公開を防止。

---

注記:
- 本リリースはコードベースから推測してまとめたものであり、実際のリリースノートと差異がある場合があります。必要であれば、各モジュールの詳細やサンプル使用法を追加で生成できます。