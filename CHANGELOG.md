# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

※ このリリースはソースコードから推測して作成した初回リリースの要約です。

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 実行エントリスクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient（BrokerClientFactory により生成）を使用し、paper trading 用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に記録して本番 DB と分離。
    - エンジンは別スレッドで実行し、data/stop_requested.flag による停止検知および data/execution.pid に PID を書き込む運用を想定。
    - リスクマネージャーのデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を含む組み立て処理を実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視は常に本番 DB を参照する設計）。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。

- 設定管理・環境変数関連
  - config.py
    - Settings クラスを提供。環境変数をラップして型変換や妥当性検証を行うプロパティを実装（例: env / log_level の検証、PAPER_FILL_MODE の有効値チェック、パス解決）。
    - .env 自動読み込み機能を導入（プロジェクトルートを .git / pyproject.toml を基準に探索）。既存の OS 環境変数を保護する仕組みあり。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - config_setup.py
    - .env を対話式に作成/更新するウィザードを実装。複数の設定項目定義、既存 .env 読み込み、シークレットのマスク表示、保存確認等をサポート。
  - validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI を実装（--strict を付けると警告も失敗扱い）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、PyYAML がある場合は YAML ファイルのパース検証、live 環境向けの保護チェックなど。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - アプリケーション共通のロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）を組み合わせて設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR / 引数による上書きに対応。
  - utils/process_priority.py
    - psutil を用いたプロセス優先度設定ユーティリティを追加（Windows / POSIX の差分吸収）。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足や未対応環境では警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコア合計が 0 の場合は等金額配分へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装。既存保有を考慮してセクター上限を超えている場合に新規候補を除外。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピングと未知値のフォールバック）を実装。
  - portfolio/position_sizing.py
    - 発注株数算出 calc_position_sizes を実装。allocation_method に応じて "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、ポジション上限、aggregate cap（利用可能現金に合わせてスケールダウン）、cost_buffer による保守的見積り、残差処理（lot 単位での追加配分）を実装。

- 解析・検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、リスク却下数、レイテンシ）を集計し、PASS/FAIL 判定を出すレポート生成スクリプトを追加。
    - 日付フィルタ（--from / --to）や DB パス指定（--db / 環境変数）に対応。P95 計算や N/A の扱いなどを実装。

- その他
  - パッケージ初期化ファイル src/kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を追加。
  - research/factor_research.py の骨組み（DuckDB を利用したファクター計算の設計、モメンタム等の定義・定数）を追加（実装は途中）。

### 変更 (Changed)
- 環境変数パースの堅牢化（config._parse_env_line）
  - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱いを実装。
  - クォートなしの値に対するコメント認識ルールを導入（`#` 前が空白/タブの場合はコメントとみなす）。
- .env ファイル読み込み順序
  - 自動読み込みの優先順位を OS 環境変数 > .env.local > .env に明確化。既存 OS 環境変数は保護される。

### 修正 (Fixed)
- 起動スクリプトの安定化
  - run_monitoring と run_execution は起動時にプロセス優先度を最初に High に設定するように変更され、実行環境の初期化がより一貫するようになった（set_process_priority の呼び出しを追加）。
  - run_execution 内で監視テーブルが存在しない場合に備え init_monitoring_db を呼び出し冪等的にテーブルを準備する処理を追加。

### 注記 (Notes)
- 設定の安全性
  - .env は絶対にリポジトリにコミットしないようスクリプトに明記されています（config_setup の出力ヘッダ参照）。
- Paper Trading と本番 DB の分離
  - paper_trading 実行時は明示的に paper_sqlite_path を使用し、本番監視 DB と分離する設計になっています。監視（run_monitoring）はあえて本番 sqlite_path を使う仕様ですので運用時の注意が必要です。
- 外部ライブラリ依存
  - PyYAML がインストールされていない場合、validate_config は YAML 内容の検証をスキップします（警告を出力）。
  - psutil が必要（process_priority、CPU affinity）。権限等で失敗するケースは警告でスキップ。
  - DuckDB/SQLite を使用するためそれらに対応した環境が必要。

---

今後のリリースで期待される改善（例）
- factor_research の完全実装（ファクター計算ロジックの完成）
- Engine / Monitor のより詳細なテストおよび障害回復処理の強化
- 銘柄別の lot_size 対応（stocks マスタとの連携）
- ロギング・モニタリングのメトリクス拡張とアラート連携（LINE 等）

--- 

この CHANGELOG はソースコードからの推測に基づいています。実際の変更履歴やリリースノートと差異がある場合は適宜修正してください。