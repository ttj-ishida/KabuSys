# CHANGELOG

すべての変化は Keep a Changelog の形式に準拠して記載しています。日付・内容はコードから推測して作成しています。

## [0.1.0] - 2026-04-20

### 追加 (Added)
- 全体
  - 初期バージョンとして主要コンポーネントを実装・公開。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。

- 実行用スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - ExecutionEngine をデーモンスレッドで起動し、停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）を扱う制御ループを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db 等）を使用して本番 DB と分離する挙動を実装。
    - BrokerClientFactory により環境に応じたブローカークライアントの生成を行う（MockBrokerClient を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立ておよび起動処理を実装。
  - 監視（SystemMonitor）起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - ポーリングループを実行し、MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能（デフォルト 60 秒）。
    - 停止フラグを検知して安全にループ終了する処理を実装。
    - 監視は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する仕様。

- 設定関連
  - 設定読み込み/管理モジュールを実装（src/kabusys/config.py）。
    - .env の自動ロード（プロジェクトルート検出による .env / .env.local の読み込み順）を実装。
    - .env の読み込みで OS 環境変数を保護する仕組み（protected set）を導入。
    - .env 行パーサを実装し、`export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
    - 環境変数から各種設定プロパティ（DB パス、API トークン、監視閾値、KABUSYS_ENV 判定など）を取得する Settings クラスを提供。
    - PAPER_FILL_MODE のバリデーション（有効値: "instant"|"partial"|"never"|"reject"）を実装。
    - paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）や各種閾値 (CPU/MEM/DISK) 等のプロパティを提供。

  - 設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - .env の対話式生成・更新をサポート。既存 .env 読み込み、シークレットマスク表示、保存機能を実装。
    - デフォルト値・選択肢・説明付きの項目群を定義し、ユーザーに入力を促す。

  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在チェックおよびパース検証（PyYAML が存在する場合）を行う。
    - KABUSYS_ENV=live の場合に本番用の注意喚起（LINE 設定未設定や Kill Switch 自動クリアの警告）を実装。
    - `--strict` オプションを用意（警告を FAIL 扱いにして exit(1)）。

- ポートフォリオ構築（ポートフォリオモジュール）
  - 銘柄選定 / 重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - BUY シグナルのスコアソート（同点時のタイブレーク）や等金額・スコア加重配分を実装。
    - スコア全てが 0 の場合は等金額にフォールバックし WARNING を出力。
  - セクター上限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - セクター集中を抑制する apply_sector_cap を実装（売却予定銘柄の除外や "unknown" セクターの扱い等）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull"=1.0 / "neutral"=0.7 / "bear"=0.3、未知は警告して 1.0 にフォールバック）。
  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - allocation_method に応じた発注株数計算を実装（"risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash 超過時のスケールダウン）および残差処理による追加配分ロジックを実装。
    - cost_buffer による保守的なコスト見積りにも対応。

- 監視・実行の共通ユーティリティ
  - ロギングセットアップユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout へ StreamHandler、ファイルへ TimedRotatingFileHandler（日次・30日保持）を設定する共通関数 setup_logging を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続するフォールバックを実装。
  - プロセス優先度 / CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX を吸収した set_process_priority と set_cpu_affinity を実装。権限不足や未対応 OS の場合はログ警告でスキップ。

- モニタリング DB 初期化
  - init_monitoring_db を呼び出して監視用テーブルの冪等な初期化を両エントリポイント（実行・監視）で行う実装を追加。

- DuckDB 統合（分析用）
  - duckdb 接続を各種コンポーネント（実行エンジン、監視、ファクター計算等）で受け渡す設計を採用。デフォルトの DUCKDB_PATH を提供。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均・最大・P95）などを SQLite の各テーブルから集計してレポート出力。
    - パス/フェイル基準（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms）を実装。
    - --from / --to / --db オプションをサポートし、PAPER_TRADING_SQLITE_PATH 環境変数を優先的に使用。

- 研究用ファクター計算（部分実装）
  - ファクター計算モジュールの骨組みを実装（src/kabusys/research/factor_research.py）。
    - Momentum/Value/Volatility/Liquidity の設計方針と定数を定義。DuckDB を用いた prices_daily/raw_financials 参照の想定。

### 変更 (Changed)
- ロギング/出力
  - ログ出力の StreamHandler を stderr ではなく stdout に統一（cron 等でのリダイレクトを考慮）。
  - 既存のルートロガーにハンドラが設定済みの場合、重複を避けるため一度ハンドラをクリアして再設定する仕様。

- DB/環境の取り扱い
  - 監視 (run_monitoring) は KABUSYS_ENV に関係なく監視用の sqlite_path（本番 DB）を使用する仕様になっている点を明記（コード上の仕様）。
  - run_execution では paper_trading モード時に paper_sqlite_path を使用して本番 DB と分離する挙動を明示。

- .env 自動ロードの挙動
  - プロジェクトルートの特定は .git または pyproject.toml を基準とし、CWD に依存しない探索を実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。

### 修正 (Fixed)
- 環境変数パースの堅牢化（src/kabusys/config.py）
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメントといった一般的な .env の表記を正しく解釈するよう改善。
  - 無効行のスキップや key の空欄チェック等の安全処理を追加。

- process_priority / cpu_affinity の失敗時フォールバック
  - 権限不足や未対応環境で例外が出ても警告ログを出し処理を継続するように変更。

- ログディレクトリ作成失敗の耐性（src/kabusys/utils/logging_setup.py）
  - ログディレクトリの作成に失敗した場合でも StreamHandler のみで動作を継続し、ユーザーへ警告を出力するように修正。

### ドキュメント / 注意事項 (Notes)
- config_setup により生成される .env は秘匿情報を含むため、コメントにある通り Git へコミットしないことが強く推奨されます。
- PAPER_FILL_MODE 等、一部環境変数には有効値チェックがあり、誤った値を設定すると起動時に例外が発生します。validate_config で事前チェックしてください。
- run_monitoring のポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能。1 未満の値や非整数はデフォルト（60 秒）へフォールバックします。
- research/factor_research.py は設計方針と定数が実装されていますが、一部関数実装が途中の可能性があるため、詳細な利用はコードの完成度を確認してください。

---

今後のリリース候補（想定）
- factor_research の完全実装（SQL クエリと正規化、出力形式の完成）
- ExecutionEngine / Monitoring の統合テストとエラーハンドリング強化
- 銘柄別 lot_size 対応（マスタ参照による単元数の差異対応）
- より細かなログやメトリクス（Prometheus 等）への出力機能

もし CHANGELOG を特定のコミット単位やファイル変更差分ベースで詳細化したい場合は、差分情報（git のコミットログなど）を提供してください。コードから推測した内容を元に作成しています。