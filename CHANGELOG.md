# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
リリース日: 2026-04-18

## [0.1.0] - 2026-04-18

### 追加
- 基本パッケージ初期実装を追加
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"` を設定。
- 実行エントリスクリプト
  - run_monitoring: `SystemMonitor` のポーリングループ起動用スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60秒）。
    - 停止フラグファイル（data/stop_requested.flag）を検出して安全にループを終了。
    - Monitoring は環境にかかわらず本番の `sqlite_path` を使用して接続。
  - run_execution: `ExecutionEngine` 起動用スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は専用の Paper Trading DB（data/paper_trading.db）を使用し、Mock ブローカーで完全に分離。
    - 停止フラグと PID ファイルを用いた起動/停止制御を実装。
    - 起動時にプロセス優先度を "high" に設定（`set_process_priority` を呼び出す）。
- 設定管理
  - `kabusys.config.Settings` を実装。
    - `.env` の自動ロード（プロジェクトルート判定: .git または pyproject.toml を探索）。
    - 多数のプロパティを提供（J-Quants / kabu API / DB パス / ペーパートレード設定 / 監視閾値 / 環境判定など）。
    - `paper_fill_mode` のバリデーション（"instant" | "partial" | "never" | "reject"）。
    - `paper_sqlite_path`（Paper Trading 専用 DB パス）。
- 環境設定ユーティリティ
  - `config_setup`：対話式ウィザードで .env を生成・更新する CLI を追加。
    - シークレット入力のマスク表示、既存 .env の読み込みと再利用、保存確認を実装。
- 設定検証
  - `validate_config` CLI を追加。以下を検証:
    - 必須環境変数の有無とプレースホルダチェック
    - `KABUSYS_ENV` / `LOG_LEVEL` の妥当性
    - DB パスの親ディレクトリ存在確認
    - `config/*.yaml` の存在チェック（PyYAML が無ければスキップ）と簡易パース検証
    - `KABUSYS_ENV=live` 時の追加ガード（LINE 設定、KILL_FLAG_CLEAR_ON_START の警告）
    - `--strict` オプションで警告を FAIL 扱いにできる
- ログ設定ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加。
    - ルートロガーに stdout 出力用 StreamHandler と日次ローテートの TimedRotatingFileHandler を設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - ログレベルの解決順序とログディレクトリの解決順序をサポート。
- プロセス制御ユーティリティ
  - `kabusys.utils.process_priority` を追加。
    - Windows と POSIX (Linux/Mac/FreeBSD) を吸収してプロセス優先度（high/normal/low）の設定を提供。
    - CPU アフィニティ設定関数 `set_cpu_affinity` を実装（利用可能コア数チェック、権限エラーをハンドル）。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。
- ポートフォリオ構築モジュール
  - `kabusys.portfolio` を追加（純粋関数群）。
    - portfolio_builder:
      - 候補選定 `select_candidates`（スコア降順、同点は signal_rank を用いる）。
      - 等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights`（総スコアが 0 の場合は等分にフォールバック）。
    - risk_adjustment:
      - セクター集中制限 `apply_sector_cap`（既存保有のセクター比率が閾値を超える場合に新規候補を除外）。
      - レジーム乗数 `calc_regime_multiplier`（"bull"/"neutral"/"bear" に基づく乗数、未知のレジームは 1.0 でフォールバック）。
    - position_sizing:
      - 発注株数算出 `calc_position_sizes`（allocation_method: "risk_based" / "equal" / "score" をサポート）。
      - 単元株（lot）丸め、per-stock 上限・aggregate 上限、cost_buffer（手数料・スリッページ考慮）を実装。
      - aggregate cap 超過時にスケーリングして残差を lot 単位で再配分するアルゴリズムを実装。
- リサーチモジュール（基盤）
  - `kabusys.research.factor_research` を追加（モメンタム等のファクター計算骨格）。
    - Momentum, MA200, ATR 等の計算に必要な定数と関数骨格を実装（DuckDB 接続を想定、prices_daily / raw_financials に依存）。
- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - Paper Trading の SQLite DB を読み、稼働率 / 注文成功率 / 送信率 / レイテンシ（平均・最大・P95）等を集計してレポート出力。
    - デフォルト閾値を定義し、PASS/FAIL 判定を行う。
    - DB テーブルが存在しない場合やデータ不足を想定して安全にデグレード（N/A 表示）する。
    - コマンドラインで期間指定（--from/--to）と DB パス指定（--db）可能。
- パッケージエクスポート整理
  - `kabusys.portfolio.__all__` を用いた明示的エクスポートを追加。
  - tools パッケージの初期化ファイルを追加。

### 変更
- 自動 .env ロード挙動
  - プロジェクトルートを `.git` または `pyproject.toml` から判定する方式に変更。これにより CWD に依存せずパッケージ配布後も動作。
  - `.env` の読み込みは OS 環境変数の保護を考慮して実装（`.env.local` は上書き、ただし既存の OS 環境変数は保護）。
- `.env` パーサ強化
  - `export KEY=val` 形式対応、クォートされた値のエスケープ処理、インラインコメントの取り扱いを改善。
- DB 接続ポリシー
  - 監視（monitoring）は起動環境にかかわらず本番の `sqlite_path` を使用する仕様を明示。
  - Execution は `paper_trading` 環境時に専用の paper DB を利用して本番 DB と分離。
- ログ出力の標準化
  - 全起動スクリプトは `setup_logging(app_name=...)` を使用して統一的なログ出力を行うように変更。

### 修正
- 例外・エラー耐性の向上
  - ポーリングループと実行スレッド周りで予期しない例外発生時にログ出力してループ継続／安全停止するように強化。
  - DB 初期化（監視テーブル）を冪等に行う `init_monitoring_db` 呼び出しを追加してテーブル未作成時の起動失敗を回避。
  - ログディレクトリ作成・ファイルハンドラ生成失敗時のフォールバック（コンソール出力のみ）を追加。
  - `process_priority` / `set_cpu_affinity` で権限エラーや未実装例外をハンドルして警告ログを出すように変更。
- validate_config の出力改善
  - 検証結果を INFO/WARNING/ERROR に分類して標準出力に出力し、終了コードで失敗/成功を返すように改善。

### 既知の事項 / 注意事項
- position_sizing 内の価格欠損時の扱い（price が 0.0 の場合のエクスポージャー過少見積り）は TODO コメントで注意喚起しています。将来的に前日終値や取得原価をフォールバックとして利用することが想定されています。
- factor_research の実装は骨格が含まれており、実データ取得ロジックや一部詳細計算は継続実装が必要です。
- .env は機密情報を含むため Git にコミットしないでください（config_setup からも明示的に警告あり）。

---

今後のリリースでは、strategy/execution 本体のロジック、より充実したユニットテスト、リサーチ関数の完成、監視・アラートの強化（LINE 通知連携など）を予定しています。