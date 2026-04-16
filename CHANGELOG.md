# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、重大度は semver（慣例）に基づいて推測しています。記載内容はコードの現状から推測して取りまとめたもので、実際のコミット履歴ではありません。

## [Unreleased]

### Added
- news_nlp モジュールを導入（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ格納する処理を実装。
  - バッチサイズ、トークン制御（記事数/文字数トリム）、429/ネットワーク/5xx に対する指数バックオフ・リトライ、レスポンス検証、スコアの ±1.0 クリップなどの堅牢性対策を組み込み。
  - ニュースウィンドウ計算（JST → UTC 変換）ユーティリティを提供。

- 研究・分析機能を追加（kabusys.research）
  - factor_research: Momentum / Volatility / Value のファクター計算を実装（DuckDB 上の prices_daily/raw_financials を利用）。
  - feature_exploration: 将来リターン計算（任意ホライズン）、IC（Spearman）計算、ファクター統計サマリー、ランク付けユーティリティを実装。
  - DuckDB 接続を受け取り SQL と純 Python で完結する設計。

- ポートフォリオ構築モジュールを追加（kabusys.portfolio）
  - portfolio_builder: シグナル選定（スコア降順・タイブレーク）、等金額・スコア重み配分を実装。
  - position_sizing: リスクベース／等配分の株数算出、単元丸め、aggregate cap によるスケールダウン（端数の lot 単位追加配分ロジック含む）を実装。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）を実装。未知レジームはフォールバック（警告発行）。

- 実行/監視用スクリプトを追加
  - run_execution: ExecutionEngine の起動エントリポイント。KABUSYS_ENV=paper_trading 時の DB 分離（data/paper_trading.db）や MockBroker 切替を考慮。
  - run_monitoring: SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイルの検知により安全にループ終了。

- ツールを追加
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成ツール。稼働率・注文成功率・送信率・P95 レイテンシ等の集計と PASS/FAIL 判定を CLI から出力。

- 設定/ユーティリティ
  - config.Settings を実装：.env 自動読み込み（.env, .env.local）、必要な環境変数の検査、Paper Trading 用のパスやしきい値のプロパティを提供。PAPER_FILL_MODE 等の入力検証を実施。
  - utils.process_priority: プラットフォーム差を吸収するプロセス優先度設定と CPU affinity 設定ユーティリティを追加（Windows / POSIX の差異を吸収し、権限不足等は警告でスキップ）。

### Changed
- DB の扱いを明確化
  - 監視（monitoring）は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する設計に変更（監視データの一元化）。
  - 実行エンジンは paper_trading 環境で専用 SQLite DB を使用（本番 DB と分離）。

- .env 読み込み挙動
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）から実行され、OS 環境変数は保護される（.env.local は上書き許可）。
  - 読み込み失敗時は警告を出力して継続する堅牢化。

### Fixed
- ポーリング間隔の不正値対策
  - MONITOR_POLL_INTERVAL が不正（0 以下や非整数）の場合にデフォルト値へフォールバックし、警告を出力するように改善。time.sleep に渡して例外が出るのを防止。

- position_sizing のスケーリング精度向上
  - aggregate cap 適用時に lot_size 単位での再配分を行い、残余キャッシュを使って端数の追加割当てを行うロジックを導入（ロバストネス向上）。

### Security
- OpenAI API キーは引数優先で環境変数をフォールバックする設計にし、未設定時は ValueError を送出して明示的に扱うように変更（誤動作の抑止）。

---

## [0.1.0] - 初期リリース (推定)
最初の公開バージョンとして推定できる機能群をまとめます（kabusys.__version__ == "0.1.0" に基づく推測）。

### Added
- コアパッケージ構成とバージョン情報（kabusys パッケージ、__version__ = 0.1.0）。
- 実行・監視の基本フロー（ExecutionEngine / SystemMonitor を起動する run スクリプト）。
- 設定管理（Settings クラス）と .env 自動読み込み機能。
- ポートフォリオ構築ロジック（銘柄選定、重み計算、ポジションサイズ算出、セクター制限、レジーム乗数）。
- リサーチ／ファクター計算（momentum / volatility / value）および特徴量解析ユーティリティ（forward returns / IC / summary）。
- Paper Trading 向けツール（検証レポート生成）。
- OpenAI を利用したニュース NLP（AI スコアリング）モジュールの骨格。
- プロセス優先度・CPU affinity ユーティリティ。
- DuckDB / SQLite を組み合わせたデータアクセス設計（prices_daily, raw_financials, ai_scores, trade_logs 等の参照を想定）。

### Changed
- （初期リリースなので主な変更点は省略）

### Fixed
- （初期リリースなので主な修正点は省略）

---

注記:
- 本 CHANGELOG はソースコードの現状を基に推測して作成しています。実際のコミット履歴やリリースノートがある場合はそちらを優先してください。
- news_nlp モジュールの末尾が途中で切れているため（ソースの一部欠落）、実装状況により挙動やエラー処理の詳細が異なる可能性があります。必要であれば該当モジュールの続き部分を提供していただければ、より正確な変更履歴へ反映できます。