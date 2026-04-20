# CHANGELOG

すべての注目すべき変更点をこのファイルに記録します。フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-04-20

初回リリース。KabuSys のコアユーティリティ、起動スクリプト、設定管理、ポートフォリオ構築・資金配分ロジック、検証ツールなどを実装しました。

### 追加 (Added)
- 全体
  - パッケージ初期バージョンを追加（__version__ = "0.1.0"）。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を検知してループを終了。
    - 例外発生時はログを出力して次ポーリングへ継続。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離。
    - 停止フラグでエンジン停止。実行 PID を data/execution.pid に管理。
    - Engine を別スレッドで実行し、停止フラグ検知で安全停止。
- 設定管理 / CLI
  - config.py: Settings クラスを実装。環境変数読み込み・検証を提供。
    - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 読み込み順は OS 環境 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パーサは export プレフィックス、クォート、エスケープ、インラインコメント（規則あり）に対応。
    - 各種設定プロパティ（DB パス、PAPER_FILL_MODE、閾値、KABUSYS_ENV 検証など）を実装。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 秘密値はマスク表示、既存 .env の読み込みと Enter での再利用に対応。
    - .env 書き込みテンプレートを提供（.env を誤ってコミットしない注意喚起付き）。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリチェック、config/*.yaml の存在・パースチェック（PyYAML があれば検証）。
    - --strict オプションで警告を FAIL 扱いにできる。
- ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - コンソールは stdout を使用。TimedRotatingFileHandler による日次ローテーション（30日分保持）。
    - ログディレクトリ作成失敗時にはファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX の差分を吸収し set_process_priority(level) を提供。
    - set_cpu_affinity(cpu_count) で最初の N コアへピンニング（未対応環境では安全にスキップ）。
    - 権限不足時は警告ログを出力して処理を継続。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算を追加（スコア全0 の場合はフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限に基づく候補除外ロジックを追加（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull/neutral/bear）を実装。未知レジームは警告を出して 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数算出を実装。
    - lot_size（単元株）丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap スケーリングを実装。
    - 価格欠損時にはログ出力して該当銘柄をスキップ。
- 解析・検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）などを算出。
    - 成否判定用の閾値を定義（例: 稼働率 >= 99%、P95 <= 200 ms 等）。
    - CLI オプション --from/--to/--db に対応。
- 研究モジュール（部分実装）
  - research/factor_research.py: ファクター計算モジュール（モメンタム等）を追加。DuckDB を用いて prices_daily / raw_financials を参照して計算する設計（実装一部省略あり）。

### 変更 (Changed)
- ロギング挙動
  - 共通の logging_setup を導入し、全起動スクリプトから呼び出すことでログ設定を統一。
  - コンソール出力は stderr ではなく stdout を使用して Task Scheduler / cron 等からのリダイレクト運用を想定。
- DB の取り扱い
  - run_monitoring は環境に関わらず production 相当の sqlite_path を使用する（監視データは本番 DB を参照する設計）。
  - run_execution は KABUSYS_ENV に応じて paper_trading 用 DB と本番 DB を切替える（本番/ペーパートレードの完全分離）。
- .env 自動読み込み
  - OS 環境変数を保護する仕組みを導入し、.env の上書き挙動を制御（.env.local は override=True で読み込むが OS 環境は保護）。

### 修正 (Fixed)
- 環境変数パースの堅牢化
  - _parse_env_line にてクォート内のエスケープシーケンスに対応し、export プレフィックスやコメント処理の仕様を明確化。
- モニタリングループの堅牢性強化
  - monitor.check_once() 内で発生する例外を捕捉してログ出力。次ポーリングで再試行する設計によりデーモンの不要な停止を防止。
- position_sizing のスケーリング
  - aggregate cap 超過時のスケールダウンと残余キャッシュを用いた lot_size 単位の再配分ロジックを実装し、安定した整数株数算出を実現。
- process_priority のクロスプラットフォーム対応
  - Windows と POSIX での優先度設定を分岐し、権限不足や未実装 API を適切にハンドリング。

### ドキュメント（コード内注釈・ヘルプ等）
- 各モジュールに詳細な docstring / コメントを追加。
  - 設計方針、使い方、引数・返り値、注意点（例: price 欠損時の挙動やレジーム乗数の意味）を明記。
  - CLI スクリプトに usage コメントとサンプルを追加。

### 注意事項 / 既知の制約 (Known issues / Notes)
- research/factor_research.py はモジュール実装の一部が途中（ファイル末尾で切れている）ため、完全なファクター計算は今後の実装が必要。
- apply_sector_cap: price_map に 0.0（欠損）を与えるとエクスポージャーが過少に見積もられる可能性があり、将来的にフォールバック価格（前日終値など）を導入する予定。
- 一部の機能（config/*.yaml のパース検証）は PyYAML がインストールされていることを前提に拡張的に動作する（未インストール時は検証をスキップして警告）。

---

今後のリリースでは以下を予定しています:
- factor_research の完全実装（すべてのファクター算出、標準化ユーティリティ連携）
- 実行エンジン・モニタリングの詳細ログ・メトリクス強化
- 単体テストの追加と CI 設定
- 銘柄別単元対応（lot_size の銘柄マッピング対応）

もし CHANGELOG に追記すべき変更点や修正履歴の表現に希望があればお知らせください。