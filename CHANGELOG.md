# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。  
このファイルはソースコードから推測して作成したため、実際のコミット履歴と差異がある場合があります。

## [0.1.0] - 2026-04-18 (初回リリース)
初回公開リリース。自動売買システム KabuSys のコアユーティリティ、実行・監視ランナー、設定関連ツール、ポートフォリオ構築ロジック、テスト/検証ツール群を含みます。

### 追加 (Added)
- 全体
  - パッケージ初回実装。バージョンは `__version__ = "0.1.0"`。
  - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を探索）。
  - .env 自動読み込み: OS環境 > .env.local > .env の優先順位でロード。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロード無効化可能。
  - .env 読み込みの堅牢化: export プレフィックス、クォート文字列、エスケープ、インラインコメント等に対応するパーサ実装。

- 設定関連 CLI
  - 環境設定ウィザード `kabusys.config_setup` を追加（対話式 .env 生成/更新）。
    - 各項目の説明表示、シークレット値はマスク表示、既存値の再利用をサポート。
    - デフォルト値・選択肢の案内、保存確認プロンプト、.env の書き出しロジックを実装。
  - 設定検証ツール `kabusys.validate_config` を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在チェック、KABUSYS_ENV=live 向けの追加ガードを実装。
    - `--strict` オプションで警告も失敗扱いにできる。

- 実行・監視ランナー
  - 実行エンジン起動スクリプト `run_execution.py` を追加。
    - 環境に応じた SQLite 接続: `paper_trading` 環境では paper 用 DB（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離。
    - ブローカークライアントの抽象化 Factory を使用して本番/モック切替を可能にする設計。
    - ExecutionEngine の起動、デーモンスレッドでの実行、停止フラグ（data/stop_requested.flag）検知による安全停止、PID ファイル管理に対応。
    - RiskManager / OrderManager / Reconciler 等の組み立てロジックを用意。
  - 監視ループ起動スクリプト `run_monitoring.py` を追加。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境に関わらず本番の sqlite_path を使用し（監視 DB の一貫性を保つため）、duckdb も併用。
    - 停止フラグ検知でループを終了、例外時もループ継続する耐障害性を有する。

- ロギング・プロセス管理ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加。
    - stdout に出力する StreamHandler と日次ローテーション（TimedRotatingFileHandler）を用いたファイル出力（デフォルト logs/）を設定。
    - 既存ハンドラのクリーンアップ、ログレベル・ログディレクトリ解決ロジックを実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - `kabusys.utils.process_priority` を追加。
    - Windows / POSIX（Linux, macOS, FreeBSD）向けにプロセス優先度（high/normal/low）を設定するユーティリティ。
    - CPU affinity を最初の N コアに固定する関数も提供。
    - 権限エラーや未対応 OS では安全にスキップし警告ログを出力。

- ポートフォリオ構築（純粋関数）
  - `kabusys.portfolio.portfolio_builder`
    - BUY シグナルの候補抽出（スコア降順、タイブレークルール）、等金額配分、スコア加重配分を実装。
  - `kabusys.portfolio.position_sizing`
    - 発注株数決定ロジック（`risk_based` / `equal` / `score`）を実装。単元株（lot_size）丸め、1銘柄上限・aggregate cap、コストバッファ対応、スケーリングと端数分配アルゴリズムを含む。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。Regime の未知値はフォールバックで警告ログ。

- リサーチ
  - `kabusys.research.factor_research` を追加（モメンタム等のファクター計算を実装する設計）。DuckDB 接続を受け取り prices_daily / raw_financials を参照して各種ファクターを計算する方針を実装。 （ファイル末尾は一部未完の可能性あり）

- ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - Paper Trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH`）から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計しレポートを出力。
    - Pass/Fail 基準（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義して判定を行う。
    - コマンドライン引数 `--from`/`--to`/`--db` をサポート。

### 変更 (Changed)
- 設定 API
  - Settings クラスで各種環境変数取得を整理:
    - デフォルト値を明示（例: KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH 等）。
    - `paper_fill_mode` のバリデーションを追加（"instant"|"partial"|"never"|"reject" のみ許容）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性検証を行い、不正値は ValueError を送出。

- 監視 / 実行周りの挙動
  - 監視・実行起動時にプロセス優先度を最初に "high" に設定するよう統一。
  - 監視 DB の初期化（init_monitoring_db）は冪等的に行い、存在確認とテーブル作成を保証。

- .env 操作
  - `.env` 書き出しのフォーマットとコメントを整備（config_setup の `_write_env`）。

### 修正 (Fixed)
- 不正な環境変数値の安全ハンドリングを強化：
  - `MONITOR_POLL_INTERVAL` の不正な値（非整数や 0 以下）を検出して警告を出し、デフォルトにフォールバックするロジックを追加。
  - .env の読み込みで権限エラーが発生した場合に警告を出すよう変更（読み込み失敗で例外破壊しない）。

- エラーハンドリング強化：
  - 監視ループ内で monitor.check_once() が例外を投げてもループを継続し、例外情報をログに残して次回ポーリングへ進むようにした。
  - Logging 設定時にファイルハンドラ作成に失敗してもコンソール出力にフォールバックするように改善。

### 注意事項 / 既知の制約 (Known issues)
- factor_research のファイル末尾が途中で切れている（実装の継続が必要な箇所がある可能性あり）。
- 一部の機能は外部ライブラリ（psutil, duckdb, PyYAML 等）に依存。PyYAML が存在しない場合は config/*.yaml の検証がスキップされる（警告）。
- process priority / cpu affinity は OS と実行権限に依存するため、権限不足時は設定がスキップされる（警告を出力）。
- .env パーサは多くのケースに対応しているが、非常に複雑なシェル拡張記法などはサポート対象外。

### マイグレーション / 運用メモ
- 本番運用前に `kabusys.config_setup` で .env を作成し、`python -m kabusys.validate_config` で検証してください。
- Paper Trading を使う場合は `KABUSYS_ENV=paper_trading` を設定し、`PAPER_TRADING_SQLITE_PATH` を指定することで本番 DB と分離して動作します。
- ログはデフォルトで logs/ に日次ローテーションで出力されます。必要に応じて `LOG_DIR` 環境変数や setup_logging の引数で変更してください。
- 監視のポーリング間隔は `MONITOR_POLL_INTERVAL` で変更可能（秒）。不正指定時は 60 秒にフォールバックします。

---

今後のリリースでは、factor_research の完全実装、戦略およびエンジンの統合テスト、YAML 設定の詳細検証、ロギング・監視の拡張（アラート連携等）を予定してください。