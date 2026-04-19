# Changelog

すべての注目すべき変更を記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット:
- 変更はバージョン単位で記載します。
- 各バージョンでの追加 (Added)、変更 (Changed)、修正 (Fixed)、セキュリティ (Security) 等を分類します。

[Unreleased]
- 現在未リリースの変更はここに記載します。

[0.1.0] - 2026-04-19
--------------------

Added
- 初期リリース: KabuSys 基本モジュール群を追加。
  - 実行/監視スクリプト
    - run_execution.py
      - ExecutionEngine 起動用スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合に MockBrokerClient を使用し、paper_trading 用の専用 SQLite(DB: data/paper_trading.db 既定) を使う仕組みを実装。
      - 起動時にプロセス優先度を設定 (set_process_priority("high"))。
      - 停止制御: data/stop_requested.flag を監視し、検知時にエンジンを停止。
      - 実行用 PID ファイル (data/execution.pid) を扱う。
    - run_monitoring.py
      - SystemMonitor ポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
      - Monitoring は環境にかかわらず本番用 sqlite_path を使用する設計（監視データは分離しない方針）。
      - 停止フラグ (data/stop_requested.flag) を検知してループを終了。
      - check_once() 実行時の例外はログ出力してポーリング継続（耐障害性）。
  - 設定読み込み/管理
    - config.py
      - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
      - 読み込み優先順: OS 環境変数 > .env.local > .env。自動ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - .env パース機能の強化: export 文、クォート内のエスケープ、インラインコメントの扱い等に対応。
      - 各種設定プロパティを提供 (J-Quants、kabuステーション、DB パス、監視閾値、環境種別判定等)。
      - PAPER_FILL_MODE の妥当性チェックやパスの Path 型返却、環境値のバリデーションを実装。
    - config_setup.py
      - インタラクティブな .env ウィザードを追加。既存 .env 読み込み、シークレットマスキング表示、保存機能を提供。
      - .env を生成する際にコミットしないよう明示的に警告を出力。
    - validate_config.py
      - 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリ存在確認、config/*.yaml の存在確認と（PyYAML がある場合の）パース検証を行う。
      - --strict モードで警告を FAIL 扱いにできる。
  - ポートフォリオ構築ロジック（純粋関数）
    - portfolio/portfolio_builder.py
      - select_candidates: BUY シグナルをスコア降順でソートし上位 N 件を返す（同点は signal_rank でタイブレーク）。
      - calc_equal_weights / calc_score_weights: 等配分・スコア加重の重み計算を実装。全スコアが 0 の場合は等配分へフォールバックして警告を出す。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクターごとの上限比率を計算し、超過しているセクターの新規候補を除外する（"unknown" セクターは制限対象外）。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull/neutral/bear、未知レジームはフォールバック1.0）。
    - portfolio/position_sizing.py
      - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数算出を実装。
      - 単元株丸め (lot_size)、per-position 上限・aggregate cap、コストバッファ考慮、スケーリングと残差処理を実装。
      - price 欠損時のスキップ、ポートフォリオ規模や available_cash を尊重した安全弁を実装。
      - 将来的な拡張 (銘柄別 lot_size) を TODO として明示。
  - ユーティリティ
    - utils/logging_setup.py
      - 統一ロギング設定ユーティリティを追加。stdout に StreamHandler、日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）をルートロガーに設定。
      - 既存ハンドラのクリア、ログディレクトリ作成失敗時はファイル出力をスキップして警告を出力。
      - 標準出力は stdout を使用（cron 等からのリダイレクト想定）。
    - utils/process_priority.py
      - psutil を用いたクロスプラットフォームなプロセス優先度設定を実装（Windows の priority class / POSIX の nice 値を吸収）。
      - CPU affinity 設定関数 set_cpu_affinity を提供。アクセス拒否等の例外は警告でスキップ。
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading 用検証レポート生成ツールを追加。システム稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）、リスク却下数等を集計して PASS/FAIL を判定。
      - デフォルト閾値を定義（稼働率 99%、フィル率 90%、送信率 95%、P95 レイテンシ 200ms）。
      - コマンドライン引数で期間指定・DB 指定可能。
  - 研究・ファクター計算基盤
    - research/factor_research.py（初期実装）
      - DuckDB 接続を受けてモメンタム等のファクターを計算する設計。モメンタム計算のための定数・仕様を定義（1M/3M/6M、MA200、ATR、出来高等）。
      - 実装はモジュール化されており、DuckDB の prices_daily/raw_financials テーブルのみ参照する方針。
      - （注）ファイルの末尾で calc_momentum の実装が途中である箇所あり（続きが必要）。

Changed
- なし（初期リリースのため既存コードの破壊的変更はなし）。

Fixed
- なし（初期リリース）。

Security
- config_setup にて .env の取り扱い注意を明示（「.env は絶対に Git にコミットしないこと」）。
- config.py の .env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能（テストや CI 向けの安全機構）。

Notes / Known limitations / TODO
- research/factor_research.calc_momentum の実装が未完（ファイル末尾で途中）。ファクター計算の追加実装が必要。
- position_sizing.calc_position_sizes:
  - price が欠損 (0.0) の場合、エクスポージャーが過少評価される可能性があり、将来的に前日終値や取得原価でフォールバックする旨を TODO として記載。
  - 銘柄ごとの単元株数対応は未実装（将来的な拡張点）。
- run_monitoring は「monitoring は環境にかかわらず本番 sqlite_path を使用」と明示しているため、監視データを環境ごとに完全分離したい場合は設定やコード変更が必要。
- process_priority / set_cpu_affinity は権限不足や未対応 OS でスキップし、警告を出力する設計。専用権限を期待する場合は運用ドキュメントで要注意。
- config/_parse_env_line は複雑なエスケープや特殊ケースを扱うが、すべての .env フォーマットバリエーションを保証するものではない（運用での確認推奨）。

Authors
- KabuSys 開発チーム（コードから推測してまとめた CHANGELOG）

旧バージョン
- なし（本リポジトリ初回公開相当の状態として 0.1.0 を記載）

（この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のリリースノートや変更履歴は開発チームの実際のコミット履歴 / リリース方針に基づいて調整してください。）