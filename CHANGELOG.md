# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。  
書式は「Keep a Changelog」に準拠します（日本語）。

最新版はセマンティックバージョニングに従います。

## [Unreleased]

（現状、リリース済みバージョン: 0.1.0 — 以降の変更はここに記載してください）

---

## [0.1.0] - 2026-04-13

最初の公開リリース。自動売買システム KabuSys のコア機能群をまとめて導入します。

### 追加 (Added)
- 実行系
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - 環境変数 `KABUSYS_ENV=paper_trading` の場合は Paper Trading 用に MockBrokerClient を利用し、専用 SQLite DB（デフォルト: data/paper_trading.db）へ記録する実装をサポート。
    - 実行時にプロセス優先度を "high" に設定する初期化処理を追加。
    - リスク管理（RiskManager）、発注管理（OrderManager）、再整合（Reconciler）等の依存コンポーネントを組み立ててセッション実行を行う。

- 監視 (Monitoring)
  - SystemMonitor のポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 監視用 DB 初期化処理（init_monitoring_db）を行い、SQLite / DuckDB 接続を利用した監視ループを実装。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する（監視データは本番 DB に記録）。

- 設定・環境変数管理
  - Settings クラスを追加（src/kabusys/config.py）。
    - .env 自動読み込み（プロジェクトルートの .env / .env.local、.env.local は上書き）を実装。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - 必須環境変数取得ユーティリティ `_require`（未設定時は ValueError）。
    - 多数の設定プロパティを提供（DB パス、API トークン、PID/kill ファイルパス、閾値、環境種別など）。
    - 値検証を導入（`KABUSYS_ENV`、`LOG_LEVEL`、`PAPER_FILL_MODE` の有効値チェック）。

- ポートフォリオ関連（Portfolio）
  - 銘柄選定・配分（src/kabusys/portfolio/portfolio_builder.py）
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
    - スコア全て 0 の場合は等金額配分へフォールバック（WARNING）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - セクター別エクスポージャーを基に新規候補を除外する apply_sector_cap。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear をマッピング）。未知レジームはログ警告の上 1.0 にフォールバック。
  - 株数決定・投下資金制限（src/kabusys/portfolio/position_sizing.py）
    - allocation_method（risk_based / equal / score）に従う発注株数算出。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り。
    - 将来的拡張（銘柄別 lot_size 等）を想定した TODO を明示。

- 研究（Research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum / Volatility / Value 等のファクター計算関数（calc_momentum / calc_volatility / calc_value）。
    - DuckDB の prices_daily / raw_financials を参照して純粋関数として実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク関数（rank）。
    - 外部ライブラリに依存せず、標準ライブラリのみで実装。

- AI ニュース NLP
  - raw_news を OpenAI API（gpt-4o-mini）でセンチメント解析し ai_scores テーブルへ書き込むモジュールを追加（src/kabusys/ai/news_nlp.py）。
    - 記事集約、チャンク（最大 20 銘柄）でのバッチ送信、429/ネットワーク/5xx に対する指数バックオフリトライを実装。
    - スコアを ±1.0 にクリップし、部分失敗時にも他銘柄の既存スコアを保護する（対象コードのみ置換）。
    - API キー未設定時は ValueError を送出（api_key 引数または OPENAI_API_KEY を使用）。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率 / 注文成功率 / 送信率 / P95 レイテンシ等を集計し PASS/FAIL を判定する CLI ツール。
    - フィルタ期間指定（--from / --to）、DB パス指定（--db）対応。
    - デフォルト閾値を定義し、結果を標準出力で整形表示。

- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX (Linux, Darwin, FreeBSD) を吸収して nice / HIGH_PRIORITY_CLASS を設定。
    - 権限不足や未対応プラットフォームでは警告を出して安全にスキップ。
    - CPU affinity 固定関数 set_cpu_affinity を提供（None で無効化、1 未満は ValueError）。

- パッケージ情報
  - パッケージルートにバージョン情報を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。

### 変更 (Changed)
- 環境変数ロード順序と保護
  - 自動ロードは OS 環境変数（既存値）を保護しつつ .env → .env.local の順に適用。`.env.local` は上書き可能（ただし OS 環境変数は保護）。
  - 自動ロードはプロジェクトルートの検出（.git または pyproject.toml）により行われ、プロジェクト外ではスキップする。

- DB パスの扱い
  - monitoring（run_monitoring）は常に Settings.sqlite_path（本番用パス）を使用する仕様。これは監視データを本番 DB に集約する意図による挙動。

### 修正 (Fixed)
- 入力値の堅牢化
  - MONITOR_POLL_INTERVAL が不正（0 以下や非整数）の場合、警告ログを出してデフォルト（60 秒）にフォールバックする実装を追加。
  - PAPER_FILL_MODE/LOG_LEVEL/KABUSYS_ENV の値検証を実装し、不正値は ValueError を発生させる。

### 既知の制限・注意点 (Notable notes / Known limitations)
- price の欠損値（0.0）に関する注意
  - apply_sector_cap 内で price が欠損（0.0）の場合、エクスポージャーが過小評価される可能性がある旨の TODO コメントあり。将来的に前日終値等でのフォールバックが必要。
- DuckDB / OpenAI 依存
  - 研究・AI モジュールは DuckDB 接続を前提とし、ai/news_nlp は OpenAI の API キーが必要。テスト時は環境を分離すること。
- 単元株（lot_size）は現状グローバル固定（デフォルト 100）。将来的に銘柄毎の単元対応を想定した拡張予定。
- Monitoring は監視データを本番 DB に書き込むため、開発/検証時は注意して実行すること（paper_trading と監視が分離されない点に注意）。

---

（以降のリリースでは、ここに Unreleased → リリース日付きの変更履歴を追記してください）