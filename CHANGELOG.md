# Changelog

All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠しています。  
リンクやコミット参照は含まれていません（コードから推測した変更点を記載しています）。

## [Unreleased]

## [0.1.0] - 2026-04-16
初回リリース。自動売買システム「KabuSys」のコア機能群を実装しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて `__version__ = "0.1.0"` として定義。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env のパース機構を実装（コメント行、`export KEY=val`、クォート内のエスケープ等に対応）。
  - Settings クラスを導入。アプリケーションで利用する主要な環境設定をプロパティとして提供。
    - サポートする環境: development / paper_trading / live（KABUSYS_ENV）。
    - DB パス: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH（paper_trading 用）。
    - Paper Trading 関連: PAPER_FILL_MODE（instant/partial/never/reject）を検証。
    - 監視・閾値関連: PID ファイルパス、kill flag、CPU/Memory/Disk のしきい値など。

- 実行エントリスクリプト
  - run_execution (src/kabusys/run_execution.py)
    - ExecutionEngine 起動用スクリプト。
    - KABUSYS_ENV=paper_trading の場合、本番 DB と分離して専用の paper_trading DB を使用。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine を組み立ててセッションをスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）および pid ファイル管理を実装。
    - RiskConfig のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec 等）を提供。

  - run_monitoring (src/kabusys/run_monitoring.py)
    - SystemMonitor ポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を調整可能（デフォルト 60 秒）。
    - Monitoring は実行環境にかかわらず本番用 sqlite_path を使用して監視データを記録（設計上の注意点）。
    - 停止フラグ（data/stop_requested.flag）による終了検知をサポート。

- ユーティリティ (src/kabusys/utils/process_priority.py)
  - プロセス優先度設定ユーティリティを実装（Windows / POSIX を吸収）。
  - set_process_priority(level: "high" | "normal" | "low")
    - Windows: psutil の PRIORITY_CLASS を使用、POSIX: nice 値を設定。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。
  - set_cpu_affinity(cpu_count: int | None)
    - 指定コア数に固定する機能（権限不足時は警告でスキップ）。

- ポートフォリオ構築 (src/kabusys/portfolio/*)
  - portfolio_builder
    - select_candidates: スコア降順で候補抽出（signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分（スコア全て0 の場合は等分配へフォールバック）。
  - risk_adjustment
    - apply_sector_cap: 同一セクター上限をチェックして候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear をサポート、未知値は警告して 1.0 にフォールバック）。
  - position_sizing
    - calc_position_sizes: 各銘柄の発注株数計算（allocation_method: "risk_based" / "equal" / "score"）。
    - lot_size 単位で丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap スケーリングを実装。
    - 手数料/スリッページ分の保守的見積もり（cost_buffer）を導入。残余キャッシュを用いた端数配分ロジックを実装。

- 研究（Research）機能 (src/kabusys/research/*)
  - factor_research
    - calc_momentum, calc_volatility, calc_value を実装（DuckDB 接続を受け prices_daily / raw_financials を参照）。
    - 各種ウィンドウサイズ（MA200, ATR20 等）や欠損時の None 処理を実装。
  - feature_exploration
    - calc_forward_returns: 将来リターン（複数ホライズン）計算（ホライズン検証あり）。
    - calc_ic: スピアマンランク相関（IC）を実装。データ不足時は None を返す。
    - factor_summary / rank: 基本統計量やランク付けユーティリティ。
  - research パッケージに zscore_normalize を含めた公開 API を整備。

- AI ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
  - raw_news を OpenAI（gpt-4o-mini）でセンチメントスコアリングし ai_scores に書き込む処理の設計・実装。
  - 実装上の特徴:
    - ニュース時間ウィンドウの計算（JST 基準 → UTC 変換）。
    - 記事数・文字数の上限（銘柄ごとのトリム）でトークン過膨張を対処。
    - バッチ送信（1回最大 _BATCH_SIZE 銘柄）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ・リトライ。
    - レスポンスバリデーションと ±1.0 クリップ。
    - 部分失敗時に既存スコアを保護するため、対象コードのみを削除してから挿入する方式（DELETE → INSERT）。
  - OpenAI API キー未設定時はエラー（api_key または環境変数 OPENAI_API_KEY が必要）。

- ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading 検証レポート生成スクリプトを提供。
  - 指標:
    - 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。
  - デフォルト閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）。
  - SQL 実行時の OperationalError を安全にハンドリングしてレポート生成を続行する実装。
  - コマンドライン引数: --from / --to / --db をサポート。

- DB 初期化ユーティリティ
  - monitoring のための init_monitoring_db 呼び出しを実行開始時に行い、監視テーブルの存在を保証（冪等性を想定）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env パーサでのクォート・エスケープ挙動を改善し、インラインコメント処理や export 形式に対応。
- 設定読み込みの際に OS 環境変数を保護する仕組みを導入（.env.local の上書き制御等）。
- calc_score_weights で全スコア 0 の場合に等金額配分へフォールバックするロジックを追加（警告ログあり）。

### Security
- OpenAI やブローカ API の認証情報は環境変数経由で供給する設計。コードやリポジトリにキーを含めないこと。
- Settings._require により必須環境変数未設定時は早期に ValueError を送出。

### Notes / Known issues / TODO
- apply_sector_cap 内で price が欠損（0.0）の場合にエクスポージャーが過少見積りされる旨をコメントで残しています。将来的に前日終値や取得原価などのフォールバックを導入する予定。
- position_sizing の lot_size は現状グローバル固定（デフォルト 100）。将来的に銘柄別 lot_map を受け取る拡張を検討。
- DuckDB に対する executemany の挙動（バージョン依存の制約）への注意コメントあり。空パラメータでの実行を避ける実装を行っている。
- Monitoring は設計上「環境にかかわらず本番 sqlite_path を使用」する挙動となっているため、paper_trading 運用時は監視用 DB の分離が必要な場合注意。
- calc_regime_multiplier は未知のレジームで 1.0 にフォールバックする（警告ログあり）。
- OpenAI 呼び出し部分は外部 API 呼び出しに依存するため、ネットワークや API 制限時のフォールトトレランス設計に留意のこと。
- news_nlp の実装は大枠を含むが、API レスポンス処理部分は堅牢なバリデーションを行う必要がある（コード中にも検証ロジックがあるが運用での確認推奨）。

### Migration / Upgrade notes
- 必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は Settings により未設定時に例外が発生します。デプロイ前に .env を準備してください（.env.example 参照を想定）。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかに設定してください。paper_trading を選ぶと発注 DB が paper_trading 用に切り替わります。
- MONITOR_POLL_INTERVAL を設定することで監視ループの間隔を変更できます（秒）。不正な値はデフォルト 60 秒にフォールバックします。
- Paper Trading 環境では PAPER_FILL_MODE を確認してください（instant/partial/never/reject）。不正値は起動時に例外となります。

---

今後のリリースでは以下を想定しています（実装予定・改善案）:
- price フォールバックロジックの実装（前日終値等）。
- 銘柄毎 lot_size サポート。
- monitoring と paper_trading の DB 分離や設定での明示化。
- AI モジュールの追加テストとエラーハンドリング強化。

（以上、ソースコードの内容から推測して作成した CHANGELOG です。追記・修正したい点があればお知らせください。）