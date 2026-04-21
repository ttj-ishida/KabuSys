# Changelog

すべての注目すべき変更点をこのファイルに記録します。
このプロジェクトは Keep a Changelog の慣習に従います。
安定性の向上と互換性に関する情報は各リリースの節をご参照ください。

注: 日付はリポジトリのコード内容（例: ドキュメント内の日付）および現在の開発状況から推測して付与しています。

## [0.1.0] - 2026-04-21
初回公開リリース。自動売買システムのコアユーティリティ、実行エンジン起動スクリプト、監視、設定関連ツール、ポートフォリオ構築ロジック、ペーパートレード検証ツールなどを含みます。

### 追加 (Added)
- 実行（Execution）関連
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を用いて実行時に適切なブローカクライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler 等の主要コンポーネントを組み立て、ExecutionEngine をスレッドで起動。
    - 停止フラグ（data/stop_requested.flag）検知時には安全に停止処理を行う。
    - 実行中の PID を data/execution.pid に保存するための pid_file の取り扱いをサポート。

- 監視（Monitoring）関連
  - run_monitoring.py: SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバック）。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番用の sqlite_path を使用する設計（監視データは本番 DB に記録）。
    - DATA ディレクトリ内の停止フラグを検知するとループを終了。
    - プロセス優先度を起動時に "high" に設定。

- 設定管理・検証
  - config.py: 環境変数読み込みと Settings クラスを実装。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動ロード（OS 環境変数を上書きしない保護機能あり）。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 各種設定プロパティ（J-Quants、kabu API、データベースパス、監視閾値、環境判定など）を提供。PAPER_FILL_MODE の検証などバリデーションを含む。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB ファイル親ディレクトリの存在チェック、config/*.yaml の存在・パース検証（PyYAML 未導入時は警告）、本番環境向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
    - --strict オプションで警告を失敗扱いにできる。
  - config_setup.py: 対話式の .env 作成/更新ウィザードを追加。
    - 秘匿項目はマスク表示、既存 .env の読み込み・再利用、.env の書き出しフォーマットを実装。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。
    - ログレベル・ログディレクトリの解決順と例外処理（ディレクトリ作成失敗時はファイルハンドラをスキップ）を実装。
  - utils/process_priority.py: プロセス優先度・CPU Affinity 設定ユーティリティを追加。
    - Windows/Linux/macOS を抽象化し、nice/priority の設定、CPU affinity 固定機能を提供。アクセス権限不足等は警告でスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: シグナルをスコア降順にソートして上位 N 件を選定。
    - calc_equal_weights / calc_score_weights: 等分配とスコア加重を実装（スコア合計が 0 の場合は等配分にフォールバックし警告）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクターごとの上限比率チェック（既存保有の影響を考慮）に基づく候補除外ロジック。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を計算。
  - portfolio/position_sizing.py:
    - calc_position_sizes: リスクベース／等配分／スコア配分に対応した株数計算。単元株（lot_size）で丸め、ポートフォリオ単銘柄上限・投下資金上限を考慮。aggregate cap 超過時のスケーリングと残差処理を実装。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py:
    - ペーパートレード SQLite DB（デフォルト: data/paper_trading.db）からシステム稼働率、注文成功率、送信率、レイテンシ統計（平均/最大/P95）およびリスク却下数を集計し、人間向けの検証レポートを出力。
    - PASS/FAIL 判定基準を定義（稼働率・成功率・送信率・P95 レイテンシ等）。
    - --from/--to/--db オプションをサポート。

- 研究モジュール（部分実装）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加（モメンタム、MA200、ATR、流動性などの算出を想定）。モジュール設計方針・定数を定義。関数の一部は続き（未表示）で実装予定。

### 変更 (Changed)
- 監視周りの設計上の明示
  - run_monitoring.py は環境変数にかかわらず監視用 DB として Settings.sqlite_path（本番設定）を使用するようにしており、監視データは本番側に記録される旨を明示的に実装。

### 修正 (Fixed)
- .env パースの堅牢化
  - config._parse_env_line: export プレフィックス、クォート文字列内のバックスラッシュエスケープ処理、インラインコメントの扱いを考慮したパーサを実装。コメントの誤認を減らすため、非クォート時の '#' の処理は直前がスペース/タブの場合のみコメントとみなすように設計。

- ロギング設定における二重ハンドラ防止
  - setup_logging() は既存ハンドラを flush/close してから削除して再設定するため、複数回呼び出してもハンドラが二重に追加されないように対処。

### 注意事項 (Notes)
- 自動 .env ロード
  - デフォルトでプロジェクトルートの .env/.env.local を自動読み込みします。ただし OS 環境変数は保護され、.env.local の override は OS 環境変数を上書きしない設計です。自動読み込みを無効化したい場面（テスト等）は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番ガード
  - validate_config.py は KABUSYS_ENV=live の際に追加の警告を出します（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の設定など）。
- 単元株・価格欠測
  - position_sizing.calc_position_sizes や risk_adjustment.apply_sector_cap では価格データの欠測時にスキップする挙動があります。将来的に前日終値等のフォールバック実装を検討する旨の TODO コメントあり。
- 未完の実装
  - research/factor_research.py はモジュール方針と一部実装を含むが、ファクター計算関数の完全実装が続きとして存在する可能性があります（提供されたコードは途中で切れています）。

### セキュリティ (Security)
- シークレット値の扱い
  - config_setup のウィザードではシークレット項目（例: J-Quants トークン、kabu API パスワード）をマスク表示しますが、.env ファイル自体は平文で保存されるため、.env をバージョン管理に含めないことを強く推奨します（生成ヘッダにも注意喚起あり）。

---

今後のリリースでは以下を予定／検討:
- research/factor_research の完全実装とテストカバレッジ追加
- 価格欠測時のフォールバック戦略（前日終値等）の導入
- ロギングおよび監視イベントのメトリクス詳細化（Prometheus 等への出力）
- 実行エンジンと監視コンポーネントの統合テスト強化

もし CHANGELOG に追記してほしい点（例: リリース日、追加の変更点や修正箇所）があれば教えてください。コードの差分に基づいて内容を調整して追記します。