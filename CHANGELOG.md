# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

- （現在未リリースの変更なし）

## [0.1.0] - 2026-04-25

初回リリース。以下の主要機能・ユーティリティを追加しました。

### 追加 (Added)

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成。
    - ExecutionEngine をスレッドで起動し、data/stop_requested.flag による停止フラグ監視を実装。
    - 実行中 PID を data/execution.pid に保存する仕組み（pid_file 引数で指定）。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化（init_monitoring_db 呼び出し）。
    - data/stop_requested.flag による優雅な停止検知を実装。

- 環境設定 / 構成関連
  - config.py
    - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env / .env.local の読み込みルール（OS 環境変数優先、.env.local は上書き可能）を実装。
    - 複雑な .env パースロジックを実装（export プレフィックス、クォート文字列、インラインコメント処理等）。
    - Settings クラスを追加し、各種設定（J-Quants トークン、kabu API、DB パス、ログレベル、監視閾値など）をプロパティで提供。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, KILL_FLAG_CLEAR_ON_START などのオプションをサポートし、値検証を実施。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成/更新する CLI を追加。
    - デフォルト値・選択肢・機密入力（マスク）をサポートし、ファイル書き込みを行う。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在・パース検証を実装。
    - --strict オプションで警告も失敗として扱う。

- ロギング / プロセス管理
  - utils/logging_setup.py
    - 共通のログ設定ユーティリティを追加。
    - stdout への StreamHandler と 日次ローテート（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決ルールを実装。ログディレクトリ作成失敗時はファイル出力をスキップしコンソールのみで継続。
  - utils/process_priority.py
    - プロセス優先度 (high/normal/low) と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX (Linux, Darwin, FreeBSD) の差を吸収して nice / priority を設定。権限不足等は警告でスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - buy シグナルの候補選定 (select_candidates) と、等配分・スコア加重の重み計算 (calc_equal_weights, calc_score_weights) を実装。スコア総和が 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（売却予定コードの除外、"unknown" セクターは無視）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear->1.0/0.7/0.3、未知レジームは警告の上 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: "risk_based", "equal", "score" をサポート）。
    - 単元株 (lot_size) に基づく丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング） 、cost_buffer（手数料/スリッページ見積）を考慮したスケーリング・残差配分ロジックを実装。
    - 不足データ（価格欠損等）はスキップし、ログ出力で通知。

- リサーチ / 指標生成（部分実装）
  - research/factor_research.py
    - モメンタム・ボラティリティ・流動性・バリュー等の計算モジュールとしての骨格を追加。DuckDB 接続を受け取って prices_daily / raw_financials を参照する方針を明記。
    - P95 計算ユーティリティなどを実装（関数の一部は継続実装予定）。

- ツール類
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、P95 レイテンシなどを算出。閾値はソース内で定義（例: 稼働率 >= 99%、P95 <= 200 ms 等）。
    - --from/--to/--db オプションで期間・DB を指定可能。DB 存在チェックとエラー回避を実装。

- パッケージ情報
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。

### 変更 (Changed)

- なし（初回リリースのため変更履歴はなし）。

### 修正 (Fixed)

- なし（初回リリースのため修正履歴はなし）。

### 既知の注意点 / TODO

- portfolio.position_sizing の価格 0.0 または欠損時の扱いに TODO コメントあり（将来的に前日終値や取得原価でフォールバックする可能性）。
- research/factor_research.py はファイル末尾で切れており、モメンタム計算の続きが未完（追加実装が必要）。
- ログディレクトリ作成やプロセス優先度設定は権限不足の環境で失敗する可能性があり、その場合は警告でスキップする実装。
- config の自動読み込みはプロジェクトルート検出に依存するため、配布環境では KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。

### セキュリティ (Security)

- .env ファイルは機密情報を含むため、config_setup のヘッダに「.env は絶対に Git にコミットしないこと」と明記。
- 環境変数が未設定の場合、起動時に明確なエラーを出す設計（Settings._require）。

---

注: 上記は現行コードベースから機能と設計意図を推測して作成した CHANGELOG です。今後の変更はこの形式に従って追記してください。