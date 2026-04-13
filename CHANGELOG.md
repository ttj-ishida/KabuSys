# Changelog

すべての notable な変更はこのファイルに記録します。

フォーマットは Keep a Changelog に準拠します。  
https://keepachangelog.com/ja/1.0.0/

現在の日付: 2026-04-13

## [Unreleased]

### Added
- 監視用ポーリングプロセス起動スクリプトを追加
  - src/kabusys/run_monitoring.py
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV に関係なく本番の sqlite_path を使用。
  - プロセス優先度を起動時に設定（utils/process_priority.set_process_priority を使用）。
  - SQLite（monitoring DB）と DuckDB に接続し SystemMonitor を用いたループで check_once() を定期実行。

- 実行エンジン起動スクリプトを追加
  - src/kabusys/run_execution.py
  - KABUSYS_ENV=paper_trading 時に MockBrokerClient を使用し、専用の paper_trading DB（デフォルト: data/paper_trading.db）に記録して本番 DB と完全分離。
  - ExecutionEngine の組み立て（Broker, OrderRepository, OrderManager, RiskManager, Reconciler 等）。
  - 起動時にプロセス優先度を設定。

- 環境設定管理モジュールを追加・改善
  - src/kabusys/config.py
  - プロジェクトルートを .git / pyproject.toml から自動検出して .env / .env.local を自動ロード（OS 環境変数を上書きしない保護機構あり）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env ファイルの行パーサは export 形式・クォート・エスケープ・インラインコメント処理をサポート。
  - Settings クラスで各種環境変数のラッパーを提供（DB パス、API トークン、監視閾値、PID ファイルパス等）。
  - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の検証ロジックを導入。

- ポートフォリオ構築関連の純粋関数群を追加
  - src/kabusys/portfolio/
  - portfolio_builder: 候補選定（score 降順、同点は signal_rank でタイブレーク）、等金額配分・スコア加重配分を実装。
  - risk_adjustment: セクター集中制限の適用（既存保有からセクターエクスポージャーを計算し候補除外）、市場レジームに応じた乗数（bull/neutral/bear）を提供。
  - position_sizing: allocation method（risk_based, equal, score）に基づく発注株数計算、単元株丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的評価を実装。

- リサーチ / ファクター関連を追加
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value ファクターの計算関数を提供（DuckDB 接続を受け取り SQL で集計）。
    - 各関数はデータ不足時に None を返す設計で安全性を確保。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算、IC（Spearman ランク相関）計算、ファクター統計サマリ、ランク関数を実装。
    - pandas 等外部ライブラリに依存しない純粋な実装。
  - research パッケージの公開 API を __init__.py で整備。

- ニュース NLP（OpenAI を用いたセンチメントスコアリング）モジュールを追加
  - src/kabusys/ai/news_nlp.py
  - raw_news + news_symbols から銘柄ごとに記事を集約し、gpt-4o-mini（JSON Mode）でセンチメントを -1.0〜1.0 にスコアリングして ai_scores テーブルへ書き込む。
  - バッチ処理（最大 20 銘柄/回）、記事・文字数制限、スコアクリップ、429/ネットワーク/5xx に対する指数バックオフリトライ等のフォールトトレラント設計。
  - OPENAI_API_KEY が未設定の場合は ValueError を発生させる（明示的なエラー報告）。

- ツール: Paper Trading 検証レポート生成スクリプトを追加
  - src/kabusys/tools/paper_verification_report.py
  - paper_trading DB からシステム稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等を集計して判定（PASS/FAIL）を出力。
  - 期間フィルタ（--from / --to）や --db オプションをサポート。
  - P95 計算、閾値（稼働率 99%, 成功率 90% 等）をデフォルトで定義。

- ユーティリティ: プロセス優先度・CPU affinity 設定
  - src/kabusys/utils/process_priority.py
  - Windows / POSIX の差分吸収。set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
  - 権限不足や未対応プラットフォームでは安全にフォールバック（warning ログ）。

### Changed
- パッケージ初期化情報を設定
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

### Fixed
- .env 読み込みでのエラー時に警告を出して読み込みをスキップする処理を導入（IO エラーに対する堅牢化）。

### Security
- 環境変数に依存する秘密情報（OpenAI / J-Quants / Kabu API）を Settings 経由で取得し、未設定時は明確なエラーを出す方針を採用。
- 自動 .env ロードでも OS 環境変数は上書きされないよう保護（protected set）。

---

## [0.1.0] - 2026-04-13

Initial release — 基本的な自動売買システムのコア機能を実装。

### Added
- 実行エンジン（ExecutionEngine）起動ロジックと関連コンポーネント（OrderManager, OrderRepository, RiskManager, Reconciler 等）。
- 監視（SystemMonitor）用ポーリング起動スクリプト。
- 環境設定管理（.env 自動読み込み、Settings クラス）。
- ポートフォリオ構築モジュール（候補選定、重み付け、株数決定、セクター制限、レジーム乗数）。
- リサーチモジュール（ファクター計算、将来リターン、IC、統計サマリ）。
- ニュース NLP スコアリング（OpenAI を利用したセンチメント算出、ai_scores への書込）。
- Paper Trading 検証レポート生成ツール。
- プロセス優先度 / CPU affinity ユーティリティ。
- DuckDB / SQLite を用いたデータアクセス基盤（prices_daily, raw_financials, raw_news, trade_logs, system_status, risk_logs, ai_scores 等を想定）。

### Changed
- N/A（初回リリース）

### Fixed
- N/A（初回リリース）

### Security
- 必須 API キー未設定時に明確な例外を発生させる（OpenAI など）。

---

注記:
- 本 CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のリリース手順・バージョニング方針や追加の変更点がある場合は適宜差し替えてください。
- 各モジュールはドキュメント内（コメントや docstring）に設計方針や注意事項が記載されています。特に paper_trading と本番 DB の分離、.env 自動ロードの挙動、OpenAI API 利用の制約（キー管理、リトライポリシー）は運用上重要です。