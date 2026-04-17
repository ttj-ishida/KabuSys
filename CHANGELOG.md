# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
日付はリリース日を示します。

## [Unreleased]
- （未リリースの変更はありません）

## [0.1.0] - 2026-04-17
初期リリース。システム全体のコア機能（監視・実行・ポートフォリオ構築・リサーチ・ユーティリティ・AI ニューススコアリング・運用ツール類）をまとめて提供します。

### Added
- 全体
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として公開。
  - DuckDB / SQLite を用いた分析・ログ格納基盤を統合（`duckdb_path`, `sqlite_path`）。
  - 設定管理クラス `Settings` を実装。環境変数の取得・検証・デフォルト値を一元化。
  - .env 自動ロード機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。

- 実行系
  - ExecutionEngine 起動スクリプト `run_execution.py` を追加。
    - 起動時にプロセス優先度を "high" に設定する仕組みを導入。
    - Paper Trading (`KABUSYS_ENV=paper_trading`) の場合は本番 DB と分離して `data/paper_trading.db` を使用し、MockBrokerClient を利用する設計をサポート。
    - 停止フラグファイル（data/stop_requested.flag）と PID ファイル（data/execution.pid）による起動・停止制御を採用。
    - リスク管理コンポーネント（RiskManager / RiskConfig）、OrderManager、Reconciler、OrderRepository の組み立てロジックを実装。

- 監視系
  - SystemMonitor のポーリングループ起動スクリプト `run_monitoring.py` を追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視 (monitoring) は環境にかかわらず本番の `sqlite_path` を使用して稼働ログを記録。
    - 停止フラグの検出、例外発生時のログ記録、KeyboardInterrupt のハンドリングを持つ安全なループ。

- ツール
  - Paper Trading 検証レポート生成ツール `kabusys.tools.paper_verification_report` を追加。
    - 指定期間のシステム稼働率、注文成功率、送信率、リスク却下件数、レイテンシ（平均/最大/P95）を算出して標準出力にレポート出力。
    - デフォルト DB パスは `data/paper_trading.db`。`--db` オプションや環境変数 `PAPER_TRADING_SQLITE_PATH` による上書き対応。
    - 判定基準（閾値）を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。

- ポートフォリオ構築
  - `kabusys.portfolio` モジュールを追加（純粋関数群: DB 参照なし）。
    - 候補選定: `select_candidates`（スコア降順、タイブレークは signal_rank）。
    - 重み計算: `calc_equal_weights`, `calc_score_weights`（全スコアが 0 の場合は等金額配分にフォールバック）。
    - セクター制限: `apply_sector_cap`（既存保有を考慮したセクター上限除外、"unknown" セクターは上限対象外）。
    - レジーム乗数: `calc_regime_multiplier`（"bull"/"neutral"/"bear" に対応、未知値は 1.0 でフォールバック）。
    - ポジションサイジング: `calc_position_sizes`（risk_based / equal / score の allocation_method、lot_size 単位丸め、aggregate cap のスケーリング、cost_buffer を考慮）。

- リサーチ / ファクター計算
  - `kabusys.research.factor_research` を追加（DuckDB 接続を受け prices_daily/raw_financials を参照）。
    - Momentum（1M/3M/6M、MA200 乖離）、Volatility（ATR20、相対 ATR、出来高指標）、Value（PER, ROE）の計算を実装。
    - 欠損データやウィンドウ不足時の None ハンドリング。
  - `kabusys.research.feature_exploration` を追加。
    - 将来リターン計算（任意ホライズン）、IC（Spearman 相関）計算、ファクター統計サマリ、ランク付けユーティリティを実装（外部依存なし）。
    - 入力検証（horizons の範囲検査等）を実装。

- AI / ニュースNLP
  - `kabusys.ai.news_nlp` を追加（OpenAI API を利用したニュースセンチメントスコアリング）。
    - 指定ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づき raw_news を銘柄別に集約して API へバッチ送信。
    - gpt-4o-mini + JSON Mode を想定、スコアを ±1.0 にクリップ。
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライ（上限あり）。
    - API キーは引数または環境変数 `OPENAI_API_KEY` から取得。未設定時は ValueError を送出。
    - （注）ファイル末尾で処理が途中で切れている箇所があるため実装は部分的。

- ユーティリティ
  - `kabusys.utils.process_priority` を追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）で差分を吸収したプロセス優先度設定 `set_process_priority(level)` を実装（"high"/"normal"/"low"）。
    - CPU affinity 設定ユーティリティ `set_cpu_affinity(cpu_count)` を提供。
    - 権限不足や非対応 OS 時は警告を出してスキップするフェイルセーフ設計。

- 設定パーサ
  - .env パース処理を堅牢化（`_parse_env_line`）。
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いなどに対応。
    - コメント判定や無効行のスキップを実装。
  - .env ファイル読み込み関数 `_load_env_file` に `override` / `protected` オプションを導入し、OS 環境変数を保護した上で `.env.local` を上書きできる挙動を実現。

### Changed
- 設計方針（ドキュメント・実装コメントによる明示）
  - 研究・リサーチ系モジュールは外部 API にアクセスせず、DuckDB を用いたローカルデータのみで完結する設計を明確化。
  - 時刻操作において "today" を参照しない設計方針（ルックアヘッドバイアス防止）を AI ニューススコアリングモジュールで明示。

### Fixed
- 環境変数の不正値ハンドリング
  - `MONITOR_POLL_INTERVAL` が無効な数値（0 以下や非整数）の場合に警告を出しデフォルト値（60 秒）へフォールバックするように改善。
  - `PAPER_FILL_MODE` の検証を追加（有効値チェック、無効時は ValueError）。

### Security
- 環境変数の自動ロードに際し、既存の OS 環境変数を保護するため `.env` 読み込みで `protected` セットを使用（自動上書きを防止）。

### Notes / Known issues / TODO
- ai/news_nlp.py はファイル末尾で処理が途中で切れている箇所が見られ、完全実装・例外処理・DB 書き込み部分の確認が必要。
- `apply_sector_cap` は price_map に 0.0（価格欠損）がある場合、エクスポージャーが過少評価される可能性があり、前日終値等のフォールバック価格対応が TODO として記載。
- position_sizing の将来的拡張: 銘柄別 lot_size（stocks マスタ）に対応する設計拡張を検討中（現在は共通 lot_size を使用）。
- `set_process_priority` / `set_cpu_affinity` は権限不足や非対応プラットフォームでスキップするため、実行環境の権限設定に注意が必要。

### Breaking Changes
- 初期リリースのため破壊的変更はありません。

---

今後のリリースでは、AI モジュールの完全実装、単体テスト・統合テストの追加、ドキュメント（API リファレンス・運用手順）の整備、依存関係の明示的バージョン固定などを予定しています。必要であれば、この CHANGELOG を英語版やより詳細なリリースノートに展開できます。