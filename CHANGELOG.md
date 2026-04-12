# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。  

重要: この CHANGELOG は与えられたコードベースの内容から推測して作成しています。実際のコミット履歴とは異なる場合があります。

---

## [Unreleased]

### Added
- モニタリング用のエントリポイント `src/kabusys/run_monitoring.py` を追加。
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視ループは SQLite（monitoring DB）と DuckDB に接続し、`SystemMonitor` の `check_once()` を定期実行する。
  - 起動時にプロセス優先度を "high" に設定する処理を実行（`set_process_priority` を使用）。
  - 監視は実行環境にかかわらず本番の `sqlite_path` を使用する仕様。

- 実行エンジン用のエントリポイント `src/kabusys/run_execution.py` を追加。
  - 環境 `KABUSYS_ENV=paper_trading` の場合は paper 用の SQLite DB（`data/paper_trading.db` など）を使用し、本番 DB と完全分離。
  - `BrokerClientFactory` によるブローカークライアント生成、`OrderRepository` / `OrderManager` / `RiskManager` / `Reconciler` を組み合わせて `ExecutionEngine` を起動。
  - `RiskConfig` にデフォルトパラメータを設定（最大ポジション比率、利用率、レート制限、サーキットブレーカーなど）。初期ポートフォリオ値をブローカーの利用可能現金で初期化。

- 設定読み込みモジュール `src/kabusys/config.py` を追加。
  - プロジェクトルート（`.git` または `pyproject.toml`）を起点に自動で `.env` / `.env.local` を読み込む（OS 環境変数を保護して上書き制御）。
  - 複雑な .env パース（クォート・エスケープ・インラインコメント対応）を実装。
  - 必須環境変数チェック `_require`、各種設定プロパティ（DB パス、PID ファイルパス、閾値、環境種別チェック、PAPER_FILL_MODE の検証など）を実装。
  - `Settings` クラスとモジュールレベルの `settings` インスタンスを提供。

- ポートフォリオ構築関連モジュールを実装（純粋関数群）。
  - `src/kabusys/portfolio/portfolio_builder.py`
    - シグナル選別（スコア降順、タイブレークは signal_rank）と等差・スコア加重の重み計算（スコア全零時のフォールバック）。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限の適用（既存保有を考慮、売却予定銘柄は除外、"unknown" セクターは制限適用しない）。
    - 市場レジームに応じた投下資金乗数（bull/neutral/bear とデフォルトフォールバック）。
  - `src/kabusys/portfolio/position_sizing.py`
    - allocation_method（risk_based / equal / score）に基づく発注株数計算。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap、cost_buffer による保守的見積り、スケールダウンと残差分配ロジックを実装。

- 研究／リサーチ用モジュールを実装（DuckDB を想定）。
  - `src/kabusys/research/factor_research.py`
    - Momentum / Volatility / Value ファクター計算（MA200、ATR20、出来高、PER/ROE 等）。
    - DuckDB を用いた SQL ベースの集約実装。
  - `src/kabusys/research/feature_exploration.py`
    - 将来リターン計算（任意ホライズン）、IC（スピアマンランク相関）計算、ファクター統計サマリー、ランク付けユーティリティを実装。
  - これらをまとめて `src/kabusys/research/__init__.py` でエクスポート。

- ニュース NLP スコアリングモジュール `src/kabusys/ai/news_nlp.py` を追加。
  - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）へバッチで送信して各銘柄のセンチメント（-1.0〜1.0）を算出し `ai_scores` テーブルへ書き込む。
  - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）計算ユーティリティを提供。
  - バッチサイズ、トークン肥大化抑制（記事数/文字数制限）、429/5xx/ネットワークエラーに対する指数バックオフ再試行、JSON レスポンス検証、スコアクリップ、部分成功に備えた部分更新戦略を実装。

- ユーティリティ群を追加。
  - `src/kabusys/utils/process_priority.py`
    - Windows / POSIX を吸収したプロセス優先度設定（high/normal/low）と CPU affinity 設定機能。アクセス権限不足時は警告を出してスキップ。

- コマンドライン用ユーティリティ
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading 用 SQLite DB から検証レポートを生成する CLI ツールを実装。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを算出し PASS/FAIL 判定を行う（閾値はソース内定義）。
    - 日付フィルタ（--from, --to）と DB パス指定オプション（--db）をサポート。

- パッケージ初期化・メタ情報
  - `src/kabusys/__init__.py` に __version__ = "0.1.0" を追加。

### Changed
- .env 自動ロード:
  - OS 環境変数を保護する仕組み（protected set）を導入し、`.env` は既存変数を上書きせず、`.env.local` は明示的に上書き可能とした。
  - プロジェクトルートの検出を __file__ の親階層走査で行い、CWD に依存しないように変更。

- DB 接続挙動:
  - 監視プロセス（run_monitoring）は環境にかかわらず本番の `sqlite_path` を使用する設計に明示（監視は本番 DB を見る想定）。
  - 実行エンジン（run_execution）は paper_trading 環境では paper 用専用 DB を使用し本番と分離。

### Fixed
- .env パーサーの改良:
  - クォート/エスケープ処理、インラインコメントの扱い、`export KEY=val` 形式などの堅牢なパースに対応。
- ポジションサイズ計算のスケーリングと残差配分ロジックの安定化（単元丸め・上限チェックの一貫性向上）。
- 各モジュールで DB テーブルが存在しない場合に `OperationalError` を捕捉してツールが致命的に終了しないように配慮（ツール側でデフォルト値を返す等）。

---

## [0.1.0] - 2026-04-12

### Added
- 初期リリース相当の機能群を実装・公開:
  - コア: 設定管理（Settings）、バージョン定義、パッケージ初期化。
  - 実行系: Execution エントリポイント、ExecutionEngine 周辺の組み立て（broker, order manager, risk manager, reconciler）。
  - 監視系: SystemMonitor 向けの起動スクリプトと DB 初期化呼び出し。
  - ポートフォリオ構築: 候補選定、重み算出、ポジションサイズ計算（risk-based を含む）。
  - リスク調整: セクターキャップ、レジーム乗数。
  - リサーチ: ファクター計算（momentum/volatility/value）、将来リターン・IC・統計要約。
  - AI: ニュース NLP スコアリング（OpenAI 経由）、タイムウィンドウ集約、バッチ処理。
  - ツール: Paper Trading 検証レポート CLI。
  - ユーティリティ: process priority / cpu affinity、.env ローダー（高機能パーサ）。

### Changed
- プロジェクト全体のログ出力は INFO レベルをデフォルトに設定するエントリポイントがある（実行時に logging.basicConfig で制御）。
- 実行・監視起動でプロセス優先度を最初に設定するワークフローを採用。

### Fixed
- 各モジュールに対して入力バリデーションとフォールバックを追加（PAPER_FILL_MODE 検証、poll interval の不正値フォールバックなど）。

---

注: 上記はコードベースの実装内容から推測した変更履歴です。実際の変更履歴（コミットメッセージやリリースノート）を元に確定的な CHANGELOG を作る場合は、リポジトリのコミットログまたはリリース情報を参照してください。