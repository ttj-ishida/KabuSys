# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]

（現在未確定の変更はここに記載）

---

## [0.1.0] - 2026-04-16

最初のパブリックリリース。日本株自動売買フレームワーク "KabuSys" の初期実装を導入します。以下はコードベースから推測される主要な機能追加・設計方針・運用上の注意点です。

### Added
- コアライブラリ
  - パッケージ初期化とバージョン情報（kabusys.__version__ = 0.1.0）。
- 設定管理
  - `kabusys.config.Settings`：環境変数・.env ファイルから設定を読み込むユーティリティを提供。
    - プロジェクトルートの自動検出（.git または pyproject.toml 基準）。
    - .env / .env.local の読み込みロジック（OS 環境変数を保護）。
    - 必須環境変数の検査ヘルパー `_require`。
    - 各種設定プロパティ（DB パス、PaperTrading モード、監視閾値、PID/kill flag パス、KABUSYS_ENV 等）。
    - `PAPER_FILL_MODE`・`KABUSYS_ENV`・`LOG_LEVEL` の入力検証を実装。
- 実行/監視ランナー
  - `run_execution.py`：ExecutionEngine を起動するエントリポイント。
    - Paper trading 環境では専用 SQLite（`data/paper_trading.db`、環境変数で上書き可能）を利用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成と依存コンポーネント（OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine）の組立て。
    - スレッドでエンジンを実行し、外部停止フラグ（data/stop_requested.flag）検出で安全に停止。
    - 実行中 PID ファイルの管理（デフォルト: data/execution.pid）。
  - `run_monitoring.py`：SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書き（デフォルト 60 秒、無効値は警告のうえデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検出でループ終了。KeyboardInterrupt による終了処理を実装。
    - 起動時にプロセス優先度を "high" に設定（`kabusys.utils.process_priority` を使用）。
- ポートフォリオ構築モジュール（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定（スコア降順 + タイブレーク）、等金額配分・スコア加重配分ロジックを実装。
  - `kabusys.portfolio.position_sizing`
    - allocation_method（risk_based / equal / score）に基づく発注株数計算、lot_size 単位丸め、aggregate cap スケールダウンロジックを実装。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中排除ロジック（既存保有を考慮）と市場レジームに応じた投下資金乗数の計算。
- 実行側ユーティリティ
  - `kabusys.utils.process_priority`：Windows / POSIX を吸収したプロセス優先度設定・CPU affinity 設定（psutil を利用）。権限不足時は安全に警告してスキップ。
- 監視/解析ツール
  - `kabusys/tools/paper_verification_report.py`：Paper Trading 用の検証レポート生成スクリプト。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を行う CLI ツール（--from / --to / --db オプション対応）。
    - P95 計算、各テーブル存在チェック、データ欠損時のフォールバックに配慮。
- リサーチモジュール
  - `kabusys.research.factor_research`
    - Momentum / Volatility / Value といった主要ファクター計算（DuckDB を使った SQL ベースの実装）。
    - 200 日移動平均、ATR、出来高・売買代金等の計算を含む。
  - `kabusys.research.feature_exploration`
    - 将来リターン計算（任意ホライズン）、Spearman ランク相関（IC）計算、基本統計サマリーを純 Python 実装。
    - ランク計算で丸め（round(..., 12)）を用いて ties の安定処理を行う。
  - research パッケージのエクスポート (`zscore_normalize` を含む)。
- AI ニューススコアリング（下地実装）
  - `kabusys.ai.news_nlp`
    - raw_news を集約して OpenAI API（gpt-4o-mini）へバッチ送信し、銘柄単位のセンチメント（-1.0〜1.0）を ai_scores テーブルに書き込む設計。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）やトークン肥大化対策（記事数・文字数制限）、バッチサイズ、リトライ（指数バックオフ）などの堅牢化方針を実装。
    - API キー未指定時はエラーを返すバリデーションを実装。
    - 部分的に実装ファイルが途中で切れている（続き実装が想定される）。
- DB 初期化ユーティリティ
  - `kabusys.monitoring.monitoring_db.init_monitoring_db`（参照のみ、コードで呼び出しあり）：監視テーブルの存在を保証する冪等的初期化。

### Changed / Design decisions
- DB 分離ポリシー
  - Paper Trading 環境は本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db を使用）。
  - 監視（run_monitoring）は本番 sqlite_path を参照（環境に関係なく本番監視を行う判断）。
- 環境変数読み込み順序
  - OS 環境 > .env.local > .env の優先順位で読み込む（OS 環境は保護され上書きされない）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
- フェイルセーフ重視
  - 監視ループ・AI スコアリング・プロセス優先度設定等、外部エラー発生時はログ出力の上で処理を継続する（例外捕捉、警告ログ）。
  - run_execution・run_monitoring は停止フラグ検出で安全に終了する仕組みを持つ。
- 設定検証
  - `PAPER_FILL_MODE`, `KABUSYS_ENV`, `LOG_LEVEL` などは有効値チェックを行い、不正値は ValueError で明示。

### Fixed / Robustness improvements
- env ファイルパーサー強化
  - `_parse_env_line` がクォート内のエスケープやインラインコメントを適切に扱うように実装。
  - `export KEY=val` 形式に対応。
- レポートツールの耐障害性
  - テーブルが存在しない等の sqlite3.OperationalError を捕捉し、該当指標を N/A 等でフォールバックする処理を追加。
- ファクター・リサーチの境界条件処理
  - データ不足時に None を返す、ウィンドウサイズチェック（行数による判定）を実装。
- ポートフォリオ算出の端数処理
  - lot_size 単位での丸めと aggregate scaling 時の再配分アルゴリズム（残差順に lot を割当てる）を実装し、合計投資額が利用可能現金を超えないように制御。

### Removed
- 特になし（初期リリース）

### Security
- OpenAI API キー等の機密情報は環境変数による注入を想定。`.env.local` の使用や OS 環境の優先保護により直接上書きを防止する設計。

### Migration / 運用ノート（重要）
- 起動前に必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定してください。未設定時は Settings のプロパティアクセスで ValueError が発生します。
- Paper Trading を実行する際は `KABUSYS_ENV=paper_trading` を設定し、必要に応じて `PAPER_TRADING_SQLITE_PATH` と `PAPER_FILL_MODE` を指定してください。
- 監視はデフォルトで本番の sqlite_path を参照します。監視を Paper DB に向けたい場合は環境変数を適切に設定／スクリプトを調整してください（設計上は監視は本番 DB に対して動作する想定）。
- OpenAI を利用する機能（ai.news_nlp）は API キー（OPENAI_API_KEY）を必ず設定してください。キー未指定時は例外が発生します。
- `.env` 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト環境等で便利です）。
- `MONITOR_POLL_INTERVAL` は正の整数を指定してください。不正な値を指定すると警告ログのうえデフォルト（60 秒）にフォールバックします。
- 実行中のプロセス優先度設定は OS 権限に依存します。権限不足時は警告が出て設定はスキップされます。

---

開発中の機能や TODO はソース内コメントに記載しています（例: price 欠損時のフォールバック価格、AI スコアリングの続き実装等）。今後のリリースでは AI モジュールの完成、運用向けの監視強化、銘柄別 lot_size サポート、より詳細なログ／メトリクス出力などを予定しています。