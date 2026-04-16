# Changelog

すべての重要な変更を記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

なお、以下の変更点は提示されたソースコードから推測して記載しています（実装コメント・ドキュメント文字列等に基づく要約）。

## [Unreleased]

### Added
- CI / 運用用ユーティリティを追加
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows / POSIX の差異を吸収し、例外時は警告を出して安全にスキップ。
    - set_process_priority(level)、set_cpu_affinity(cpu_count) を提供。
- 実行・監視用エントリポイントを追加
  - 実取引/紙トレード切替に対応した ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db）を使用。
    - Broker クライアントのファクトリ、OrderManager、OrderRepository、RiskManager、Reconciler を組み立ててエンジンを起動。
    - 停止フラグ / PID ファイルの取り扱いを実装。
  - システム監視ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き、停止フラグ検出、監視 DB 初期化の実装。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明示。
- 設定ローダーと Settings クラスを追加（src/kabusys/config.py）
  - .env/.env.local の自動ロード（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - export KEY=val、クォート付き値、インラインコメント等を考慮した柔軟な .env パーサ実装。
  - 環境変数の保護（protected）・上書き制御を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - 各種設定プロパティ（DBパス、paper trading 用パス、各種閾値、ログレベル判定、env 判定など）を提供。必須項目は _require() で検証。
- ポートフォリオ構築モジュールを追加（kabusys.portfolio）
  - 銘柄選定、等配分・スコア配分（portfolio_builder.py）。
  - セクター集中制限・レジーム乗数（risk_adjustment.py）。
  - 株数決定・リスク制限・単元丸め・投下資金スケール処理（position_sizing.py）。
  - aggregate cap（総投資額超過時の縮小）アルゴリズムと lot_size 単位での残余配分を実装。
- 研究（research）モジュールを追加
  - ファクター計算（momentum, volatility, value）（research/factor_research.py）。
    - DuckDB 上の prices_daily / raw_financials を用いた計算。MA200、ATR20、各種モメンタムリターンを算出。
  - 特徴量探索ユーティリティ（research/feature_exploration.py）
    - 将来リターン計算（複数ホライズン対応）、Spearman ベースの IC 計算、ファクター統計サマリ、ランク付けユーティリティを実装。
  - research パッケージは zscore_normalize（外部モジュール経由）等をエクスポート。
- ニュース NLP スコアリングモジュールを追加（kabusys.ai.news_nlp）
  - raw_news + news_symbols を集約し、OpenAI（gpt-4o-mini）を用いて銘柄単位のセンチメント（-1.0〜1.0）を算出して ai_scores テーブルに書き込む設計。
  - バッチサイズ、トークン肥大対策（記事数・文字数上限）、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアクリップを実装する方針をドキュメント化。
  - ニュース収集ウィンドウの算出ユーティリティ（calc_news_window）を実装（JST→UTC の変換仕様を明示）。
- 運用ツールを追加
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）。
    - system_status / trade_logs / risk_logs テーブルを集計し、稼働率・注文成功率・送信率・レイテンシ等の指標を算出し、PASS/FAIL を出力する CLI ツール。
    - P95 の計算、日付フィルタ、DBパス引数対応を実装。

### Changed
- パッケージ初期化情報追加
  - パッケージバージョンを __version__ = "0.1.0" として定義（src/kabusys/__init__.py）。

### Fixed
- 環境設定読み込みの堅牢化
  - .env パーサが export プレフィックスやクォート内のエスケープ、コメント処理を正しく扱うよう実装。
- ポジションサイズ計算の安定化
  - price が不正（None/0）な場合はスキップするなど、例外投げない防御的処理を追加。
  - risk_based と equal/score 両フローで単元（lot_size）丸めを適用。

### Known issues / Notes
- apply_sector_cap の価格欠損時のフォールバックは TODO として残存（前日終値等の扱いは未実装）。
- ニュース NLP モジュールは複数の処理フローを設計どおりに記述しているが、実際の外部 API 呼出し周りの完全なエラー耐性と DB 書き換えトランザクションの動作は運用で確認が必要。
- DuckDB に対する executemany の制約（空パラメータの禁止）に注意した実装注釈あり。

---

## [0.1.0] - 2026-04-16

初回公開リリース。上記の機能群をまとめて初版としてリリース。

### Added
- コア機能
  - 実行エンジン起動スクリプト（run_execution.py）
  - 監視ループ起動スクリプト（run_monitoring.py）
  - 設定管理（config.Settings）、.env 自動ロード機構
  - プロセス優先度 / CPU affinity ユーティリティ
- トレーディング関連
  - ポートフォリオ構築（選定・重み付け・リスク調整・銘柄別量決定）
  - リスク管理用構成 (RiskConfig) と RiskManager 周辺の組み立て方針（エンジン統合）
  - order/reconciler/repository の基本的な組立て（起動スクリプト側）
- 研究・分析
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC・統計サマリユーティリティ
- AI / NLP
  - ニュースのセンチメントスコアリング設計と部分実装（OpenAI 経由で ai_scores へ格納）
- 運用ツール
  - Paper Trading 検証レポート生成ツール（CLI）
- ドキュメント化
  - 各モジュールに詳細な docstring / 設計ノート・制約を追加

### Fixed
- 各モジュールにおける nil/zero チェックとフォールトトレランスを強化（DB 欠損、価格欠損、API キー欠損等）。

---

参考:
- 主要設計文書参照箇所はソース内 docstring に記載（例: PortfolioConstruction.md、StrategyModel.md 等）。