# Changelog

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。  
バージョン番号はパッケージ内の __version__ に合わせています。

## [Unreleased]

（現在のスナップショットに基づく最新状態。リリース前の変更や小さな修正をここに追記してください。）

---

## [0.1.0] - 2026-04-16

初回リリース。本リリースでは、日本株自動売買システム KabuSys のコア機能群（構成管理、監視・実行起動スクリプト、ポートフォリオ構築、リサーチユーティリティ、ニュース NLP、ツール類、ユーティリティ）が実装されています。主な追加点は以下のとおりです。

### Added
- 基本パッケージ情報
  - パッケージメタ情報を追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。
- 設定・環境変数管理（src/kabusys/config.py）
  - .env/.env.local 自動ロード機能を実装（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサの強化：export 形式対応、引用符付き値のエスケープ処理、インラインコメント処理、無効行スキップ。
  - Settings クラスを導入し、環境変数アクセスをプロパティ化（J-Quants / kabu API / LINE / DB パス / 監視閾値 / ログレベル / 環境種別等）。
  - 環境変数の検証を追加（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE などで不正値時は ValueError）。
- 実行・監視起動スクリプト
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor の初期化・ポーリングループを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する挙動を明記。
    - 停止フラグファイル data/stop_requested.flag による安全停止検出。
    - 起動時にプロセス優先度を "high" に設定。
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - ExecutionEngine の起動ロジックを実装（スレッド実行・停止フラグ検知）。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（paper/live 実行切替を想定）。
    - 各種依存コンポーネント（OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine）を組み立てて実行。
- 監視 DB 用初期化ヘルパー呼び出し
  - 起動時に監視テーブルが存在することを保証する init_monitoring_db を呼び出し（冪等）。
- ポートフォリオ構築（src/kabusys/portfolio/*）
  - 候補選定・配分重み（portfolio_builder）
    - select_candidates（スコア降順・タイブレーク）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）
  - セクター集中制限とレジーム乗数（risk_adjustment）
    - apply_sector_cap（既存保有割合に応じて候補を除外、"unknown" セクターは除外対象外）
    - calc_regime_multiplier（"bull"/"neutral"/"bear" に対応、未知レジームは警告の上 1.0 にフォールバック）
  - 株数決定・リスク制限・単元丸め（position_sizing）
    - calc_position_sizes（allocation_method: "risk_based" / "equal" / "score"、lot_size・コストバッファ・aggregate cap に基づくスケーリングを実装）
    - 投資額の scale down（available_cash を超える場合のスケーリングと lot_size 単位での再配分ロジックを実装）
- リサーチ・ファクター計算（src/kabusys/research/*）
  - factor_research:
    - calc_momentum（1M/3M/6M リターン、MA200 乖離率、データ不足ハンドリング）
    - calc_volatility（ATR20、相対 ATR、平均売買代金、出来高比率）
    - calc_value（PER, ROE。raw_financials から直近レコードを取得）
    - DuckDB を用いた大規模データ処理設計
  - feature_exploration:
    - calc_forward_returns（任意ホライズンの将来リターン取得、入力検証）
    - calc_ic（Spearman ランク相関（IC）計算。十分なデータがない場合は None）
    - factor_summary（count/mean/std/min/max/median を計算）
    - rank（同順位は平均ランクにする実装）
  - research パッケージ __all__ に主要関数をエクスポート
- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント解析して ai_scores テーブルへ書き込むワークフロー（バッチ送信、最大記事数/文字数トリム、スコアクリッピング、リトライ、レスポンス検証、部分書き換えで既存データ保護等）。
  - ニュースウィンドウ計算ユーティリティ calc_news_window（JST ベースのウィンドウを UTC naive datetime として返す）。
  - OpenAI API キー解決と未設定時の ValueError。
  - （ファイル末尾がスナップショットで途中まで収録されていますが、主要設計方針と再試行ロジック等が実装されています）
- ツール（src/kabusys/tools）
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率 / 注文成功率 / 送信率 / P95 レイテンシ等の指標を算出し、PASS/FAIL を判定する閾値を定義（稼働率>=99%、成立率>=90% 等）。
    - 日付フィルタ、DB 存在チェック、DB からの安全なクエリ実行、P95 計算、出力フォーマットを実装。
- ユーティリティ（src/kabusys/utils/process_priority.py）
  - set_process_priority(level) を実装（Windows / POSIX の差分吸収、例外時は警告してスキップ）。
  - set_cpu_affinity(cpu_count) を追加（利用可能コア数のチェック、例外時は警告）。
  - psutil を利用した実装で、未対応 OS の場合はスキップして警告。
- DB と分析用に DuckDB を採用
  - 各所で duckdb 接続を受け取り分析処理や ai 処理を行う設計（軽量かつ高速な分析向け）。

### Changed
- 設定ロード順序を明記（OS 環境 > .env.local > .env）。.env.local は .env を上書きする。
- run_monitoring / run_execution の起動シーケンスで起動直後にプロセス優先度を設定するように統一。
- 実行スクリプトは両方とも init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等処理）。

### Fixed
- 環境変数パースの改善により、引用符内のエスケープやインラインコメントの誤取り扱いを修正。
- ポジション算出周りで price が欠損した場合のスキップやデバッグログ出力を追加し、誤発注リスクを低減。
- process_priority での例外（権限不足や未実装 API）を捕捉して警告し、プロセスがクラッシュしないように修正。

### Security
- OpenAI API キーを環境変数または引数でのみ受け取り、未設定時は明示的にエラーを出すことでキー漏洩リスクを低減する設計を採用。

### Notes / Important behaviors
- run_monitoring は監視専用 DB に常に本番の sqlite_path を使用します（KABUSYS_ENV に依存しない挙動）。paper_trading 実行時に監視を分離したい場合は設定やコードの変更が必要です。
- PAPER_TRADING_SQLITE_PATH を指定した場合、paper_trading 実行は本番 DB と完全に分離されます（run_execution の挙動）。
- MONITOR_POLL_INTERVAL に 0 以下や非整数を設定した場合、デフォルトの 60 秒にフォールバックして警告を出力します。
- calc_score_weights は全スコアが 0 の場合、等配分へ自動フォールバックして警告を出します。
- calc_regime_multiplier は未定義レジームを受けた場合に 1.0 でフォールバックし警告を出します。

---

今後の予定（例）
- ai.news_nlp のレスポンス処理と DB 書き込みロジック（ファイル断片の続き）を完成させる。
- Strategy / Execution の各コンポーネントに対する単体テスト充実。
- エラー監視・メトリクス出力の強化（Prometheus / ログ構造の改善等）。