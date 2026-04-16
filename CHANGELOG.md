# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
現在のリリース: 0.1.0

## [Unreleased]
（現時点で未リリースの変更はありません）

---

## [0.1.0] - 2026-04-16
初回リリース。日本株自動売買システム「KabuSys」のコア機能をまとめて導入しました。

### 追加
- 基本パッケージとバージョン情報
  - パッケージ初期化およびバージョン設定を追加（kabusys.__version__ = "0.1.0"）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサを実装（export プレフィックス対応、クォート・エスケープ処理、インラインコメント処理）。
  - OS 環境変数の保護（.env.local の override でも OS 環境変数は上書きしない）。
  - Settings クラスを導入し、各種設定をプロパティとして提供：
    - J-Quants / kabuステーション / LINE API 等のトークン・URL
    - データベースパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
    - Paper Trading の動作モード（PAPER_FILL_MODE）の検証（有効値: instant, partial, never, reject）
    - 監視関連設定（pid/kill flag、閾値など）
    - 環境タイプ（development, paper_trading, live）の検証とヘルパープロパティ（is_live, is_paper, is_dev）
  - 必須環境変数未設定時に明確なエラーメッセージを送出。

- 実行・監視起動スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加：
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立て。
    - stop フラグファイル（data/stop_requested.flag）検知による安全停止処理。
    - 実行エンジンの PID を data/execution.pid に記録。
  - 監視ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）を追加：
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はフォールバックして警告）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視データを一元管理。
    - stop フラグ検知でループ終了、例外時はログを残して次ポーリングへ継続。

- 監視 DB 初期化ユーティリティの呼び出し（init_monitoring_db）を実行起動時に行い、監視テーブルの存在を保証（冪等）。

- プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
  - Windows / POSIX の差分を吸収してプロセス優先度を設定（high/normal/low）。
  - CPU affinity を最初の N コアに固定するユーティリティを追加（set_cpu_affinity）。
  - 権限不足や未サポート OS 時は安全にスキップして警告出力。

- ポートフォリオ構築モジュール（src/kabusys/portfolio/*）
  - 候補選定・重み計算（portfolio_builder.py）
    - select_candidates: スコア降順、同点は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights（スコアが全て 0 の場合は等配分にフォールバック）。
  - セクター集中管理・レジーム乗数（risk_adjustment.py）
    - apply_sector_cap: 既存保有に基づくセクター別エクスポージャーを計算し、上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告とともに 1.0 フォールバック。
  - ポジションサイジング（position_sizing.py）
    - calc_position_sizes: risk_based / equal / score の各配分方式に対応。単元株（lot_size）丸め、max_position_pct / max_utilization / cost_buffer を考慮した集約キャップ実装。
    - aggregate cap 時のスケーリングと残余キャッシュに応じた lot 単位での追加配分ロジック。

- 研究・ファクター計算（src/kabusys/research/*）
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB の prices_daily から計算。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比を計算（true_range の NULL 伝播を制御）。
    - calc_value: raw_financials の最新財務データと価格を組み合わせて PER / ROE を計算。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズンの将来リターンを計算（複数ホライズン同時取得、引数検証あり）。
    - calc_ic: スピアマンランク相関（IC）を実装（データ不足時は None）。
    - factor_summary / rank: 基本統計量とランク変換ユーティリティ。
  - research パッケージの __all__ に zscore_normalize の再エクスポートを追加（kabusys.data.stats から）。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news を OpenAI API（gpt-4o-mini）でセンチメントスコア化し、銘柄別 ai_scores に書き込む処理を追加。
  - バッチ送信、最大記事/文字数制限、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアクリッピング（±1.0）を設計。
  - API キー解決は引数 > 環境変数 OPENAI_API_KEY。未設定時は ValueError を送出。

- Paper Trading 検証ツール（src/kabusys/tools/paper_verification_report.py）
  - paper_trading DB（デフォルト data/paper_trading.db）から以下指標を集計して標準出力レポートを生成:
    - 稼働率（uptime）、エラー数、総ポーリング数
    - 注文成功率（Filled / Created）、送信率（Sent / Created）
    - リスク却下数（risk_logs）
    - レイテンシ統計（avg, max, P95）
  - CLI オプション: --from / --to / --db。閾値を超えた場合に FAIL 判定を出力。
  - P95 計算、SQL の存在チェック、OperationalError に対するフォールバック処理を実装。

- モジュールエクスポート整理（src/kabusys/portfolio/__init__.py, src/kabusys/research/__init__.py, src/kabusys/tools/__init__.py）

### 変更
- DuckDB を分析用途の内部 DB として採用し、リサーチ・AI・一部集計処理で使用（duckdb 接続引数を各関数／クラスが受け取る設計）。
- 実行系と監視系で DB の使い分けを明確化：
  - 監視は常に本番 sqlite_path を参照して監視データを一元化。
  - Paper Trading 実行は paper_sqlite_path を用いて本番と完全分離（KABUSYS_ENV に依存）。

### 修正（バグ修正 / 安全性）
- 環境変数のパースを強化し、クォートやエスケープを正しく処理して .env の柔軟性を改善。
- プロセス優先度設定・CPU affinity の失敗を例外で止めず警告ログに留めることで起動の堅牢性を向上。
- ポジションサイズ計算で price が欠損した場合にスキップするロジックにより除外・安全化（ログ出力あり）。
- Paper Trading レポート生成でテーブル欠損時に OperationalError をキャッチして N/A を出力するフォールバックを追加。

### ドキュメント（コード内ドキュメンテーション）
- 各モジュールに設計方針・使用法・注意点を詳細に docstring とコメントで記載（例: PortfolioConstruction.md, StrategyModel.md を参照する旨の注記）。
- tools/paper_verification_report に使用例と環境変数の説明を追加。

### 既知の制約・注意事項
- apply_sector_cap:
  - price_map に price が欠損（0.0）だとエクスポージャーが過少見積もられるため将来的にフォールバック価格導入を検討中（TODO 注記あり）。
- position_sizing:
  - 現状 lot_size はグローバル共通値で、将来は銘柄別 lot_map に拡張予定（TODO 注記あり）。
- ai/news_nlp:
  - OpenAI API を使用するため API キー（OPENAI_API_KEY）の管理が必要。大規模運用時はレート制限とコスト管理に注意。
  - 実装はフェイルセーフ設計（API 失敗時に他処理を継続）だが、部分失敗時の DB 一貫性に配慮している（更新対象コードを絞るなど）。

### セキュリティ
- 必須トークン類（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）が未設定の場合は起動時に明示的エラーとすることで、意図しない無認証運用を防止。

---

（今後のリリース予定）
- 単体テスト・CI の整備、さらに詳細なエラー監視・アラート機能の追加予定。
- ニュース NLP の高速化（バッチ最適化・トークン最小化）とレスポンス検証の強化。
- portfolio サブモジュールの拡張（銘柄別 lot_size、price フォールバック、最適化手法の追加）。