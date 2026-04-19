# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠します。  
このファイルはコードベースから推測して作成した初期リリースノートです。

## [0.1.0] - 初回リリース (推定)
リリース日: 未設定

### 追加 (Added)
- プロジェクト全体の初期実装を追加。
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード用の DB（data/paper_trading.db）および MockBrokerClient を使用し、本番 DB と分離。
    - プロセス優先度を "high" に設定（utils.process_priority を利用）。
    - 停止フラグファイル (data/stop_requested.flag) による安全停止機構を実装。
    - 実行中の PID を data/execution.pid に保存（pid_file 対応）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計。
    - 停止フラグ検知によるループ終了処理を実装。

- 設定・環境管理
  - config.py
    - .env ファイルと OS 環境変数から設定を読み込み、Settings クラスを提供。
    - プロジェクトルートを .git または pyproject.toml を基準に探索して自動で .env をロード（無効化可能な KABUSYS_DISABLE_AUTO_ENV_LOAD を用意）。
    - 環境変数の厳密チェック用ユーティリティ（必須変数の取得 _require、enum チェック等）。
    - 各種設定プロパティ（DB パス、PID ファイルパス、閾値、PAPER_FILL_MODE 等）を定義。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI。
    - 初期値・選択肢・シークレット入力に対応し、.env の書式で保存する機能を提供。
  - validate_config.py
    - .env および config/*.yaml の存在・基本妥当性を検証する CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ検査、YAML のパース検査（PyYAML があれば）など。
    - --strict オプションで警告を失敗扱いにできる。

- 監視（Monitoring）
  - monitoring_db 初期化呼び出しを各起動スクリプトで保証（init_monitoring_db を使用して監視テーブルが存在することを冪等に確保）。

- ユーティリティ
  - utils/logging_setup.py
    - 共通のロギング設定ユーティリティを追加。
    - stdout への StreamHandler と、日次ローテーション (TimedRotatingFileHandler) のファイル出力（logs/<app_name>.log）を設定。
    - LOG_DIR 未作成時はファイルハンドラをスキップしてコンソール出力のみで継続するフォールバック処理あり。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"。
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows の priority class、POSIX の nice 値を扱う）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（権限不足時にワーニングでスキップ）。

- ポートフォリオ構築（Portfolio）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等分配 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコア全てが 0 の場合は等分配へフォールバックし警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限を実装する apply_sector_cap（"unknown" セクターは制限の対象外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（"bull"=1.0,"neutral"=0.7,"bear"=0.3）を追加。未知のレジームは 1.0 にフォールバックして警告。
  - portfolio/position_sizing.py
    - allocation_method に基づく株数決定ロジック（"risk_based","equal","score"）を実装。
    - 単元株（lot_size）で丸め、ポジション上限（max_position_pct）・投下資金上限（max_utilization）・手数料スリッページ見積り（cost_buffer）を考慮した aggregate cap ロジックを実装。
    - 利用可能現金を超える場合はスケールダウンし、残余を再配分するアルゴリズムを提供。

- リサーチ（Research）
  - research/factor_research.py（部分実装）
    - DuckDB 接続を受けて定量ファクター（Momentum, Value, Volatility, Liquidity）を計算する設計。モメンタム計算関数 calc_momentum の骨子あり（ターゲット日ベース、MA200, 1M/3M/6M リターン等）。
    - DuckDB の prices_daily / raw_financials を参照する想定。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード DB（デフォルト: data/paper_trading.db）を集計して検証レポートを出力。
    - 指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、P95 レイテンシ 等。
    - デフォルト閾値:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - コマンドラインで期間指定 (--from/--to) や DB パス指定 (--db) が可能。

### 変更 (Changed)
- N/A（初回リリースのため過去との変更は無し）。ただし、設計上の注意点やフォールバック処理を豊富に実装：
  - .env 自動ロードはプロジェクトルートの検出に依存し、見つからない場合はスキップ。
  - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のログのみで継続。
  - process_priority の操作は権限がない場合にワーニングを出してスキップ。

### 修正 (Fixed)
- N/A（初回リリース）。

### 既知の制約・注意点 (Notes / Known issues)
- research/factor_research.py はファイル末尾が途中で終わっており、実装が完了していない箇所がある可能性がある（calc_momentum の続きなど）。実稼働前に追加実装・テストが必要。
- position_sizing と apply_sector_cap の一部ロジックは価格データ欠損（価格=0.0）の場合に扱いが保守的になっており、将来的にフォールバック価格（前日終値や取得原価）を取り入れることを想定している。
- KILL / STOP フラグはファイル（data/kill.flag / data/stop_requested.flag）ベースで実装されているため、運用ドキュメントに従った取り扱いが必要。
- 一部の機能（YAML パース検査、DuckDB SQL 実行など）は外部ライブラリ（PyYAML, duckdb）に依存する。これらが未インストールの場合は該当検証/解析をスキップする処理が入っている。

---

今後の提案（推奨事項、次の作業）
- research/factor_research の未完部分の実装完了およびユニットテスト追加。
- ExecutionEngine / SystemMonitor を含む統合テスト・エンドツーエンドテストの追加。
- 各 CLI と主要モジュールに対するユニットテストおよび CI 設定の整備。
- 設定例（.env.example）・運用ドキュメント（Kill Switch の扱い、ログ保管方針、バックアップ等）の充実。

（この CHANGELOG はソースコードの構造・コメントから内容を推測して作成しています。正式なリリースノートを作成する際はコミット履歴や実際の変更差分を参照してください。）