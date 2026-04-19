# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
日付はリリース時点の目安です（変更履歴はコードから推測して作成しています）。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース。日本株自動売買システム KabuSys の基本機能を実装しました。

### 追加 (Added)
- 基本パッケージとバージョン情報
  - パッケージ初期化: `kabusys.__version__ = "0.1.0"` を導入。

- 起動スクリプト
  - `run_execution.py`：ExecutionEngine を起動するエントリポイントを追加。  
    - KABUSYS_ENV による Paper Trading モードの分離（MockBrokerClient を使用、paper_trading 用 SQLite に記録）。
    - プロセス優先度設定、高速ログ出力、PID ファイル、停止フラグ検知をサポート。
  - `run_monitoring.py`：SystemMonitor のポーリングループを実行するスクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番の sqlite_path を使用する点を明示。

- 設定管理
  - `config.py`：環境変数/.env 読み込みロジックと Settings クラスを実装。  
    - プロジェクトルート自動検出（.git / pyproject.toml 基準）による .env の自動読み込み（.env.local が .env を上書き）。  
    - 必須環境変数取得ヘルパ (`_require`) と各種設定プロパティ（DB パス、KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
    - PAPER_FILL_MODE の検証、有効値チェックを実施。
  - `.env` 作成・更新支援 CLI: `config_setup.py` を追加（対話式ウィザードで .env を生成 / 更新）。
  - 設定検証 CLI: `validate_config.py` を追加（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス、config/*.yaml の存在と YAML パース検査、`--strict` オプション）。

- ポートフォリオ構築ライブラリ
  - `portfolio/portfolio_builder.py`：候補選定・重み計算（等金額・スコア加重）を実装。
  - `portfolio/risk_adjustment.py`：セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
  - `portfolio/position_sizing.py`：ポジションサイズ計算（risk_based / equal / score）および aggregate cap によるスケーリング・単元丸めを実装。
  - `portfolio/__init__.py`：エクスポートをまとめたモジュールを追加。

- ユーティリティ
  - `utils/logging_setup.py`：統一ログ設定ユーティリティを追加。  
    - stdout への StreamHandler と 日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。  
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続するフォールバックを実装。
  - `utils/process_priority.py`：プラットフォーム差分を吸収したプロセス優先度設定と CPU affinity 設定を追加（Windows / POSIX 対応、失敗時は警告）。
  - `utils/__init__.py`：ユーティリティパッケージ化。

- 監視・検証ツール
  - `monitoring` 関連（DB 初期化 / SystemMonitor）は起動スクリプトから利用する設計を追加（init_monitoring_db を使用して監視テーブルの存在を保証）。
  - `tools/paper_verification_report.py`：Paper Trading の検証レポート生成スクリプトを追加。  
    - 稼働率、注文成功率、送信率、レイテンシ（平均 / 最大 / P95）などを算出して PASS/FAIL 判定を行う。  
    - デフォルト DB パスは `PAPER_TRADING_SQLITE_PATH` 環境変数または `data/paper_trading.db`。

- 研究 / 指標計算
  - `research/factor_research.py`：DuckDB を使ったファクター計算モジュール（Momentum, Value, Volatility, Liquidity）を用意（設計コメント・定数を含む）。

### 変更 (Changed)
- 環境変数読み込みのポリシー
  - OS 環境変数を優先し、`.env` と `.env.local` を自動で読み込む挙動を実装（`.env.local` が `.env` を上書き）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - `.env` 読み込み時に既存 OS 環境変数を保護するため protected セットを使った上書き制御を導入。

- ログ出力
  - ログレベル解決順とログディレクトリ解決順を明確化（引数 > 環境変数 > デフォルト）。

- DB 接続
  - Monitoring の DB 初期化は冪等（init_monitoring_db を呼ぶことでテーブルが存在することを保証）で Execution と Monitoring が適切に DB を作成・利用できるようにした。

### 修正 (Fixed)
- 環境変数パースの堅牢化
  - `_parse_env_line` において引用符付き値のエスケープ処理や、インラインコメントの扱い、`export KEY=val` 形式への対応を実装し、不正な行を無視するようにした。
  - `_get_poll_interval`（監視ポーリング間隔）で負の値や 0 を入力した場合にデフォルトへフォールバックするロジックを追加し、time.sleep での ValueError を回避。

- ログハンドラの二重登録防止
  - setup_logging() が既存ハンドラを flush/close してから削除し、二重設定を防止するようにした。

- プロセス優先度設定のフォールバック処理
  - 権限不足や未サポート環境での例外をキャッチし、警告を出して処理を続行するようにした。

- Paper Trading の分離
  - paper_trading モード時は `paper_sqlite_path` を使用して本番 DB と完全分離するよう修正（発注ログ・監視データの混在防止）。

- レポート生成の堅牢化
  - `paper_verification_report.py` の各クエリでテーブルが存在しない場合の sqlite3.OperationalError を捕捉して安全に N/A を返すようにした。
  - P95 計算関数 `_p95` を追加してパーセンタイル計算に対応。

### 既知の注意点 / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO コメントあり。
- portfolio/position_sizing:
  - 現状は全銘柄共通の lot_size（デフォルト 100）を使用。将来的には銘柄別単元情報を持たせる設計を予定している。
- research/factor_research:
  - ファクター計算関数は設計に沿って実装されているが、環境やデータ依存で動作するため実データでの検証が必要。

### セキュリティ (Security)
- 重要なシークレット（J-Quants リフレッシュトークン、kabu API パスワード）は .env に保存しない/コミットしない旨をドキュメントに明記（config_setup にも注意書きあり）。
- validate_config による本番環境（KABUSYS_ENV=live）でのガードチェックを実装（LINE 通知設定の未設定や Kill Switch 自動クリア設定の警告）。

---

この CHANGELOG はコードベースの内容から推測して作成しています。実際にプロジェクトで管理している変更履歴がある場合はそれに合わせて更新してください。