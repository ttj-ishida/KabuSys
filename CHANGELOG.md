# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」仕様に準拠します。

フォーマット:
- 変更ログはセマンティックバージョニングに従います。
- 各リリースは Added / Changed / Fixed / Removed / Security 等のカテゴリで整理します。

なお、本CHANGELOGはリポジトリ内のソースコードから推測して作成しています。実際のリリースノート作成時は必要に応じて調整してください。

## [Unreleased]

- なし（初回リリースに向けた状態）

## [0.1.0] - 2026-04-16

初期リリース。

### Added
- 全体
  - パッケージの初期バージョンを追加（kabusys.__version__ = 0.1.0）。
  - DuckDB / SQLite を利用したデータ処理基盤を実装。
- 実行用エントリポイント
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトルート/data/stop_requested.flag によって検知。
    - 監視用 DB 初期化（init_monitoring_db）と duckdb 接続を行う。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB から分離。
    - ブローカークライアント生成（BrokerClientFactory）・OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止機構と PID ファイル出力を備える。
    - 起動時にプロセス優先度を "high" に設定。
- 設定（config）
  - Settings クラスを実装し、環境変数／.env ファイルから設定を取得する共通機構を提供。
    - プロジェクトルート検出ロジック: .git または pyproject.toml を探索して自動的にルートを判定。
    - .env / .env.local の読み込み順序（OS 環境変数を保護）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。
    - 必須値取得ヘルパー _require を提供（未設定時は ValueError）。
    - 各種環境変数に対するバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
    - デフォルトパス: DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH 等。
- ポートフォリオ構築（portfolio）
  - portfolio_builder: 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を実装。
    - calc_score_weights は全スコアが0のとき等金額配分にフォールバック（WARNING ログ）。
  - risk_adjustment: セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier を実装。
    - calc_regime_multiplier のデフォルトマップ: bull=1.0, neutral=0.7, bear=0.3。未知のレジームは 1.0 でフォールバック（WARNING）。
    - apply_sector_cap は "unknown" セクターを上限適用対象外とする設計。売却予定銘柄（sell_codes）をエクスポージャー計算から除外可能。
  - position_sizing: calc_position_sizes を実装（risk_based / equal / score の allocation_method 対応）。
    - lot_size（単元）丸め、max_position_pct（1銘柄上限）、max_utilization（投下上限）、cost_buffer による保守的見積り、aggregate cap によるスケールダウン、残差配分ロジックを実装。
    - 価格欠損時は該当銘柄をスキップする挙動（ログ出力）。
- 研究（research）
  - factor_research: calc_momentum, calc_volatility, calc_value を追加（DuckDB 接続を受け取り SQL による集計を実行）。
    - momentum: 1M/3M/6M リターン、MA200 乖離を計算。データ不足時は None を返す。
    - volatility: 20日 ATR、atr_pct、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を扱う。
    - value: raw_financials から直近財務データを取得し PER / ROE を計算。
  - feature_exploration: calc_forward_returns（任意ホライズンの将来リターン計算）、calc_ic（スピアマンランク相関による IC）、factor_summary（基本統計量）、rank（平均ランク同順位処理）を追加。
    - calc_forward_returns は horizons 引数のバリデーションと一括 SQL 取得を実装。
    - calc_ic は有効レコードが 3 未満の場合 None を返す設計。
- AI / ニュース（ai）
  - news_nlp: raw_news を OpenAI API（gpt-4o-mini を想定）でセンチメント評価し ai_scores テーブルへ書き込むロジックを追加（設計・定数・ウィンドウ計算など）。
    - ニュース収集ウィンドウ: target_date の前日 15:00 JST ～ 当日 08:30 JST（UTC 変換）を採用。
    - バッチ処理、トークン肥大化対策（1銘柄あたり最大記事数 / 文字数）、結果の JSON バリデーション、スコアの ±1.0 クリッピング、429/ネットワーク/5xx に対する指数バックオフでのリトライ設計を備える。
    - OpenAI API キー未設定時は ValueError を送出する仕様。
    - （注）ソース抜粋内で記事取得処理の _fetch_articles 部分が途中までで切れているため、実装の完全性に注意が必要（コード断片由来のため、実装はリポジトリ本体を確認してください）。
- ユーティリティ（utils）
  - process_priority: set_process_priority（Windows / POSIX を吸収して Nice / Priority を設定）と set_cpu_affinity（最初の N コアに固定）を実装。
    - サポート OS: Windows および POSIX（Linux, Darwin, FreeBSD）。未対応 OS はスキップして警告。
    - AccessDenied 等の例外は警告ログでスキップするフェイルセーフ設計。
- ツール（tools）
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。
    - DB（PAPER_TRADING_SQLITE_PATH）から system_status / trade_logs / risk_logs を集計し、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを算出して標準出力へ出力。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を設定し、Pass/Fail を判定する。
    - 日付フィルタ（--from / --to）と --db オプションをサポート。

### Changed
- なし（初回リリースのため該当なし）

### Fixed
- なし（初回リリースのため該当なし）

### Documentation
- 各モジュール内に詳細な docstring と実装上の注意や TODO を追加。
  - 例: position_sizing の price 欠損時の TODO コメント、news_nlp の設計注記、config の .env パース仕様など。

### Notes / Known limitations
- news_nlp のソースは提示された抜粋で途中まで切れているため、記事取得（_fetch_articles）以降の実装をリポジトリ本体で確認する必要あり。
- position_sizing では価格が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があり、将来的に前日終値や取得原価等のフォールバック実装が必要という TODO が残る。
- .env 読み込みでは OS 環境変数がデフォルトで保護されるため、意図的に上書きする場合は .env.local を使用する設計。自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。
- 実行時のプロセス優先度 / CPU affinity 設定は権限不足や一部プラットフォームで失敗する可能性があり、その場合はログに警告を出して処理を継続するフェイルセーフを採用。

---

（補足）
- 本 CHANGELOG はソースコードから機能・設計・既知の注意点を推測して作成しています。リリースノートやユーザ向けドキュメントに使用する際は、実際のコミット履歴やリリース方針に合わせて調整してください。