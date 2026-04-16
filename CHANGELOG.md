# Changelog

すべての重要な変更点を Keep a Changelog の形式に従って日本語で記載しています。  
各項目はコードベース（src/ 以下）の実装内容から推測してまとめています。

フォーマット:
- Added: 新規機能
- Changed: 挙動の改善・仕様変更
- Fixed: バグ修正・堅牢化
- Deprecated / Removed / Security: 現状該当なし

## [0.1.0] - 2026-04-16

### Added
- 全体
  - 初回公開バージョン。自動売買システム KabuSys のコア機能群を実装。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定（src/kabusys/__init__.py）。

- 実行・監視
  - 実行エントリ:
    - run_execution.py を追加。ExecutionEngine を起動するランナーを提供。
      - BrokerClientFactory 経由でブローカークライアントを作成。
      - Paper Trading 環境では専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離。
      - エンジンはスレッドで起動し、data/stop_requested.flag の検出で安全に停止できる。
      - 実行時の PID を data/execution.pid に書き込む仕組み（pid_file 参照）。
      - RiskManager のデフォルト設定を含むリスク制御の組み立てを行う。
  - 監視エントリ:
    - run_monitoring.py を追加。SystemMonitor のポーリングループを提供。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境にかかわらず本番用 sqlite_path を使用する旨の設計（監視データは一元管理）。
      - stop フラグ検知によりループを脱出。例外発生時はログ出力して次ポーリングまで待機するフェイルセーフ。

- 設定・環境変数
  - Settings クラス（src/kabusys/config.py）を実装。
    - .env 自動読み込み機構（プロジェクトルート検出ロジックを含む。.git または pyproject.toml を基準に探索）。
    - `.env` / `.env.local` の読み込み順序と上書きルール（OS 環境変数の保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - 各種プロパティ（J-Quants / kabu API / LINE / DB / 監視閾値 / 環境判定 等）を実装。
    - PAPER_FILL_MODE の値検証（instant|partial|never|reject）。
    - KABUSYS_ENV / LOG_LEVEL の入力バリデーション。

- ユーティリティ
  - process_priority ユーティリティ（src/kabusys/utils/process_priority.py）。
    - set_process_priority(level) — Windows / POSIX の差を吸収してプロセス優先度を設定。
    - set_cpu_affinity(cpu_count) — 利用コア数のピン留め（利用不可時や権限不足は警告を出して安全にスキップ）。
  - .env パーサーを強化:
    - export KEY=val 形式に対応、クォート（シングル/ダブル）の内部エスケープ処理、コメント処理の扱いを改善。

- ポートフォリオ構築（純関数群）
  - portfolio_builder:
    - select_candidates(buy_signals, max_positions) — スコア降順で候補選定（タイブレークで signal_rank を考慮）。
    - calc_equal_weights, calc_score_weights — 等金額配分・スコア加重配分（全スコア 0 の場合は等配分にフォールバックして警告）。
  - risk_adjustment:
    - apply_sector_cap(...) — セクター集中制限を適用（sell_codes を除外可能、"unknown" セクターは適用免除）。
    - calc_regime_multiplier(regime) — 市場レジームに基づく投下資金乗数（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - position_sizing:
    - calc_position_sizes(...) — 発注株数決定ロジックを実装（allocation_method = "risk_based"/"equal"/"score"）。
    - lot_size 単位丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate scaling、端数分配ロジックを実装。

- リサーチ／ファクター計算
  - research/factor_research.py:
    - calc_momentum, calc_volatility, calc_value — DuckDB を用いたファクター計算を実装（prices_daily / raw_financials テーブル参照）。200 日 MA、ATR、ボラティリティ、流動性、PER/ROE 等を算出。
  - research/feature_exploration.py:
    - calc_forward_returns — 任意ホライズンの将来リターンを計算。horizons の検証（正の整数・最大 252 日まで）。
    - calc_ic — スピアマンのランク相関（Information Coefficient）を実装（同順位は平均ランクで扱う）。
    - rank, factor_summary — ランク変換、基本統計量（count/mean/std/min/max/median）を算出。
  - research パッケージは zscore_normalize（kabusys.data.stats から）と主要関数群をエクスポート。

- AI / ニュース処理
  - ai/news_nlp.py:
    - raw_news テーブルからニュースを集約し、OpenAI (gpt-4o-mini) でセンチメントを算出して ai_scores テーブルへ書き込む設計を実装。
    - バッチサイズ、トークン肥大対策（記事数・文字数制限）、エクスポネンシャルバックオフ、レスポンス検証、スコアクリップ（±1.0）等を考慮。
    - news ウィンドウ計算（JST を基準に UTC に変換）を実装。
    - （注）ファイル終端が途中で切れているため、一部実装が未表示／継続の可能性あり。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 検証レポート生成ツールを CLI で提供（--from / --to / --db オプション）。
    - 稼働率・注文成功率・送信率・リスク却下数・レイテンシ（平均・最大・P95）を集計し PASS/FAIL 判定（閾値はファイル内定義）。
    - p95 計算用ユーティリティ、DB 存在チェック、エラー時のフォールバックを実装。

### Changed
- 設計/挙動
  - 監視プロセスは（意図的に）どの環境でも本番 sqlite_path を参照する仕様になっている旨が明記されている（監視データの一元管理目的）。
  - .env のロード優先度は OS 環境変数 > .env.local > .env。`.env.local` は OS 環境変数より下だが `.env.local` 自体は `.env` より上書きされる。
  - duckdb / sqlite の接続を必要箇所で確実に初期化・クローズするように整理（run_monitoring/run_execution）。

### Fixed / Robustness improvements
- 環境変数パーサーの堅牢化:
  - export 接頭辞、引用符内のバックスラッシュエスケープ、インラインコメントの扱い等に対応。無効行は無視。
  - 自動ロード時に読み込み失敗が起きた場合、警告を出して処理を継続。
- run_monitoring._get_poll_interval:
  - MONITOR_POLL_INTERVAL に不正値が入った場合は警告してデフォルトにフォールバック（time.sleep に 0 以下を渡すと例外になる問題への対策）。
- calc_score_weights:
  - 全銘柄スコアが 0 の場合は等金額配分へフォールバックし、警告ログを出力。
- process_priority:
  - 未対応 OS や権限不足時に警告してスキップするようにして、起動失敗のリスクを低減。
- calc_forward_returns:
  - horizons の検証を追加（正の整数かつ 252 以下）、SQL の生成でエイリアス衝突を避けるために重複を排除。
- position_sizing:
  - lot_size 単位での丸め、aggregate cap のスケーリング時の端数処理（残余キャッシュで再配分）等の安全弁実装。
- ニュース NLP：
  - API キー未設定時に明示的な ValueError を送出するようにし、キー探索順序を api_key 引数 -> 環境変数に統一。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

注記:
- 上記はソースコードから推測できる変更点・機能一覧をまとめたものです。実際のリリースノート（ユーザ向け）では、公開日や影響範囲、既知の制限・マイグレーション手順などを追記してください。
- ai/news_nlp.py は末尾で切れているため、実装の一部（記事フェッチ・API 呼び出し・DB 書き込みの完全な流れ）が未表示です。実行前に該当ファイルを確認してください。