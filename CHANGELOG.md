CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
------------

- 今後のリリースへ向けたタスク／TODO を追記する予定です（コード内にいくつか TODO コメントがあります）。
- research/factor_research.calc_momentum の実装が途中で終わっているため、完全なファクター計算は次版での対応を推奨します。

[0.1.0] - 2026-04-19
--------------------

初回公開リリース。日本株自動売買システム "KabuSys" の基盤となるモジュール群を追加。

Added
^^^^^

- 全体
  - パッケージ初期公開: バージョン 0.1.0 を追加。パッケージのメタ情報は src/kabusys/__init__.py に記載。

- 設定関連
  - .env 自動読み込み機構（src/kabusys/config.py）
    - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を自動読み込み。
    - export KEY=val 形式、シングル／ダブルクォート、インラインコメントの扱い、エスケープ対応など実用的なパーサを実装。
    - OS 環境変数を保護するオプション（上書き制御）をサポート。
    - Settings クラスを提供し、アプリケーション設定値をプロパティ経由で取得可能（DB パス、ログレベル、環境判定、Paper Trading 関連等）。
    - 環境変数未設定時は明示的なエラーを出す _require() を用意。

  - 環境設定ウィザード CLI（src/kabusys/config_setup.py）
    - 対話式に .env を生成・更新するウィザードを提供。
    - デフォルト値、選択肢、シークレット入力・マスク表示、既存 .env の再利用に対応。
    - .env の書式生成と保存処理を実装。

  - 設定検証ツール（src/kabusys/validate_config.py）
    - 起動前に .env および config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パスの親ディレクトリ確認、YAML パース（PyYAML があれば）を実行。
    - --strict オプションで警告を失敗扱いにするモードを実装。

- ランナー / デーモン系
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - ExecutionEngine の起動フローを実装。プロセス優先度設定、DB 接続、BrokerClientFactory によるブローカクライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler といった依存コンポーネントの組み立て、スレッドでの engine.run_session 実行、停止フラグ検知による安全停止、PID ファイル管理を提供。
    - Paper Trading 環境 (KABUSYS_ENV=paper_trading) の場合、専用 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
    - 起動前に停止フラグが立っている場合は起動を回避。

  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor をポーリングで定期実行するランナーを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視データは本番監視用 DB に集約）。
    - stop_requested.flag による終了検知をサポート。

- ロギング・プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - コンソール出力（stdout）と日次ローテーションファイル出力（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL / 引数での上書きに対応。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラの二重設定防止（既存ハンドラをクリア）を実装。

  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity（最初の N コアに固定）を設定する set_cpu_affinity を提供。
    - 権限不足や未対応 OS に対しては警告を出して安全にスキップ。

- ポートフォリオ構築（pure functions）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates、calc_equal_weights、calc_score_weights を提供。スコア全てが 0.0 の場合は等金額配分にフォールバック。

  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター毎の既存エクスポージャが閾値を超える場合に新規候補を除外するロジック。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を返す（bull/neutral/bear）。

  - 株数計算・リスク制約・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注株数計算、lot_size（単元）での丸め、aggregate cap（利用可能現金に合わせたスケールダウン）、cost_buffer（手数料・スリッページ推定）の考慮を実装。
    - risk_based の場合は stop_loss_pct / risk_pct を用いたポジションサイズ計算を実装。

  - モジュールエクスポート（src/kabusys/portfolio/__init__.py）
    - 主要関数をパッケージ公開。

- ツール
  - Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading 用 SQLite からシステム稼働率、注文成功率、送信率、レイテンシ（平均 / 最大 / P95）などを集計し、PASS/FAIL 判定を出力する CLI。
    - 閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し、期間指定 (--from/--to) に対応。
    - DB が存在しない場合やテーブルが不足している場合に graceful にハンドリングして N/A を出力。

- 調査用ファクター計算基盤（src/kabusys/research/factor_research.py）
  - ファクター計算用モジュールを追加（Momentum / Value / Volatility / Liquidity を想定）。
  - DuckDB 接続を受けて prices_daily / raw_financials から計算する方針で実装開始。
  - calc_momentum の枠組みを追加（注: 実装途中のため次版で補完予定）。

Changed
^^^^^^^

- 初回リリースのため該当なし。

Fixed
^^^^^

- 初回リリースのため該当なし。コード内で細かなフォールバック・エラーハンドリング（例: .env 読み込み失敗時の警告、ログディレクトリ作成失敗時のフォールバック、プロセス優先度設定失敗時の警告）を充実させて実運用での堅牢性を向上。

Known Issues / Notes
^^^^^^^^^^^^^^^^^^^^^

- research/factor_research.calc_momentum の実装は途中で終了している箇所（ファイル末尾に未完の変数 start_da 等）があります。ファクター計算を本番で利用する場合は該当メソッドの完成が必要です。
- position_sizing や risk_adjustment 内に将来の拡張やフォールバック（例: price が欠損時のフォールバック価格取得）に関する TODO コメントが残っています。実運用時にはこれらを検討してください。
- run_monitoring は「監視は環境にかかわらず本番 sqlite_path を使用する」設計となっているため、開発環境で監視データを分離したい場合は設定やコードの変更が必要です。
- .env パーサは多くのケースに対応していますが、極端な複雑な quote/escape のケースは想定外である可能性があります。重要なシークレット値は保存・運用ポリシーを検討してください。

Security
^^^^^^^^

- .env は絶対にリポジトリへコミットしないよう生成スクリプトや README 等で周知することを推奨します（config_setup.py のヘッダにも記載済み）。

Acknowledgements
^^^^^^^^^^^^^^^^

- 初回リリースに向けた基盤実装。以降はテストカバレッジの追加、Factor 実装の完成、運用ドキュメントの拡充を予定しています。

----- 

（この CHANGELOG はコードから推測して作成しています。実際の変更履歴やコミットメッセージに基づく詳細は git の履歴を参照してください。）