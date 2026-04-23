# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

最新リリース: [0.1.0] - 2026-04-23

## [Unreleased]
- なし

## [0.1.0] - 2026-04-23
初回公開リリース。コードベースから推測される主要機能・実装内容を以下にまとめます。

### 追加
- 基本アプリケーション情報
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。

- 実行エントリ & ランナー
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV が `paper_trading` の場合は paper-trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用する設計。
    - BrokerClientFactory を用いてブローカークライアントを生成（MockBrokerClient を含む想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler 等の依存コンポーネントを組み立て、ExecutionEngine を別スレッドで実行。
    - 停止フラグ（data/stop_requested.flag）を監視して安全に停止可能。
    - 起動時にプロセス優先度を "high" に設定。
    - PID ファイル（data/execution.pid）出力をサポート。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視用 DB 初期化（init_monitoring_db）および DuckDB 接続を確立。
    - 停止フラグでループ終了。KeyboardInterrupt にも対応。
    - 起動時にプロセス優先度を "high" に設定。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する実装（監視データを本番 DB に蓄積する意図）。

- 環境 / 設定管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルートを .git または pyproject.toml で探索）。
    - .env/.env.local の読み込み順序と上書きルールを実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env の各行を堅牢にパース（export 形式、シングル/ダブルクォート、エスケープ、インラインコメントの扱い等に対応）。
    - Settings クラスで環境変数をラップして型・値チェックを提供（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
    - データベースパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）、監視閾値、フラグパス等のプロパティを提供。

  - config_setup.py
    - 対話式ウィザードで .env を生成/更新する CLI。
    - 各設定項目のラベル、説明、選択肢（KABUSYS_ENV 等）を定義し、既存 .env の読み込み・マスク表示・確認後保存を行う。
    - 保存テンプレートは Git にコミットしない旨の注記を含む。

  - validate_config.py
    - 起動前チェック CLI。
    - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在および（PyYAML が使える場合は）パース検証を実行。
    - `--strict` オプションで警告も失敗扱いにできる。
    - live 環境向けの追加ガード（LINE 通知設定の有無、KILL_FLAG_CLEAR_ON_START の設定確認など）。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 一貫したログ設定ユーティリティを提供（StreamHandler -> stdout、TimedRotatingFileHandler -> 日次ローテーション、30日保持）。
    - ログレベル・ログディレクトリの解決順を実装（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップし、コンソール出力のみで継続。
    - 既存ハンドラの二重設定防止のため、設定前に既存ハンドラを閉じて削除。

  - utils/process_priority.py
    - Windows と POSIX(Linux, macOS 等) の差分を吸収してプロセス優先度 (nice / HIGH_PRIORITY_CLASS 等) を設定。
    - CPU affinity セット関数を提供（最初の N コアに固定）。
    - アクセス権限不足や未対応 OS の場合は警告ログを出し安全にフォールバック。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 信号選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等金額配分へフォールバックして警告を出す。

  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有を元にセクター別エクスポージャを計算し、上限超過セクターの新規候補を除外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピングと未知レジームのフォールバック）。

  - portfolio/position_sizing.py
    - 発注株数算出 calc_position_sizes（allocation_method: risk_based/equal/score をサポート）。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap、cost_buffer（手数料/スリッページ見積り）を考慮したスケーリングロジックを実装。
    - TODO コメント: 将来は銘柄別 lot_size 等に対応予定。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）のログを集計してレポート出力。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。
    - 期日フィルタ（--from/--to）、DB パス上書き（--db）、環境変数 PAPER_TRADING_SQLITE_PATH 対応。
    - 基準値（稼働率99%、成功率90%等）を定義し PASS/FAIL 判定を出力。

- リサーチ / ファクター計算（部分実装）
  - research/factor_research.py
    - モメンタム、ボラティリティ、流動性、バリュー系の計算を想定するモジュール骨格を実装。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルを利用してファクターを計算する設計。
    - 一連の定数（21/63/126日等）、P95 算出や MA200 乖離の仕様が記載されているが、一部実装が途中（ファイル末尾の断片あり）。

- DB / DuckDB
  - DuckDB との接続点を各ランナーやリサーチで使用（duckdb.connect を使用）。
  - 監視用 DB 初期化（init_monitoring_db）が呼ばれる実装。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 既知の制約・注意点
- research/factor_research.py は一部実装が未完（ファイル末尾が途中で終わっている）ため、ファクター計算の完全実装は未着手箇所あり。
- position_sizing のコメントにあるように、銘柄ごとの lot_size や価格フォールバック（price が 0 の場合の扱い）に関する拡張は未実施。
- Monitoring は常に本番 sqlite_path を使用する実装になっている（テスト/開発用に分離したい場合は注意）。
- 一部の外部依存（psutil、duckdb、PyYAML 等）が環境に存在しない場合、フォールバックや警告はあるが一部機能が制限される可能性あり。
- .env 自動読み込みはプロジェクトルート検出に依存するため、配布後や特殊な配置では自動検出がスキップされることがある。

---

SemVer ポリシー: メジャー・マイナー・パッチの増分は以下を目安にします。
- MAJOR: 後方互換性を壊す変更
- MINOR: 新機能追加（後方互換性維持）
- PATCH: バグ修正・ドキュメント修正

（この CHANGELOG はコードの内容から推測して作成しています。実際のリリースノート作成時はコミットログやリリース管理情報を参照してください。）