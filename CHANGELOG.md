# CHANGELOG

すべての変更は Keep a Changelog の慣習に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/ を参照してください。

注: 以下の履歴は提供されたコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートに合わせて適宜調整してください。

## [Unreleased]

### 追加
- （今後のリリース用のプレースホルダ）

---

## [0.1.0] - 2026-04-19
初回公開リリース。KabuSys のコアユーティリティ、実行エンジン起動スクリプト、監視、設定管理、ポートフォリオ構築／ポジション決定ロジック、調査ツール等を含む。

### 追加
- コアパッケージ
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - パッケージ公開用のエクスポートを設定（data, strategy, execution, monitoring）。

- 実行・監視ランナー
  - run_execution.py
    - ExecutionEngine 起動用スクリプトを追加。
    - プロセス優先度を起動時に "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を利用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のバックグラウンドスレッド実行をサポート。
    - 停止フラグ（data/stop_requested.flag）と PID ファイルによる制御を実装。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書き（デフォルト 60 秒）をサポート。無効値はデフォルトにフォールバックして警告を出力。
    - 監視（monitoring）は環境にかかわらず本番用の sqlite_path を使用する設計（設定ファイル参照）。
    - 停止フラグ検知でループ終了、例外発生時はログを残して次ループに復帰。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
    - .env/.env.local の読み込み順序と OS 環境変数保護（protected）に対応。
    - .env の行パースロジックを強化（export プレフィックス、クォート文字列、エスケープ、インラインコメントの処理）。
    - 各種設定プロパティ（J-Quants トークン、kabu API パスワード、DB パス、paper trading のモード等）を提供する Settings クラスを追加。
    - KABUSYS_ENV / LOG_LEVEL 等のバリデーションを実装。
    - settings インスタンスをデフォルトでエクスポート。

  - config_setup.py
    - 対話式 .env ウィザードを追加（.env の初期作成・更新を支援）。
    - デフォルト値、選択肢、シークレット項目のマスク表示、保存前の確認を実装。
    - .env ファイルの読み書きフォーマットを定義（ファイルにコメント付きで保存）。

  - validate_config.py
    - 起動前に .env と config/*.yaml の不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の検証、DB パスの親ディレクトリ確認、YAML の存在・パースチェック（PyYAML 未インストール時はスキップ）、live 環境用ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
    - --strict オプションで警告を FAIL 扱いにする機能を提供。

- ロギング／プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定関数 `setup_logging` を追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順と、ログディレクトリ作成失敗時にファイル出力をスキップするフェイルセーフを実装。
  - utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定 `set_process_priority` を追加（Windows / POSIX の実装）。
    - CPU affinity を固定する `set_cpu_affinity` を追加（psutil を使用、利用不可時は警告を出力）。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順、タイブレークは signal_rank）`select_candidates` を追加。
    - 等金額配分 `calc_equal_weights` とスコア加重配分 `calc_score_weights` を実装。全スコアが 0 の場合は等金額にフォールバックして警告出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する `apply_sector_cap` を追加（既存保有エクスポージャ計算、売却予定銘柄の除外、"unknown" セクターは制限対象外）。
    - 市場レジームに基づく投下資金乗数 `calc_regime_multiplier` を追加（bull/neutral/bear のマッピング、未知レジームは警告のうえ 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - position sizing ロジック `calc_position_sizes` を追加。
    - allocation_method に応じて "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、利用可能現金による aggregate cap、cost_buffer（手数料・スリッページ見積り）考慮、スケールダウン時の残差処理アルゴリズムなどを実装。

  - portfolio/__init__.py で上記関数を公開。

- リサーチ
  - research/factor_research.py（ファクター計算の下地を追加）
    - DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等のファクターを計算する設計。
    - 定数・計算方針（窓長、スキャン範囲）を記載。関数 calc_momentum の実装途中（ファイル末尾が途中で切れていることを示唆）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から集計して検証レポートを生成する CLI を追加。
    - システム稼働率、注文成功率（Fill / Send）、リスク却下数、レイテンシ（平均・最大・P95）を集計し PASS/FAIL を判定する閾値を実装。
    - P95 計算、日付フィルタ（ISO8601 UTC 文字列化）および CLI オプション（--from/--to/--db）を提供。
    - データ欠損やテーブル未存在時のフェイルセーフ処理を実装。

- DB 初期化ヘルパ
  - monitoring/monitoring_db.init_monitoring_db の呼び出しを行い、起動時に監視テーブルが存在することを保証（冪等で呼べる）。

### 変更
- 設定の挙動
  - .env 自動ロード機能を追加。既存 OS 環境変数はデフォルトで保護され、.env.local の値は .env を上書き可能（ただし OS 環境変数は保護）。
  - Settings クラスによりアプリ全体で統一的に環境変数を参照・検証可能に。

- 実行プロセス管理
  - run_execution と run_monitoring でプロセス優先度を最初に "high" に設定するよう統一。

### 修正（バグ／耐障害性）
- .env パーサーの堅牢化
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを改善。
- logging_setup の堅牢性向上
  - ログディレクトリ作成に失敗した場合でもコンソールログで継続するようにし、既存ハンドラの二重登録を防止するためハンドラを一旦クリアしてから再設定する。
- process_priority での例外処理強化
  - psutil の権限不足や未対応 OS での例外をキャッチして警告を出力し、起動継続するようにした。

### ドキュメント（コード内コメント／注記）
- 各モジュールに設計方針や注意点を詳細にコメントとして追加（例: portfolio の設計参照ドキュメント、regime の注意、将来的な拡張点の TODO）。
- config_setup の出力メッセージに validate_config の実行推奨を記載。

### 既知の制限 / TODO
- research/factor_research.calc_momentum の実装が途中（ファイルが途中で終端している）である旨を示唆（追加実装が必要）。
- position_sizing の price 欠損時のフォールバック（前日終値など）に関する TODO を残す。
- 将来的に銘柄ごとの lot_size をサポートするための設計拡張案をコメントに記載。

---

今後の更新では、以下を想定しています（例）:
- research モジュールの完成（ファクター計算の実装完了とテスト追加）
- ExecutionEngine / SystemMonitor の単体テスト追加
- ドキュメント（README、運用手順）の整備
- CI の導入・設定ファイルの追加

（必要に応じて、各項目をリリースノートの粒度に合わせて分割・追記してください。）