# Changelog

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

現在のバージョン: 0.1.0

## [Unreleased]

(なし)

## [0.1.0] - 2026-04-13

初回リリース。以下の主要機能・モジュールを追加しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを設定: `kabusys.__version__ = "0.1.0"`。
- 起動スクリプト
  - SystemMonitor 用ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する設計。
    - プロセス優先度を起動時に "high" に設定。
    - DB 初期化用 init_monitoring_db を呼び出し、DuckDB 接続も確立。
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - `KABUSYS_ENV=paper_trading` 時は paper_trading 専用 SQLite DB（data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine を起動。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - 環境変数・.env 自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml を基準に探索して .env / .env.local を自動読み込み（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env のパースはクォート／エスケープ／コメント記法に対応。
    - Settings クラスを提供し、各種設定（DB パス、API トークン、PID ファイルパス、閾値、環境種別判定等）をプロパティ経由で取得。
    - PAPER_FILL_MODE の検証（"instant" / "partial" / "never" / "reject"）や KABUSYS_ENV / LOG_LEVEL の検証を実装。
- 監視/ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX を横断的に処理し、権限不足や未対応 OS の場合は警告を出して安全にスキップ。
    - set_cpu_affinity によるコア固定機能を提供。
- ポートフォリオ構築（純粋関数群）
  - 候補選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - signal スコアに基づくソート、等分配・スコア加重配分の実装。
    - 全スコアが 0 の場合は等分配にフォールバックして警告を出す。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - セクターごとの既存エクスポージャー計算に基づく候補除外（unknown セクターは除外対象外）。
    - レジームに応じた資金乗数（bull:1.0, neutral:0.7, bear:0.3）。未知レジームは警告の上 1.0 にフォールバック。
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - allocation_method（risk_based / equal / score）に応じた株数算出。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash）によるスケーリング、cost_buffer による保守的見積りを実装。
    - スケールダウン時は lot_size 単位で端数処理を行い、残余キャッシュで優先度順に追加配分するロジックを含む。
- 研究・ファクター計算
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（ATR20 等、出来高指標）、Value（PER / ROE）を DuckDB 上の prices_daily / raw_financials から計算する関数を実装。
    - データ不足時に None を返す安全な実装。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（任意 horizon の fwd リターン）、IC（Spearman ランク相関）計算、ファクター統計サマリ、ランク関数等を実装。
    - pandas 等外部ライブラリに依存しない純粋 Python 実装。
  - research パッケージのエクスポートを整理（src/kabusys/research/__init__.py）。
- AI ニュース NLP スコアリング
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリングモジュールを追加（src/kabusys/ai/news_nlp.py）。
    - 対象ウィンドウの計算（JST 基準 → UTC 変換）、記事集約、銘柄単位のトリミング（記事数・文字数上限）を実装。
    - API 呼び出しは最大バッチサイズで分割し、429 / ネットワークエラー / 5xx に対して指数バックオフでリトライ。
    - レスポンス検証・スコアクリッピング（±1.0）・部分失敗時のテーブル更新の安全化（部分的に削除→挿入）を考慮。
    - OPENAI_API_KEY 未設定時は ValueError を送出。
- ツール
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - コマンドラインから期間指定（--from / --to / --db）で SQLite の paper_trading DB を解析し、稼働率・注文成功率・送信率・P95 レイテンシ等の指標を算出して PASS/FAIL を出力。
    - デフォルト閾値（稼働率 99% 等）や P95 計算ロジックを実装。
    - DB が存在しない場合やテーブル欠損時を想定したフォールバック処理を実装。

### Changed
- なし（初回リリース）

### Fixed
- 監視ポーリング間隔のバリデーション
  - `MONITOR_POLL_INTERVAL` が不正値（非数値または 0 以下）の場合にデフォルト（60 秒）へフォールバックし、警告ログを出すように実装（src/kabusys/run_monitoring.py）。
- .env パーサの挙動改善
  - クォート内のバックスラッシュエスケープや、クォート無しの行におけるコメント判定ルールを明確化（src/kabusys/config.py）。

### Security
- 外部 API キー取り扱い
  - OpenAI API キーは引数または環境変数 `OPENAI_API_KEY` を使用。未設定時に明示的にエラーを出すことで、鍵の未設定による挙動不確実性を回避（src/kabusys/ai/news_nlp.py）。

---

開発・運用上の注意:
- run_monitoring/run_execution は起動時にプロセス優先度設定を試みますが、権限不足や環境によってはスキップされます（警告ログが出力されます）。
- DuckDB / SQLite のテーブルスキーマや初期化は init_monitoring_db 等で行われます。DB マイグレーションや既存データとの互換性に留意してください。
- Paper Trading 環境では本番 DB と分離された `PAPER_TRADING_SQLITE_PATH` を使用し、mock ブローカー等による完全分離を図っています。

ご要望があれば、各モジュールごとの詳細な変更点（関数単位の説明・使用例・既知の制限）を追記します。