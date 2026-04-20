# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-20

初回リリース。日本株自動売買システム「KabuSys」のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、および検証ツールを実装しました。

### 追加 (Added)
- 全体
  - パッケージの初期バージョンを定義（__version__ = "0.1.0"）。
  - Settings クラスを導入し、環境変数から設定を一元管理（env 検証、ログレベル、DB パス、しきい値等）。
  - .env 自動ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパース処理を強化（export 形式対応、単/二重クォートのエスケープ、インラインコメントの扱い等）。

- 起動 / 実行スクリプト
  - run_execution.py: 実際の ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを作成。ExecutionEngine を別スレッドで実行し、停止フラグ（data/stop_requested.flag）を監視して安全に停止可能。
    - 実行中 PID 管理用の PID ファイル (data/execution.pid) をサポート。
  - run_monitoring.py: SystemMonitor 向けのポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視データを本番 DB に記録）。

- 設定管理 / ツール
  - config_setup.py: 対話式の環境設定ウィザードを追加（.env の初期作成/更新を支援）。
    - 各項目の説明表示、既存 .env 読み取り、シークレットマスク表示、保存確認を実装。
  - validate_config.py: 起動前の構成検証 CLI を追加。
    - 必須環境変数の確認、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在と YAML パース（PyYAML 未インストール時は警告）を実施。
    - --strict オプションで警告を FAIL 扱いにする機能を追加。
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計・判定し PASS/FAIL を出力。
    - 日付フィルタ（--from / --to）および DB パス指定（--db / 環境変数）に対応。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順（同点時 signal_rank 昇順）でソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア重み計算。全スコアが 0 の場合は等金額にフォールバックし警告を出力。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限を検査し、上限超過セクターの新規候補を除外。
      - unknown セクターは上限適用除外（除外しない）。
      - 売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームでは警告を出して 1.0 にフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method に応じた発注株数計算を実装（"risk_based" / "equal" / "score"）。
      - 単元株（lot_size）で丸め、1 銘柄上限、aggregate cap（available_cash）を考慮したスケールダウン。
      - cost_buffer による保守的なコスト見積りをサポート。
      - 価格欠損時のスキップ、超過時の再配分ロジック（端数処理）を実装。

- ユーティリティ
  - utils.logging_setup: 統一的なロギング設定ユーティリティを追加。
    - stdout への StreamHandler（stdout を採用）と、日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - ログレベル決定順: 引数 > 環境変数 LOG_LEVEL > デフォルト。
  - utils.process_priority: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収し、psutil を使用して優先度 (high/normal/low) を設定。
    - set_cpu_affinity により先頭 N コアへの固定を実装。権限不足等は警告を出してスキップ。

- 研究用モジュール（未完）
  - research.factor_research: モメンタム系ファクター計算関数の骨組みを実装（calc_momentum 等）。DuckDB 接続を使用して prices_daily / raw_financials を参照する設計。未実装部分あり（モジュール末尾が途中で切れているため今後拡張予定）。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 注意点 / 既知の制約 (Notes / Known issues)
- apply_sector_cap:
  - price_map に price が欠損（0.0）だとエクスポージャーが過少見積りされ、想定外に候補除外が解除される可能性があります（将来的にフォールバック価格導入を検討）。
- calc_score_weights:
  - 全銘柄のスコアが 0 の場合に等金額配分へフォールバックする挙動を採用（警告ログあり）。
- run_monitoring:
  - 監視はどの環境でも settings.sqlite_path（本番パス）を使う設計。環境に応じて監視 DB を分離したい場合は設定変更が必要。
- logging_setup:
  - ログディレクトリ作成失敗時はファイルロギングを諦めて標準出力のみで継続する（起動時に警告を出力）。
- validate_config:
  - PyYAML が未インストールの場合、config/*.yaml の内容検証をスキップして警告を出力する。

### セキュリティ (Security)
- なし

### 将来の改善（TODO）
- research.factor_research の完全実装（ファクター計算ロジックの完成）。
- 銘柄ごとの lot_size を stocks マスタで管理するなど、position_sizing の拡張。
- 価格欠損時のフォールバックロジック（前日終値など）の導入。
- より詳細な監視メトリクス（I/O、ディスク使用率閾値アラート等）。

---

このリリースはコードベースの初期導入を反映しています。各モジュールはユニットテスト、統合テスト、実運用での検証を通じてさらに堅牢化していく予定です。