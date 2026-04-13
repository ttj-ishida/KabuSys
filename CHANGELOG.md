# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
このファイルはコードベースの内容から推測して作成した初期リリース記録です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

※日付はリポジトリ内のコードコメント等を基に推定しています。

## [Unreleased]

## [0.1.0] - 2026-04-13

### Added
- 全体
  - プロジェクトの初期公開リリース。自動売買システム「KabuSys」の基本コンポーネント群を提供。
  - DuckDB / SQLite を用いたオンプレミスデータ処理基盤を導入。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視用 DB 初期化（init_monitoring_db）および DuckDB 接続を行う。
    - 例外発生時のロギングと継続ループを備えた堅牢な実行ループを実装。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - 本番環境と Paper Trading を完全に分離する DB パスの扱いを実装（`PAPER_TRADING_SQLITE_PATH` / Settings.is_paper）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動を行う。
    - RiskConfig によるリスク制約（最大ポジション比率、最大利用率、レート制限、サーキットブレーカー、初期ポートフォリオ値等）を導入。

- 設定管理
  - config.py
    - .env 自動読み込み: プロジェクトルート検出（.git または pyproject.toml）を基に .env / .env.local を読み込む。
    - `_parse_env_line` により export 形式、クォート内のバックスラッシュエスケープ、インラインコメントの扱いを正しくパース。
    - `_load_env_file` は override / protected オプションを持ち、OS 環境変数の保護（上書き防止）に対応。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能。
    - Settings クラスを提供し、各種環境変数（DB パス、OpenAI 等のキー、PID/kill フラグパス、閾値、PAPER_FILL_MODE 等）をプロパティとして安全に取得・検証。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）: スコア降順、同点は signal_rank でタイブレーク。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights）。全スコアが 0 の場合は等配分にフォールバックし警告を出力。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）: 既存保有のセクター比率が閾値を超える場合に当該セクターの新規候補を除外。sell_codes を考慮して当日売却予定銘柄をエクスポージャー計算から除外。
    - レジーム乗数（calc_regime_multiplier）: "bull"/"neutral"/"bear" に対する資金乗数を定義。未知レジームは警告を出して 1.0 でフォールバック。

  - portfolio/position_sizing.py
    - 株数算定（calc_position_sizes）
      - risk_based、equal、score の割当方式に対応。
      - lot_size（単元株）を考慮した丸め処理。
      - per-stock 上限・aggregate cap（available_cash）を適用し、必要に応じてスケーリングして残差ロジックで追加配分を行う。
      - cost_buffer により手数料・スリッページ分を保守的に見積もる。

- 研究（Research）
  - research/factor_research.py
    - Momentum, Volatility, Value ファクター計算関数（calc_momentum / calc_volatility / calc_value）を提供。DuckDB の SQL ウィンドウ関数を用いた実装で、欠損データや最小行数要件に対する扱いを明示。
  - research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic：スピアマン順位相関）計算、ファクター統計サマリ（factor_summary）、rank ユーティリティを追加。標準ライブラリのみで実装。

- AI（ニュース NLP）
  - ai/news_nlp.py
    - raw_news テーブルのニュースを OpenAI API（gpt-4o-mini）でセンチメントスコアリングし、ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（日本時間ベース → UTC 変換）、記事トリム（記事数・文字数制限）、銘柄バッチ（最大 20 銘柄）での送信、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップ、部分失敗時のデータ保護（対象コードのみを置換）など堅牢な処理フローを採用。
    - API キーは引数または環境変数 `OPENAI_API_KEY` から解決。未設定時は ValueError。

- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム差異を吸収するプロセス優先度設定ユーティリティを追加（Windows / POSIX 対応）。
    - CPU affinity 設定関数（set_cpu_affinity）を提供。
    - 許可エラーや未実装環境では警告を出力して安全にスキップ。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成 CLI を追加（--from/--to/--db オプション対応）。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計し、閾値に基づく PASS/FAIL 判定を出力。
    - DB テーブルが存在しない場合やデータ不足時のフォールバック（N/A 表示）を実装。

### Changed
- なし（初期リリースのため変更履歴は追加事項中心）。

### Fixed
- なし（初期リリース）。ただし各モジュールにおいて入力検証・例外処理を充実させ、実行時の安全性を高める防御的実装を採用。

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キーなどの機密情報は Settings 経由で環境変数から取得する設計。`.env.local` を使ったローカル上書きや OS 環境変数の保護（protected）を考慮。

## 今後の注意点（実装上の注記）
- ai/news_nlp.py は外部 API 呼び出しを行うため、API エラーやレート制限に対する運用上の監視が必要。
- position_sizing の価格欠損時（価格が 0.0 の場合）のフォールバックロジックは TODO コメントとして残されている（前日終値等の導入検討）。
- .env パーサは多くのケースをカバーするが、極端に複雑な .env の書式（複数行文字列等）は想定外の動作をする可能性がある。
- run_monitoring は「監視用 DB を環境にかかわらず本番 sqlite_path を使用する」設計。ローカルテスト時の取り扱いに注意。

---

（この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時はコミット履歴やバージョン管理のタグ情報を基に正確な差分を反映してください。）