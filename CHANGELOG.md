# Changelog

すべての重要な変更点は Keep a Changelog の形式に準拠して記載しています。  
このファイルは手元のコードベースから推測して作成した変更履歴です。

全ての日付は 2026-04-25（本作成日）です。

## [0.1.0] - 2026-04-25

### 追加 (Added)
- 基本的なアプリケーション骨格を追加
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。
- 環境設定管理
  - Settings クラスを実装し環境変数経由で設定取得を提供（src/kabusys/config.py）。
  - .env 自動読み込み機能を実装（OS 環境変数 > .env.local > .env の優先順位、`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
  - .env パース機能を堅牢に実装（クォート、エスケープ、export 形式、行内コメント処理など）。
  - config_setup：対話式 .env 作成/更新ウィザードを追加（python -m kabusys.config_setup）。
- 設定検証ツール
  - validate_config CLI を追加。必須環境変数やファイルパス、config/*.yaml の存在・パース検証（PyYAML 未導入時は検証スキップの挙動）を行う（python -m kabusys.validate_config）。
- 実行系ランチャー
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - `KABUSYS_ENV=paper_trading` 時は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（paper/live に応じて Mock/実クライアントを想定）。
    - エンジンの PID ファイル、停止フラグ（data/stop_requested.flag）を扱うロジックを実装。
- 監視系ランチャー
  - SystemMonitor のポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒、無効値はデフォルトへフォールバック）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する挙動を実装。
    - stop フラグ検知でループを終了する安全なシャットダウン処理。
- 監視 DB 初期化ユーティリティ（init_monitoring_db）呼び出しを各起動スクリプトで保証。
- ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）
  - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定する共通関数 `setup_logging()`。
  - LOG_DIR 作成失敗時はファイル出力を無効化してコンソール出力のみで継続するフォールバック実装。
- プロセス優先度 / CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）
  - Windows / POSIX 差分を吸収し、`set_process_priority()` と `set_cpu_affinity()` を提供（psutil 利用、権限不足や未対応 OS の場合は警告でスキップ）。
- ポートフォリオ構築ライブラリを追加（src/kabusys/portfolio/*）
  - 候補選定、重み計算（等分・スコア加重）を実装（portfolio_builder.py）。
  - セクター集中制限とレジームに応じた資金乗数を実装（risk_adjustment.py）。
  - 株数算出（リスクベース / equal / score）・単元丸め・aggregate cap スケーリングなどを実装（position_sizing.py）。
  - 上記をパッケージとしてエクスポート（src/kabusys/portfolio/__init__.py）。
- Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）
  - paper_trading 用 SQLite（環境変数 `PAPER_TRADING_SQLITE_PATH` またはデフォルト）から指標を抽出し、稼働率・注文成功率・送信率・P95 レイテンシ等を算出してレポート出力。
  - PASS/FAIL 判定基準（稼働率、成功率等）をコード内定数で定義。
- 研究用ファクター計算モジュールの骨格を追加（src/kabusys/research/factor_research.py）
  - momentum 等の指標設計（関数シグネチャ、定数）を実装（実装途中のファイルあり）。

### 変更 (Changed)
- なし（初期リリースのため新規実装が主体）。

### 修正 (Fixed)
- なし（初期リリースのためバグ修正履歴は無し）。

### 注意点 / 実装上の考慮 (Notes)
- Settings / .env の自動読み込みはプロジェクトルートを .git または pyproject.toml で判定して行うため、配布後や CI での挙動に注意が必要（見つからない場合は自動ロードをスキップ）。
- .env 読み込みでは OS 環境変数の保護（protected set）を行い、.env.local は .env を上書きするが OS 環境変数は上書きしない設計。
- process_priority の設定は権限不足や未対応 OS の場合に警告してスキップするため、必ず設定されることを保証しない点に注意。
- portfolio/position_sizing の計算には価格マップが必須。価格欠損時は該当銘柄をスキップする挙動になっている（TODO コメントでフォールバック価格の検討あり）。
- validate_config は PyYAML が未インストール時に YAML 検証をスキップする（警告出力）。CI 等では PyYAML の導入を推奨。
- research/factor_research.py は一部未完（ファイル末尾が途中で切れているため実装継続が必要）。

### 既知の TODO / 改善ポイント
- price の欠損時のフォールバック（前日終値や取得原価など）を実装し、エクスポージャー算出精度を改善する。
- 個別銘柄の lot_size をマスタに持たせるなど、単元対応の柔軟化。
- factor_research の完全実装とユニットテスト追加。
- ログ回転・ファイルハンドラのテスト強化（権限や特殊環境下での挙動確認）。
- 起動スクリプトのエラーハンドリングと健全なシャットダウン手順の更なる強化。

### セキュリティ (Security)
- 本リリースでは機密情報（API トークン・パスワード）を .env に保存する前提のため、.env を Git 等にコミットしない旨をドキュメント・config_setup に明記済み。環境運用時は適切なシークレット管理を推奨。

---

（今後のリリースでは機能追加や bugfix をここに追記してください。）