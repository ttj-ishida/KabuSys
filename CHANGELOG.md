# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
日付はこのリリースを生成した日付です。

## [0.1.0] - 2026-04-18

### 追加
- 基本的なアプリケーション構成・起動スクリプトを追加
  - src/kabusys/__init__.py にパッケージ情報（__version__ = "0.1.0"）を追加。
  - 実行系・監視系のエントリポイントを追加：
    - src/kabusys/run_execution.py
      - ExecutionEngine を起動する CLI スクリプト。
      - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite DB を使用（data/paper_trading.db がデフォルト）。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の起動・停止監視（stop flag による制御）を実装。
      - デーモンスレッドでエンジンを実行し、停止フラグ検知で安全停止を行う。
    - src/kabusys/run_monitoring.py
      - SystemMonitor ポーリングループの起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境に関わらず本番用の sqlite_path を使用して監視テーブルを初期化。
      - 停止フラグ検出・例外ハンドリング・リソースクローズ処理を実装。
- 設定管理・自動 .env 読み込み
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml 基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - 複雑な .env パーサ（export プレフィックス、クォート・エスケープ、インラインコメント処理）を実装。
    - Settings クラスで各種環境設定をプロパティとして提供（J-Quants / kabu API / DB パス / 監視閾値 / env 判別等）。
    - PAPER_FILL_MODE のバリデーション、有効値制限を実装。
- 設定ウィザード・検証ツール
  - src/kabusys/config_setup.py
    - 対話式で .env を作成・更新するウィザードを実装。初期値表示、シークレットマスク、選択肢チェック、保存確認などの操作を提供。
  - src/kabusys/validate_config.py
    - 起動前に環境変数や config/*.yaml の存在・整合性を検証する CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、PyYAML がない場合のスキップ／警告、KABUSYS_ENV=live 時の追加ガードを実装。
    - --strict を指定すると警告も失敗（exit 1）として扱うオプションを提供。
- ロギング・プロセス制御ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - ルートロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定するユーティリティを追加。
    - ログディレクトリの自動作成、失敗時のフォールバック（コンソールのみ）をサポート。ログレベル解決ロジックを実装。
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定（high/normal/low）と CPU affinity 設定関数を提供。権限不足や未対応環境では警告を出してスキップする安全設計。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナルの選定（select_candidates）、等重配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等重にフォールバックして警告を出す。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有の時価に基づくセクター露出計算、上限超過セクターの除外）。unknown セクターは上限適用外。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear→1.0/0.7/0.3、未知は警告のうえ 1.0 フォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく株数算出ロジックを実装。
    - risk_based: 許容リスク率（risk_pct）と損切り率（stop_loss_pct）からベース株数算出。
    - equal/score: ウェイトと portfolio_value に基づき各銘柄の割当を計算。
    - 単元（lot_size）丸め、1 銘柄上限（max_position_pct）、投下資金上限（max_utilization）、手数料/スリッページ見積り（cost_buffer）を考慮した aggregate cap のスケーリング処理、余りの再配分ロジックを実装。
  - src/kabusys/portfolio/__init__.py で主要関数をエクスポート。
- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB（デフォルト: data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95））を集計し、基準値に基づき PASS/FAIL を判定するレポート生成スクリプトを追加。
    - P95 算出ユーティリティ、日付フィルタ化、データ欠損時の安全ハンドリングを実装。判定閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）を定義。
- 研究用ファクタ計算（着手）
  - src/kabusys/research/factor_research.py
    - モメンタム / Value / Volatility / Liquidity などのファクター計算の設計と calc_momentum の実装開始（DuckDB 接続を受け prices_daily / raw_financials を参照する方針、各種期間定数を定義）。※ ファイルは途中で切れており、以降の実装は継続予定。

### 変更（設計的決定）
- DB の取り扱い
  - 監視コンポーネントは実行環境にかかわらず本番 sqlite_path を使用する設計（監視データは本番 DB に集約する想定）。
  - ExecutionEngine は paper_trading モード時に paper_sqlite_path を使用して本番 DB と完全分離するよう実装。
- サービス起動時の優先度設定
  - run_execution と run_monitoring の起動処理で最初に set_process_priority("high") を呼び出すポリシーを採用（重要プロセスの優先度を上げるため）。
- ロギング出力先のポリシー
  - stdout を StreamHandler に使い、ファイル出力はログディレクトリ作成が成功した場合にのみ有効化する冗長性を導入。

### 修正（注意喚起 / 安全策）
- 設定/運用安全性
  - validate_config にて KABUSYS_ENV=live の場合は複数の注意喚起（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START=1 の危険性）を出力するようにし、本番での誤設定を検出しやすくした。
  - .env の自動読み込みは明示的に無効化できる（KABUSYS_DISABLE_AUTO_ENV_LOAD）ので、テスト環境等で OS 環境変数を壊さない設定が可能。
- 例外・権限不許可時のフォールバックを強化
  - process_priority / cpu_affinity / logging file handler の作成において、権限不足や未サポート環境では警告を出して処理をスキップする堅牢な設計。

### 既知の問題・WIP
- src/kabusys/research/factor_research.py の calc_momentum 実装が途中で終わっている（ファイル末尾が途切れている）。ファクター計算の完全実装は引き続き作業中。
- 一部の TODO コメント（例: position_sizing の lot_size を銘柄別に拡張する等）が残っているため、将来的な改善余地あり。

### セキュリティ
- 機密情報（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、LINE_CHANNEL_ACCESS_TOKEN 等）は .env に保存する設計だが、config_setup の出力では明示的に "絶対に Git にコミットしないこと" を注意書きしている。

---

今後の予定（非公式）
- factor_research の完全実装（ファクター計算と正規化）
- ExecutionEngine / RiskManager 周りの統合テストとモック化の整備
- ログ・メトリクスのさらなる強化（Prometheus / structured logging 等）
- position_sizing の銘柄別単元対応と手数料モデルの拡張

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴や変更履歴と差異がある可能性があります。）