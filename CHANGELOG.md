CHANGELOG
=========
すべての重要な変更は Keep a Changelog の形式に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（現在の作業ツリーがリリース済みバージョンに対応していない場合に記載します。今回は初回リリース相当の内容を 0.1.0 として記載しています。）

0.1.0 - 2026-04-23
------------------

Added
- 初期リリース: KabuSys 自動売買フレームワークのコア機能を追加。
  - 起動スクリプト/サービス
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
      - 停止制御はプロジェクト直下の data/stop_requested.flag を参照。  
      - 監視は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用する設計。  
      - エラー時はログを残して次のポーリングまで待機、KeyboardInterrupt による停止をハンドル。
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
      - KABUSYS_ENV=paper_trading の場合は専用 MockBroker を用い data/paper_trading.db に記録し、本番 DB と分離。  
      - 起動前後に PID / stop flag を用いたプロセス制御を実装。スレッドで engine.run_session を実行し、停止フラグ検知で安全停止。  
      - RiskManager, OrderManager, Reconciler など主要コンポーネントを組み立てて起動するテンプレートを提供。
  - 設定・環境管理
    - config.py: .env 自動ロードと Settings クラスを実装。  
      - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を自動読み込み（必要に応じて無効化可能）。  
      - .env パースは export 形式、クォート、インラインコメント等に対応。OS 環境変数は保護され、.env.local で上書き可能。  
      - Settings に各種プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、PAPER_FILL_MODE、KABUSYS_ENV、ログレベル等）。環境変数の検証ロジックを備える。
    - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。秘密項目はマスク表示、既存値の再利用、保存前の確認を行う。
    - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数や KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリ、config/*.yaml の存在・パースチェック（PyYAML が無ければスキップ）などを報告。--strict オプションで警告も失敗扱いにできる。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py: シグナル選定（スコア降順）・重み算出（等分配／スコア加重）を実装。スコア全てが 0 の場合は等配にフォールバックして警告を出す。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。unknown セクターの取扱いやレジームフォールバックについて記載あり。
    - portfolio/position_sizing.py: 株数算出ロジックを実装（risk_based / equal / score の allocation_method）。単元株丸め、1 銘柄上限、aggregate cap のスケーリング、cost_buffer（手数料・スリッページ想定）対応などを含む。
    - portfolio/__init__.py: 上記関数群をエクスポート。
  - ユーティリティ
    - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。  
      - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション・30 日保持）をルートロガーに設定。  
      - 既存ハンドラの二重登録を防ぐため一度クリーンアップして再設定。LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - utils/process_priority.py: psutil を用いたクロスプラットフォームなプロセス優先度 / CPU affinity 設定ユーティリティを追加。Windows と POSIX（Linux/Mac/FreeBSD）を考慮した実装で、権限や未対応環境では警告を出してスキップする。
  - ツール
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。  
      - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等を計算して PASS/FAIL を判定する閾値を設定（例: 稼働率 >= 99% 等）。  
      - --from/--to/--db オプション、環境変数 PAPER_TRADING_SQLITE_PATH に対応。DB が存在しない場合はメッセージを出力。
  - 研究用モジュール（開発途上）
    - research/factor_research.py: DuckDB を用いたファクター計算（モメンタム、MA200、ATR、出来高等）を開始。関数のインターフェースと計算方針（スキャン幅、日数定数など）を定義（実装途中）。
  - パッケージ情報
    - __init__.py にてパッケージバージョンを 0.1.0 として定義。

Changed
- （初回リリースのため該当なし）

Fixed
- ロギング初期化での二重ハンドラ登録やログディレクトリ作成失敗時の挙動を改善（logging_setup.py）。
- .env パーサーの改善（export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱い等）により、より現実的な .env 内容を安全に読み込み可能に（config.py）。

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- .env は絶対にリポジトリに含めない旨を config_setup.py の出力ヘッダで明示し、シークレットはウィザードでマスク表示することで誤コミット・表示リスクを軽減。

Internal / Implementation notes
- DB 分離: paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番用 monitoring.db とデータを分離する設計。監視プロセス(system monitor)はあえて環境に依存せず本番 sqlite_path を参照する点に注意。
- 停止制御: run_* スクリプト両方で data/stop_requested.flag を使った外部停止フラグに対応。run_execution は PID ファイルの扱いを想定（data/execution.pid）。
- エラー耐性: ポーリングループやエンジンスレッドループで例外を捕捉してログに記録し、できる限り安定して継続する設計（監視ループは例外を握りつぶさずログ出力して次回に復帰）。
- 依存ライブラリ: duckdb, psutil を利用。YAML 検証は PyYAML に依存（未インストール時は警告を出してスキップ）。

補足
- この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートに合わせて日付や詳細（既知の制約、既知のバグ、互換性注意点等）を適宜更新してください。