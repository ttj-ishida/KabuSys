# CHANGELOG

すべての変更は Keep a Changelog のガイドラインに準拠して記載しています。  
（注: 以下の内容は提示されたコードベースの実装内容から推測してまとめた変更履歴です。）

## [Unreleased]
- なし

## [0.1.0] - 2026-04-19
初期リリース。システムの起動スクリプト、設定管理、検証・ウィザード、ポートフォリオ構築ユーティリティ、実行エンジン及び監視周りのユーティリティ群、ツール類を含む基本実装を追加。

### 追加
- 全体
  - パッケージ初期バージョン `0.1.0` を追加（src/kabusys/__init__.py）。
  - 主要サブパッケージのエクスポートを定義（data, strategy, execution, monitoring）。

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を "high" に設定して起動。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを作成（Mock の利用を想定）。
    - ExecutionEngine を別スレッドで実行、外部停止フラグ（data/stop_requested.flag）に対応して安全に停止。
    - PID ファイルの取り扱いと DB 初期化（監視用テーブルの冪等初期化）を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず監視用（本番） sqlite_path を使用する設計。
    - 停止フラグ検知・例外保護・KeyboardInterrupt への対応を実装。

- 設定・環境変数管理
  - config.py: 環境変数/設定管理を追加。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）。
    - .env ファイルの自動読み込み（.env, .env.local）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - export 形式やクォート・エスケープ・インラインコメント等に対応する .env パーサ実装。
    - 各種設定プロパティ（J-Quants、kabu API、DB パス、paper_trading 用設定、監視閾値、環境判定メソッド等）を提供。
    - PAPER_FILL_MODE の検証（許容値: instant/partial/never/reject）。
    - 環境指定（KABUSYS_ENV）が制約（development/paper_trading/live）に従うことを検証。

  - config_setup.py: .env 作成/更新用の対話式ウィザードを追加。
    - 各設定項目の説明・デフォルト・シークレット入力に対応。
    - 既存 .env の読み込みと差分入力、保存時にテンプレート形式で書き出し。
    - 書き込み前の確認プロンプトを実装。

  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認。
    - config/*.yaml ファイルの存在確認と（PyYAML があれば）パースチェック。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や Kill Switch の設定確認）。
    - --strict モードで警告を失敗扱いにできる。

- ログ・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - コンソール出力は stdout を使用。
    - 日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を追加、デフォルト logs/ を作成。
    - 既存ハンドラのクリア処理やログレベル解決ロジック（引数 > 環境変数 > デフォルト）を実装。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。

  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX 系の差異を吸収（psutil を使用）。
    - set_process_priority(level) で high/normal/low を設定。失敗時は警告にフォールバック。
    - set_cpu_affinity(cpu_count) で最初の N コアにプロセスを固定。未対応環境では安全にスキップ。

- ポートフォリオ構築モジュール（純粋関数）
  - portfolio/portfolio_builder.py:
    - 候補選定 select_candidates（スコア降順、同点は signal_rank でタイブレーク）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコアが 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py:
    - セクター集中制限 apply_sector_cap（既存ポジションのセクター比を計算して新規候補を除外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマッピング、未知のレジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - position sizes 計算 calc_position_sizes。
    - allocation_method による分岐（risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap のスケールダウンロジックを実装。
    - cost_buffer を用いた保守的なコスト見積と残差処理（残余キャッシュで lot 単位の再配分）。

- 実行/監視用 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db が run_execution/run_monitoring から呼び出され、監視用テーブルの存在を保証（冪等）。

- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - SQLite（paper_trading.db デフォルト）を参照してシステム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数を計算。
    - しきい値（稼働率 99%、注文成功率 90%、送信率 95%、P95 200ms）に基づく PASS/FAIL 判定を実装。
    - 日付フィルタ（--from / --to）をサポート、P95 計算の実装を含む。
  - tools パッケージの初期化ファイルを追加。

- 研究用モジュール（初期実装）
  - research/factor_research.py: DuckDB を利用したファクター計算モジュールの骨格を追加（モメンタム・移動平均・ATR 等の定数と関数設計方針を記載）。一部実装が続くことを示す（作業途中のファイル断片あり）。

### 変更
- なし（初回リリースのため既存コードからの差分なし）

### 修正
- なし（初回リリースのため既存バグ修正履歴なし）

### 既知の注意点 / TODO（コード中の注釈より）
- portfolio.risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャーが過少評価される可能性があるため、将来的には前日終値や取得原価等のフォールバック価格を検討する旨の TODO がある。
- position_sizing:
  - 将来的に銘柄別の lot_size を導入するための拡張予定をコメントで示している。
- research/factor_research.py:
  - ファイル末尾に "start_da" のような未完のトークンがあるため、ファクター計算の実装が未完であることが示唆される（作業継続が必要）。

### セキュリティ
- シークレット値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は .env に保存する設計。ただし .env を Git にコミットしないよう README/コメントで明示している。

---

今後のリリースでは、research モジュールの完成、テストの追加、エラーハンドリング強化、ドキュメント（API 参考・運用手順）の整備などを想定しています。必要であればこの CHANGELOG をベースに英語版や GitHub Release 用の短縮版も作成します。