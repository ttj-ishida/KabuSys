# Changelog

すべての注記は Keep a Changelog の方針に基づき、重要な変更を分かりやすく記録しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

現在のバージョン: 0.1.0 — 初回公開

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-18
初回リリース。システム全体の起動スクリプト、設定管理、監視・実行ユーティリティおよびポートフォリオ構築ロジックの基盤を導入。

### Added
- 基本パッケージ情報を追加
  - src/kabusys/__init__.py にバージョン情報（0.1.0）とエクスポート一覧を追加。

- 起動スクリプト／デーモン系
  - run_monitoring.py: システム監視ポーリングループの起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視プロセスは KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計。
    - 停止フラグファイル（data/stop_requested.flag）を検知して安全に終了。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し、paper_trading 用 DB（data/paper_trading.db）に完全分離して記録。
    - 起動前に停止フラグを確認し、フラグ検知で起動中止／停止を行う。
    - ExecutionEngine は別スレッドで実行され、停止フラグ／スレッド監視による優雅な終了を実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定・環境管理
  - src/kabusys/config.py: 環境変数／.env 読み込みと Settings API を追加。
    - プロジェクトルート自動検出（.git / pyproject.toml 基準）により .env を自動ロード（無効化フラグあり）。
    - .env 行パーサは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
    - 各種設定プロパティを提供（J-Quants、kabu API、LINE、DB パス、監視閾値、環境判定等）。
    - PAPER_FILL_MODE（"instant"|"partial"|"never"|"reject"）、PAPER_TRADING_SQLITE_PATH 等の paper_trading 関連設定をサポート。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
  - config_setup.py: 対話式ウィザードで .env を初期作成／更新する CLI を追加。
    - 複数の設定項目を対話で入力可能。シークレット入力のマスク、選択肢、デフォルト表示、書き出し機能を提供。
  - validate_config.py: 起動前に設定不備を検出する検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在・YAML パース（PyYAML がインストールされている場合）等を検証。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: 全起動スクリプトで共通に使えるロギング設定ユーティリティを追加。
    - StreamHandler を stdout に出力、TimedRotatingFileHandler で日次ローテーション（デフォルト logs/、30 日分保持）。
    - ログレベル・ログディレクトリの解決順を明確化（引数 > 環境変数 > デフォルト）。
    - ディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: Windows/Linux/macOS の差を吸収するプロセス優先度・CPU affinity 設定ユーティリティを追加。
    - set_process_priority(level) で "high"/"normal"/"low" を指定可能。プラットフォーム毎に適切な nice / priority を適用（権限不足時は警告でスキップ）。
    - set_cpu_affinity(cpu_count) により最初の N コアにピン留め可能（未サポート OS では noop）。

- Portfolio（銘柄選定・配分・株数決定）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を返す。
    - calc_equal_weights: 等金額配分 (1/N) を計算。
    - calc_score_weights: スコア加重配分を計算（全銘柄スコアが 0 の場合は等分配へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクターごとの既存エクスポージャーが閾値を超える場合、新規候補を除外するロジックを追加（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 重み・候補・リスクパラメータに基づき発注株数を計算。
      - allocation_method="risk_based" / "equal"/"score" をサポート。
      - 単元株（lot_size）で丸め、1銘柄上限、aggregate cap（available_cash）でスケーリングするアルゴリズムを実装。
      - cost_buffer を使った保守的コスト見積り、余剰キャッシュでの残差配分ロジックを実装。

- 監視／運用ツール
  - monitoring/initialization (実装参照): 監視用 DB 初期化を呼び出す init_monitoring_db を使用（冪等にテーブルを作成）。
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - 指定期間（--from / --to）または全期間で検証レポートを出力。
    - 稼働率（uptime）、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）などを算出し PASS/FAIL 判定を行う（しきい値を定義）。
    - デフォルト DB パスは data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能）。

- 研究用モジュール
  - research/factor_research.py: ファクター計算モジュール（Momentum / Value / Volatility / Liquidity）を追加。
    - DuckDB 接続を受け取り prices_daily / raw_financials を元にファクターを算出する設計。
    - モメンタム（1M/3M/6M、MA200乖離）、ATR、出来高系指標などを想定している（関数群の実装を含む）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数・シークレット関連の取り扱いに注意
  - .env は生成時に README に明示して Git にコミットしない旨を記載。
  - config_setup のシークレット項目は表示をマスクする実装。

---

補足:
- コマンドラインから直接起動できるエントリポイントは各モジュールの __main__ を通じて利用可能（例: python -m kabusys.run_execution, python -m kabusys.run_monitoring, python -m kabusys.config_setup, python -m kabusys.validate_config, python -m kabusys.tools.paper_verification_report）。
- 本 CHANGELOG はソースコードから推測できる機能・挙動に基づいて作成しています。実際の API や内部実装の詳細・追加変更はコミットログやリリースノートと合わせて確認してください。