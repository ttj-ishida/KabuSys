# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。  
各リリースは日付付きで記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース。

### Added
- 基本アプリケーションパッケージ "KabuSys" を追加。
  - バージョン情報: `kabusys.__version__ = "0.1.0"`。
- 設定管理
  - 環境変数および .env/.env.local からの自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - .env のパース機能を実装（export 形式、引用符付き値、インラインコメント対応）。
  - `Settings` クラスを追加し、アプリ全体から設定を安全に参照可能に（DBパス、APIキー、閾値など多数のプロパティを提供）。
- 起動/運用用スクリプト・CLI
  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書きが可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番の `sqlite_path` を使用する挙動を採用。
    - 停止フラグファイルを検知して安全にループ終了。
    - 起動時にプロセス優先度を "high" に設定。
  - `run_execution.py`：ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し、専用の Paper Trading SQLite (`data/paper_trading.db`) に記録して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグの監視と安全停止処理を実装。
  - `validate_config.py`：設定検証 CLI を追加。
    - .env と config/*.yaml の基本チェック（必須環境変数、KABUSYS_ENV 値、ログレベル、DB パスの親ディレクトリ存在確認、PyYAML があれば YAML パース検証）。
    - `--strict` オプションで警告を FAIL 扱いにできる。
  - `config_setup.py`：対話式 .env 作成・更新ウィザードを追加。
    - 設定項目の一覧と説明を表示し、既存値の再利用やデフォルト設定をサポート。
    - 保存時にテンプレート形式で .env を書き出す（注意文あり）。
  - `tools/paper_verification_report.py`：Paper Trading 検証レポート生成スクリプトを追加。
    - 指定期間の稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを出力。
    - 合格基準（稼働率 >= 99%、注文成功率 >= 90% 等）を設定し PASS/FAIL 判定を表示。
- ポートフォリオ構築モジュール（純粋関数群）
  - `portfolio.portfolio_builder`：
    - シグナルのランク・スコアに基づく候補選定（上位 N）。
    - 等分配重み（equal）およびスコア加重（score）計算関数を追加。スコアが全て0の場合は等分配にフォールバック。
  - `portfolio.risk_adjustment`：
    - セクター集中制限を適用する `apply_sector_cap` を追加（売却予定銘柄除外、"unknown" セクターの扱い等）。
    - 市場レジームに応じた資金乗数算出 `calc_regime_multiplier` を追加（bull/neutral/bear のマッピングと未知レジームのフォールバック）。
  - `portfolio.position_sizing`：
    - 各配分方式（risk_based / equal / score）に対応した株数決定ロジックを実装。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り、残差を利用した追加配分ロジックを実装。
  - `portfolio.__init__` で主要関数をエクスポート。
- ユーティリティ
  - `utils/logging_setup.py`：統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーションする TimedRotatingFileHandler（デフォルト logs/、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで動作。
    - 引数/環境変数でログレベル・ログディレクトリを解決。
  - `utils/process_priority.py`：プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）に対応した優先度設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定する機能を提供。
    - 権限不足などで設定できない場合は警告ログを出してスキップ。
- データ分析 / 研究基盤
  - `research/factor_research.py`：ファクター計算モジュールを追加（Momentum, Value, Volatility, Liquidity の設計方針を実装予定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する方針を実装。
    - （モジュールは部分実装。モメンタム計算関数の骨組みあり。）
- データベース初期化支援
  - `monitoring.monitoring_db.init_monitoring_db` 呼び出し箇所を run 系スクリプトに追加し、監視テーブルの存在を保証（冪等）。

### Changed
- 環境変数取り扱いと安全性
  - .env 読み込みは OS 環境変数を保護（protected set）して上書き制御を行う仕様に。
  - .env.local を .env の上書きとして優先的にロードする挙動を導入。
- ロギング
  - ログ出力は標準エラーではなく標準出力（stdout）に送るように変更。これにより外部のスケジューラ/cron でのリダイレクト扱いが容易に。
- 実行時振る舞い
  - run_monitoring は MONITOR_POLL_INTERVAL の値検証を追加。無効な値（0 以下や非整数）はデフォルト（60 秒）にフォールバックして警告を出力。
  - run_execution は paper_trading 環境では専用の SQLite を使用するよう明示（運用・テスト DB の分離）。
  - 両 run スクリプトは起動時にプロセス優先度を "high" にする処理を追加。
- validate_config の検証項目整理
  - 必須環境変数一覧、オプション一覧、config/*.yaml の存在チェック、PyYAML が無ければパース検証スキップする柔軟性を実装。
  - KABUSYS_ENV=live 時の追加ガード（LINE 設定未設定や KILL_FLAG_CLEAR_ON_START の危険設定への警告）を追加。

### Fixed
- .env パーサの改善により以下を正しく扱えるように修正/実装：
  - 値が引用符で囲まれている場合のバックスラッシュエスケープ処理（クォート内はインラインコメントを無視）。
  - export KEY=val 形式のサポート。
  - クォートなし値でのコメント認識（'#' 前にスペースがある場合のみコメント扱い）。
- ログハンドラ重複設定防止のため、既存のルートロガーのハンドラをクリアしてから再設定するように修正。

### Security
- .env ファイル生成時の注意喚起を README 相当のヘッダに追加（.env を絶対に Git にコミットしない旨を明記）。

---

今後の予定（例）
- research/factor_research の完全実装（各ファクターの具体的算出と正規化パイプライン）。
- ExecutionEngine / Reconciler / BrokerClient の詳細なユニットテスト追加。
- 単体テスト・CI の整備、コンテナ化、運用向けドキュメントの充実。

---
記載はコードベースの現状から推測して作成しています。実際の変更履歴やリリースノート作成時はコミットログやリリース手順に基づいて差分を確定してください。