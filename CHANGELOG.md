# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。日付・内容はコードベースから推測して作成しています。

全般的な注意
- このリリースはコードベースの初期公開相当（version 0.1.0）を想定してまとめています。
- 記載はソースから推定した機能追加・振る舞い・既知の制約やフォールバックを中心にしています。

Unreleased
- なし

0.1.0 - 2026-04-23
Added
- 基本アプリケーション構成
  - パッケージ初期化とバージョン定義（src/kabusys/__init__.py）。
- 実行用スクリプト
  - 監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検出で安全に終了。
    - 監視は環境に依らず本番用 sqlite_path を使用する挙動を明示。
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時に MockBrokerClient を利用し、paper_trading 用 DB に分離して動作（data/paper_trading.db、設定で上書き可）。
    - 停止フラグ／PID 管理（data/stop_requested.flag, data/execution.pid）のサポート。
    - エンジンは別スレッドで実行し、停止フラグ検知で安全停止。
- 設定管理・検証・ウィザード
  - 環境変数読み込み／Settings クラス（src/kabusys/config.py）。
    - .env/.env.local 自動ロード（OS 環境変数を保護して上書き制御）。
    - 複雑な .env 行のパース（export 形式、クォートとバックスラッシュエスケープ、インラインコメントの扱い）に対応。
    - 各種設定プロパティ（DB パス、KABUSYS_ENV、PAPER_FILL_MODE 等）を提供し、無効値時に例外を送出するバリデーションを実装。
  - 設定ウィザード CLI（src/kabusys/config_setup.py）。
    - 対話式で .env を作成・更新するウィザードを提供。
    - シークレット入力／デフォルト値／選択肢のサポート、.env の保存処理を実装。
  - 設定検証 CLI（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV・LOG_LEVEL 検証、DB パス存在チェック、config/*.yaml の存在および（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードを実装。
    - --strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築関連（純粋関数群）
  - 候補選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates（スコア降順、タイブレークロジック）、calc_equal_weights、calc_score_weights（全スコア 0 の場合は等分にフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap（既存保有を考慮したセクター上限フィルタ）。
    - calc_regime_multiplier（regime に応じた投下資金乗数、未知レジームはフォールバックして警告）。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）。
    - risk_based / equal / score の配分方式、単元（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer による保守的見積り、利用可能現金を超える場合の端数配分ロジックを実装。
- ユーティリティ
  - ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）。
    - StreamHandler を stdout に出力、TimedRotatingFileHandler による日次ローテーション（デフォルト 30 世代保持）、ログディレクトリ自動作成とフォールバック（作成失敗時はコンソールのみ）を実装。
  - プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収して nice 値や優先度を設定、CPU affinity 固定機能を提供。権限不足などに対しては警告でフォールバック。
- 検証ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）。
    - 指定期間の稼働率・注文成功率・送信率・API レイテンシ（平均／最大／P95）等を集計して PASS/FAIL 判定を行う。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
- 研究用モジュール（骨組み）
  - ファクター計算モジュール開始（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity の設計方針・定数を記載。DuckDB 接続を受けて prices_daily / raw_financials を参照する方針（途中まで実装あり）。

Changed
- ログ出力挙動
  - コンソールへのログは stdout に出力する方針に統一（cron 等でのリダイレクト運用を想定）（src/kabusys/utils/logging_setup.py）。
  - 既存ハンドラがある場合は一度クリアしてから再設定し、二重出力を防止。
- .env 自動読み込みの優先順位と保護
  - 自動ロードは OS 環境変数 > .env.local > .env の順で行い、既存の OS 環境変数は保護（override の挙動制御）（src/kabusys/config.py）。
- プロジェクトルート検出
  - .git または pyproject.toml を親ディレクトリから探索してプロジェクトルートを特定することで CWD に依存しない自動読み込みを実現（src/kabusys/config.py）。
- 実行開始時のプロセス優先度
  - run_monitoring/run_execution の起動流程で最初にプロセス優先度を "high" に設定するようにした（src/kabusys/run_monitoring.py, src/kabusys/run_execution.py）。

Fixed
- 環境変数の堅牢なパース
  - export 形式、クォート内のバックスラッシュエスケープ、インラインコメント処理などを考慮した .env 行パーサを実装し、誤解析を低減（src/kabusys/config.py）。
- フォールバックと安全なデフォルト
  - MONITOR_POLL_INTERVAL が不正値の場合に警告を出してデフォルト（60 秒）に戻す（src/kabusys/run_monitoring.py）。
  - PAPER_FILL_MODE の許容値チェックを追加し、不正値は ValueError を送出（src/kabusys/config.py）。
  - DB ハンドリングで init_monitoring_db を確実に呼ぶことで監視テーブルの存在を保証（冪等）（src/kabusys/monitoring/monitoring_db を利用する呼び出し）。
  - SQLite / DuckDB のクローズを finally ブロックで確実に行うようにした（run_monitoring/run_execution）。
  - 各種箇所で try/except を追加し、単一の不具合でプロセスが死なないように保護（例: monitor.check_once() の例外捕捉、SQL 実行の OperationalError ハンドリングなど）。
- ポジション計算での堅牢性
  - 価格情報が欠損した銘柄はスキップしてログでデバッグ出力（position_sizing, risk_adjustment）。
  - calc_score_weights が全部 0 の場合は等金額配分にフォールバックして警告を出す。

Security
- 重大なセキュリティ修正はなし。ただし .env は Git にコミットしない旨を README/ウィザードで注意喚起（src/kabusys/config_setup.py）。

Deprecated
- なし

Removed
- なし

Known issues / TODOs
- position_sizing の price が 0.0（欠損）時にエクスポージャーが過小見積りされる可能性があるため、将来的に前日終値や原価をフォールバック価格として使用する案がコメントで残されている（src/kabusys/portfolio/risk_adjustment.py）。
- research/factor_research.py は設計方針と定数が整備されているが、実装は途中（コメント末尾で切れている）。今後のファクター計算実装が必要（src/kabusys/research/factor_research.py）。
- 一部外部ライブラリ（PyYAML, psutil, duckdb）が必要。インストール状況によっては一部検証や機能がスキップされる（validate_config, process_priority, research 等）。

参考（主なファイル）
- 実行スクリプト: src/kabusys/run_monitoring.py, src/kabusys/run_execution.py
- 設定管理: src/kabusys/config.py, src/kabusys/config_setup.py, src/kabusys/validate_config.py
- ポートフォリオ: src/kabusys/portfolio/*.py
- ユーティリティ: src/kabusys/utils/logging_setup.py, src/kabusys/utils/process_priority.py
- ツール: src/kabusys/tools/paper_verification_report.py
- 研究: src/kabusys/research/factor_research.py

もし特定のファイルや変更点についてより詳細な注釈（例: 実装上の注意点、呼び出し順序の図、将来の改良案）をご希望でしたら指示してください。