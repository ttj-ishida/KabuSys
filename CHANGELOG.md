# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
日付はコードスナップショットの作成日（2026-04-17）を使用しています。

注: バージョン番号はパッケージ内の __version__（0.1.0）に合わせています。

## [Unreleased]
- 現在未リリースの変更はありません。

## [0.1.0] - 2026-04-17

### Added
- 全体
  - 初期パブリックリリースとして以下の機能群を追加。
  - パッケージバージョン: 0.1.0

- 実行 / エンジン
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用に分離された SQLite DB（data/paper_trading.db）を使用する。
    - プロセス優先度を起動時に "high" に設定（set_process_priority）。
    - 実行はスレッドで行い、data/stop_requested.flag による外部停止制御をサポート。
    - 実行中は execution.pid に PID を書き込む想定（pid_file のパスを設定可能）。
  - Execution 側で RiskManager / OrderManager / Reconciler 等の初期設定を行う組み立てロジックを含む。
    - RiskConfig のデフォルトパラメータ（max_position_pct, max_utilization 等）を導入。
    - RiskConfig.initial_portfolio_value はブローカからの get_available_cash() を初期値に使用。

- 監視
  - SystemMonitor のポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path を使用して監視テーブルに書き込む仕様。
    - data/stop_requested.flag による外部停止制御をサポート。

- 設定 / 環境変数
  - Settings クラスを実装（src/kabusys/config.py）。
    - .env / .env.local の自動ロード機構を実装（プロジェクトルートは .git または pyproject.toml を探索して検出）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export プレフィックス、クォート／エスケープ、コメント処理などをサポート。
    - 各種プロパティ（duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, CPU/MEM/DISK の閾値 等）を提供。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL の入力値チェック（有効値検証）を実装。

- ポートフォリオ構築
  - 銘柄選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates, calc_equal_weights, calc_score_weights を追加。
    - calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックして警告を出力。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有のセクター割合で候補除外）、calc_regime_multiplier（bull/neutral/bear に応じた乗数）を追加。
  - 発注株数計算（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes を追加。
    - "risk_based", "equal", "score" の配分方式に対応。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer を考慮した安全なスケールダウンロジックを実装。

- リサーチ / ファクター計算
  - DuckDB ベースのファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）、calc_volatility（ATR20・流動性指標）、calc_value（PER, ROE）を実装。
    - データ不足時の None 扱い等の堅牢化を行う。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns（将来リターン）、calc_ic（Spearman IC）、rank（同順位平均ランク化）、factor_summary（統計サマリ）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- AI / ニュース NLP
  - ニュースセンチメントスコアリングモジュールを追加（src/kabusys/ai/news_nlp.py）。
    - raw_news を集約して OpenAI API（gpt-4o-mini）にバッチ送信し、銘柄ごとに ai_scores テーブルへ保存する処理フローを実装。
    - API 呼び出し時のバッチサイズ、記事数/文字数のトリム、429/タイムアウト/5xx に対する指数バックオフリトライ、結果のスキーマ検証、スコアの ±1.0 クリップといった耐障害性を組み込み。
    - ニュース収集ウィンドウの計算（JST 指定 → UTC に変換）をサポートしルックアヘッドバイアスを避ける設計。
    - API キー未設定時は例外を投げる。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - CLI で期間 (--from / --to) と DB パス (--db) を指定可能。
    - system_status / trade_logs / risk_logs から uptime, 成立率, 送信率, リスク却下数, 平均/最大/P95 レイテンシを計算してレポート出力。
    - P95 計算ユーティリティ、各種閾値（稼働率 99%, 成立率 90% 等）と Pass/Fail 判定を実装。
    - DB が存在しない場合やテーブルがない場合に堅牢に N/A 処理を行う。

- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, Darwin, FreeBSD） の差分を吸収して set_process_priority(level) を提供。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアに制限可能。
    - 権限不足や未対応 OS の場合は警告を出してスキップする。

### Changed
- 設定ファイル読み込みの優先順位を明確化
  - 自動ロード順: OS 環境変数 > .env.local > .env（.env の未上書きを行った後 .env.local で上書きする挙動）
  - プロジェクトルートが特定できない場合は自動ロードをスキップする（配布環境での安全性向上）。

- DB 利用ポリシーの明示
  - 監視プロセスは環境に関係なく sqlite_path（本番監視DB）を使用する仕様であることを明記（run_monitoring）。
  - Execution は paper_trading 環境で専用の paper_sqlite_path を使用して本番DBと分離。

### Fixed
- 環境変数パースの堅牢化
  - .env パーサでクォート内のバックスラッシュエスケープ、インラインコメントの扱い、`export KEY=val` 形式への対応を実装し、不正な行は無視するよう改善。

- MONITOR_POLL_INTERVAL の不正値扱い
  - run_monitoring で MONITOR_POLL_INTERVAL が 0 以下や整数変換失敗した場合にデフォルト（60 秒）へフォールバックし、警告を出すように修正（time.sleep の ValueError 回避）。

- calc_score_weights のフォールバック
  - 全スコアが 0.0 の場合は等金額配分へフォールバックして警告を出す（ゼロ除算回避）。

- process_priority の安全な失敗処理
  - set_process_priority / set_cpu_affinity が権限不足や未実装 API に遭遇した場合に例外を上げず、警告を出してスキップするように変更。

- position sizing のスケーリング周りの改善
  - aggregate cap 適用時の丸め処理と残余キャッシュを使った lot 単位での再配分を実装し、過度な投資超過を抑制。

- research / SQL クエリの NULL 考慮
  - ATR 等の計算で high/low/prev_close が NULL の場合に true_range として NULL を扱う（カウント制御により過小評価を防ぐ）。

- ai/news_nlp の API バックオフと入力検証
  - OpenAI API 呼び出しでの 429/ネットワーク/5xx に対する指数バックオフリトライ実装と、レスポンススキーマの厳密な検証を追加、部分失敗時に既存スコアを保護するため銘柄単位で置換を行う設計。

### Security
- OpenAI API キー等の機密情報は Settings 経由で環境変数から取得することを想定。自動ロードを無効にするフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を用意し、テスト/配布時の誤読を防止。

### Internal / Other
- パッケージの __all__ とエクスポートを整理（portfolio / research モジュール）。
- ドキュメント的コメント・設計ノートを各モジュールに追加し、将来の拡張（lot_size の銘柄別化、価格フォールバック等）を注記。

---

メンテナンスや追加リリースの際は、この CHANGELOG を更新してください。必要であれば、各変更点をさらに小さなコミット単位に分解して記載することを推奨します。