CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

現在のバージョン: 0.1.0 (初回リリース)
リリース日: 2026-04-24

Unreleased
----------

（なし）

0.1.0 - 2026-04-24
-----------------

Added
- 全体
  - 初回リリース。KabuSys 基本コンポーネント群を追加。
  - パッケージバージョンを __version__ = "0.1.0" に設定。

- 実行ランナー / 監視
  - run_execution.py：ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite (デフォルト data/paper_trading.db) を使用し、本番 DB と分離。
    - BrokerClientFactory を通じてブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで実行。
    - エンジン停止用の stop フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) をサポート。
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様を明示。

- 設定・環境管理
  - config.py：環境変数読み込みと Settings クラスを追加。
    - プロジェクトルート検出（.git または pyproject.toml）に基づいて .env 自動ロードを実行（必要であれば無効化可能）。
    - .env ファイルのパースは export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、inline コメント等に対応。
    - 設定用プロパティ（DB パス、ログレベル、KABUSYS_ENV 判定、paper_trading 関連設定等）を提供。
  - config_setup.py：対話式 .env 生成/更新ウィザードを追加。
    - シークレット値のマスク表示、デフォルト/選択肢サポート、保存前の確認プロンプトを実装。
  - validate_config.py：設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス／config/*.yaml 存在チェック、live 環境向けガード（LINE 通知や Kill Switch クリアの警告）を実装。
    - --strict モードで警告を FAIL 扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py：統一ロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler、30日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の環境変数または引数で柔軟に設定可能。ログディレクトリ作成失敗時はファイル出力をスキップして継続する安全設計。
  - utils/process_priority.py：プロセス優先度および CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX (Linux/Mac/FreeBSD) を吸収する実装、優先度レベル ("high"/"normal"/"low") をサポート。権限不足や未対応 OS の場合は警告を出してスキップ。
    - set_cpu_affinity() により先頭 N コア固定を簡易的に指定可能。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を抽出。
    - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分を実装（全スコア 0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェックで新規候補を除外するロジック。
    - calc_regime_multiplier: market レジームに応じた資金乗数（bull/neutral/bear）を返す。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based"/"equal"/"score"）に基づき発注株数を計算。単元株（lot_size）丸め、1 銘柄上限・aggregate cap、スケーリングロジック、cost_buffer を考慮。

- リサーチ / ファクター計算
  - research/factor_research.py（部分実装）
    - モメンタム・MA200乖離・ATR・流動性等の計算方針を定義。DuckDB 接続を受け prices_daily / raw_financials を参照して結果を返す設計（関数シグネチャ・定数群を含む）。

- ツール
  - tools/paper_verification_report.py：Paper Trading 検証レポート生成スクリプトを追加。
    - 指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシなどを集計。
    - 閾値（稼働率 >=99%、成立率 >=90% 等）に基づく PASS/FAIL 判定を出力。
    - --from / --to / --db オプションで期間・DB を指定可能。
  - tools/__init__.py を追加（パッケージ化）。

Changed
- DB 周りの初期化
  - 監視機能起動時に monitoring DB テーブルを確実に作成するため init_monitoring_db() を呼び出す処理を追加。冪等に動作するよう設計。

- Logging / output
  - ログは標準では stdout に出力され、ファイル出力は logs/<app>.log に日次ローテーションで保存する。ログディレクトリ作成に失敗してもアプリが停止しないように変更。

Fixed
- .env パーサーの堅牢化
  - export プレフィックス、引用符で囲まれた値（バックスラッシュエスケープ含む）、およびインラインコメント処理を正しく扱うよう改善。
  - _load_env_file() において OS 環境変数を保護する protected 引数を導入し、意図せぬ上書きを防止。

- run_monitoring のポーリング間隔取り扱い
  - MONITOR_POLL_INTERVAL が不正な値（数値でない、0 以下など）の場合に警告を出しデフォルト(60s)にフォールバックするように修正。time.sleep に渡して ValueError になるのを防止。

- process_priority の安全性向上
  - 権限不足や未実装 API 呼び出し時には警告ログを出し操作をスキップすることでクラッシュを防止。

- Paper Trading の DB 分離
  - paper_trading モードでは paper_sqlite_path を使用することで本番データとの完全分離を保証。

- Paper 検証レポート
  - レイテンシの P95 を計算するユーティリティ _p95 を追加し、欠損データに対する安全な処理を実装。

Security
- 環境変数の取り扱いでシークレット値を対話式ウィザード・表示においてマスクするようにし、.env ファイルの Git コミットを明示的に禁止するヘッダコメントを追加。

Removed
- （なし）

Notes / Breaking changes / 注意事項
- 監視起動スクリプト (run_monitoring.py) は「環境にかかわらず」Settings.sqlite_path（デフォルト data/monitoring.db）を使用する仕様です。開発環境で別 DB を使いたい場合は sqlite_path の環境変数を明示的に設定してください。
- KABUSYS_DISABLE_AUTO_ENV_LOAD を設定しない限り、プロジェクトルートが特定できた場合は .env 自動ロードが行われます。CI やテストで自動ロードを抑止したい場合はこの環境変数で無効化してください。
- process_priority の設定は OS / 権限に依存します。権限が不足する環境では無視されます（警告ログのみ）。
- research/factor_research.py は設計・定数を含むが実装の一部が未完（ファイル末尾で中断）。今後のリリースで計算ロジックの完成を予定。

開発者向けメモ
- config/*.yaml の内容検証は PyYAML に依存します。validate_config は PyYAML 非インストール時に YAML の検証をスキップして警告を出します。
- ログレベル・ログ出力先は環境変数 LOG_LEVEL / LOG_DIR または setup_logging の引数で制御できます。

今後の予定（例）
- research モジュールのファクター計算実装完了
- ExecutionEngine / SystemMonitor の詳細な単体テスト・統合テスト整備
- ブローカークライアントのモック拡張とペーパートレードの挙動検証ツール強化

ライセンス、貢献方法等はリポジトリの README を参照してください。