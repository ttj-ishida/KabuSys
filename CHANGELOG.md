# CHANGELOG

すべての注記は Keep a Changelog に準拠しています。重要な変更・追加はセクション別にまとめています。日付はリポジトリの最新状態（このコードベース）に基づく推定です。

## [Unreleased]

### Added
- 起動スクリプト: run_execution.py / run_monitoring.py を追加。
  - run_execution.py
    - ExecutionEngine 起動用のエントリポイントを実装。
    - KABUSYS_ENV=paper_trading のときは paper_trading 専用 SQLite (デフォルト: data/paper_trading.db) を使用して本番 DB と完全分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（MockBroker を含む想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。停止フラグ (data/stop_requested.flag) による安全停止処理を実装。
    - 実行中に PID ファイルを書き出す仕組みを想定（pid ファイルパスを設定可能）。

  - run_monitoring.py
    - SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する挙動を明記。
    - 停止フラグ検知および例外耐性（check_once() で例外が発生してもループ継続）を実装。

- 設定管理: src/kabusys/config.py
  - .env 自動読み込み機能を導入（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env と .env.local の読み込み順を明確化（OS 環境変数 > .env.local > .env）。.env.local は override=True（OS 環境変数を保護）で読み込む。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パーサを強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応
    - クォートなし行のインラインコメント扱いの扱い改善
  - Settings クラスを提供し、各種環境変数（DB パス、PID/フラグパス、しきい値、PAPER_FILL_MODE 等）をプロパティで安全に取得。値検証（有効値チェック）を行う。

- ポートフォリオ構築モジュール: src/kabusys/portfolio/*
  - portfolio_builder.py: 候補選定 (select_candidates)、等金額/スコア加重の重み計算 (calc_equal_weights / calc_score_weights) を実装。スコア全0時は警告出して等金額にフォールバック。
  - risk_adjustment.py: セクター集中制限 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。未知レジームはフォールバックで 1.0。
  - position_sizing.py: 株数決定ロジック (calc_position_sizes) を実装。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、最大ポジション比率・max_utilization による制限、cost_buffer を用いた保守的なコスト見積り。
    - aggregate cap 超過時のスケーリング処理（スケーリング後に残余キャッシュで端数を lot 単位で再配分）を実装。
    - price 欠損時のスキップやログ出力などのフォールトトレランスを考慮。

- 監視 / ツール:
  - monitoring 側の DB 初期化ユーティリティ（init_monitoring_db）を参照する起動フローを導入。
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を計算して PASS/FAIL 判定を行う。
    - デフォルト閾値を明確化 (稼働率 99%, 成功率 90%, 送信率 95%, P95 レイテンシ 200ms)。
    - 日付フィルタ、DB存在チェック、SQL エラー耐性を実装。

- リサーチ / ファクター計算:
  - research/factor_research.py:
    - calc_momentum / calc_volatility / calc_value を実装。DuckDB の prices_daily / raw_financials を使い、欠損・データ不足時は None を返す安全設計。
    - MA200, ATR, turnover, volume ratio 等を計算。ウィンドウサイズやスキャンバッファを定義。
  - research/feature_exploration.py:
    - 将来リターン計算 (calc_forward_returns)、IC 計算 (calc_ic)、ファクター統計サマリ (factor_summary)、ランク変換 (rank) を実装。
    - calc_ic は有効レコードが 3 未満の場合 None を返す。
    - rank は同順位に平均ランクを割り当てる実装（丸めによる ties 検出対策あり）。

- AI ニュース NLP: src/kabusys/ai/news_nlp.py
  - OpenAI（gpt-4o-mini）を用いたニュースの銘柄別センチメントスコアリングロジックを追加（バッチ処理、トークン肥大対策、エラー時のリトライとフォールトトレランス、レスポンス検証、スコアクリッピング）。
  - calc_news_window によりターゲット日のニュースウィンドウ（JSTベース→UTC）を正確に算出。
  - 注意: ファイル末尾が切れている（コード断片あり）。主要アルゴリズムは実装されているが、完全実行に必要な内部関数（例: _fetch_articles）の続きが未含有の可能性あり。

- ユーティリティ:
  - utils/process_priority.py:
    - set_process_priority(level) 実装（Windows と POSIX を吸収）。アクセス権限失敗時に警告でスキップ。
    - set_cpu_affinity(cpu_count) 実装。利用可能コア数を考慮した安全設計。
  - パッケージ __init__ のバージョンを 0.1.0 に設定。

### Changed
- 環境変数の読み込みポリシーを明確化（.env / .env.local の優先度、OS 環境の保護、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
- run_monitoring の poll interval 取得ロジックを堅牢化。MONITOR_POLL_INTERVAL が不正（非整数・<=0）の場合はデフォルト 60 秒にフォールバックし、警告ログを出力するように変更。
- Execution 起動時の DB 選択を settings.is_paper に依存させ、paper_trading 時には専用 DB を用いるようにした（本番データ保護）。
- rank / calc_ic / factor_summary 等、統計系ユーティリティの境界条件処理（データ不足時の None / 空リスト処理）を厳密化。

### Fixed
- .env パーサでのクォート・エスケープ処理の不具合対策（引用符内のバックスラッシュエスケープ解釈、インラインコメントの扱い）。
- position_sizing のスケーリング処理での整数丸めに伴う再配分ロジックを明確化し、残余キャッシュを用いた端数処理を導入。
- CPU / プロセス優先度設定での未対応 OS の挙動を警告ログで明示し、例外ハンドリングを追加。

### Known issues / Notes
- ai/news_nlp.py は主要ロジック（ウィンドウ算出、バッチング、API レスポンス検証等）を実装しているが、ファイル末尾が切れているため完全に実行できない部分がある可能性があります（_fetch_articles 等の実装が途中で途切れている）。実運用前に該当部分の実装・テストが必要です。
- position_sizing の price 欠損時の扱いに注記（TODO: 前日終値や取得原価のフォールバック導入を検討）。
- 一部の警告・フォールバックはログ出力に依存しているため、運用環境では LOG_LEVEL の適切な設定を推奨します。

---

## [0.1.0] - 2026-04-16 (推定)
初回（ベースライン）リリース相当。上記の多くの機能を含む初期版としてまとめています。

### Added
- パッケージ基盤:
  - kabusys パッケージ初期構成（__version__ = 0.1.0）。
  - 公開 API: portfolio / research / tools / ai / monitoring / execution の主要関数を __all__ でエクスポート。
- 環境設定と読み込み:
  - Settings クラス、.env 自動読み込み（.env / .env.local 対応）、必須環境変数チェックを実装。
- 実行基盤:
  - run_execution.py（ExecutionEngine 起動フロー、paper_trading 分離、停止フラグ/PID 管理）、run_monitoring.py（SystemMonitor のポーリングループ、MONITOR_POLL_INTERVAL）を提供。
  - process_priority/set_cpu_affinity ユーティリティ。
- ポートフォリオ構築:
  - 候補選定・重み計算・リスク調整・ポジションサイズ計算ロジック一式（等金額・スコア重み・risk_based 配分、セクター上限、レジーム乗数）。
- リサーチ:
  - ファクター計算（Momentum/Volatility/Value）、将来リターン/IC/統計サマリ/ランク処理を実装。DuckDB 前提の SQL ベース設計。
- 監視/ツール:
  - monitoring DB 初期化ユーティリティ利用、paper_verification_report による Paper Trading の検証レポート生成。
- AI:
  - ニュース NLP スコアリングモジュール（OpenAI 接続、バッチング、クリッピング、再試行ロジック）を追加（ただし一部未完）。

### Changed
- （初回リリース）多数のモジュールを新規追加。

### Fixed
- （初回リリース）初期実装時に想定されるデータ不足や外部依存の失敗に備えた例外処理・フォールバックを多く導入。

---

注: 上記の変更履歴は、提供されたコードベースから機能・設計意図を推測して作成したものです。実際のコミット履歴や変更記録とは差異がある場合があります。必要であれば、実コミットログに基づく正確な CHANGELOG 生成も支援します。