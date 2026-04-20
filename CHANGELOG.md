# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはリポジトリのコードベースから推測して作成した変更履歴です。

## [0.1.0] - 2026-04-20

### 追加 (Added)
- 初期リリースとしてコア機能を追加。
- 実行スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、paper_trading 環境時の DB 分離、Engine のデーモンスレッド起動、停止フラグ検出と安全終了処理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能。停止フラグ検知による終了処理を実装。
- 設定管理
  - config.py: 環境変数/`.env` の自動読み込み機能を実装（プロジェクトルート検出、`.env` / `.env.local` の読み込み順制御、保護キーの考慮）。Settings クラスを提供し、各種設定値（DB パス、API トークン、運用環境フラグ、監視閾値 など）をプロパティで安全に取得可能に。
- 設定ツール / 検証
  - config_setup.py: 対話式の環境設定ウィザードを追加。`.env` の初期作成・更新を支援。
  - validate_config.py: 起動前設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスや config/*.yaml の存在チェック、`--strict` モードを備える。
- ポートフォリオ構築モジュール
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア重み配分（calc_score_weights）を追加。
  - portfolio.risk_adjustment: セクター集中上限適用（apply_sector_cap）、市場レジームに応じた乗数計算（calc_regime_multiplier）を追加。
  - portfolio.position_sizing: 各銘柄の株数算出ロジック（risk_based / equal / score の allocation_method 対応）、単元株丸め、集計 cap によるスケールダウンロジックを追加。
  - portfolio パッケージの __init__ を追加し、主要関数をエクスポート。
- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。stdout StreamHandler と 日次ローテーションの TimedRotatingFileHandler をルートロガーへ設定し、LOG_DIR/LOG_LEVEL との連携、既存ハンドラの安全なクリアを実装。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定を追加。パーミッションエラー等は警告でスキップ。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計し、PASS/FAIL 判定を出力。PAPER_TRADING_SQLITE_PATH やコマンドライン引数で期間・DB を指定可能。
- リサーチ
  - research/factor_research.py（途中実装）: DuckDB を使ったファクター計算モジュールの骨格を追加（モメンタム等の仕様・定数を含む）。

### 変更 (Changed)
- ログ出力方針
  - ログは stdout を標準出力に出す構成を採用（cron/task scheduler でリダイレクトしやすいよう stderr ではなく stdout を使用）。
  - ログファイルはデフォルトで logs/<app_name>.log に日次ローテーション（30日分保持）。
- DB の扱い
  - 実行系の paper_trading 環境では paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
  - 監視 (monitoring) は環境に依らず本番用 sqlite_path を使う仕様を明示（監視データは一元管理）。
- .env 読み込み
  - .env のパースを強化（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ処理、インラインコメント処理、override/protected の仕組み）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
- 設定検証の挙動
  - validate_config で PyYAML が未インストールの場合は YAML 検証をスキップし警告を出すように変更。
  - 本番(env=live)時の安全ガード（LINE 通知の未設定、KILL_FLAG_CLEAR_ON_START の注意喚起）を追加。

### 修正 (Fixed)
- 環境変数の不正値に対して、明示的なメッセージやフォールバックを追加
  - MONITOR_POLL_INTERVAL が不正（非数値や <= 0）の場合、デフォルト 60 秒へフォールバックして警告ログを出力。
  - PAPER_FILL_MODE の値検証を追加し、不正な値で ValueError を送出するように。
  - Settings.env / log_level の不正値で明確な ValueError を投げるようにして起動時に早期検出可能に。
- プロセス優先度設定や CPU affinity 設定で発生するパーミッション例外を警告に変換し、プロセス継続を保証。

### ドキュメント・メッセージ (Documentation)
- 各モジュールに日本語の docstring を追加し、仕様・設計方針（例えば portfolio の設計参照ドキュメントや関数の引数説明）を明記。
- config_setup の対話ウィザードで生成される .env テンプレートに注意書きを追加（.env を絶対に Git にコミットしない等）。
- tools/paper_verification_report にしきい値（稼働率、成功率、レイテンシなど）のデフォルト基準を定義。

### 既知の制約 / TODO
- research/factor_research.py は一部（calc_momentum の実装開始）で途中ファイルが含まれており、完全実装が必要。
- position_sizing の価格欠損時のフォールバック（前日終値など）に関する TODO が残っている。
- stocks ごとの lot_size を持つ拡張（銘柄別単元対応）は将来的な課題としてコメントあり。

---

注: 上記はソースコードの中身から推測して作成した CHANGELOG です。実際の開発履歴・コミットメッセージとは差異がある可能性があります。必要であれば、各モジュールの変更点をさらに細かく分割（例えば minor/patch レベルで分ける）して更新できます。