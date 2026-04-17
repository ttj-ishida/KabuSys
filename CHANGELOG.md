CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" と Semantic Versioning.

フォーマット: 日本語

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-17
--------------------

Added
- 初回リリース。以下の主要コンポーネントを追加。
  - 実行・監視ランナー
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に記録して本番 DB と完全分離。
      - 実行中は data/execution.pid を利用。停止は data/stop_requested.flag の検出で行う。
      - スレッドでエンジンをデーモン実行し、停止フラグ検知で安全に停止。
      - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を導入し、初期ポートフォリオ値は broker.get_available_cash() から取得。
    - run_monitoring.py
      - SystemMonitor ポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下はデフォルトにフォールバック）。
      - 停止はプロジェクトルート/data/stop_requested.flag を検出。
      - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。

  - 設定管理・検証・セットアップ
    - config.py
      - .env 自動ロード（プロジェクトルートの .env/.env.local）、OS 環境変数の保護（上書き禁止）を実装。
      - .env パースの強化（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱い）。
      - 各種設定プロパティを提供（DB パス、PID/kill flag パス、しきい値、PAPER_FILL_MODE の検証等）。
    - config_setup.py
      - 対話式ウィザードで .env を作成/更新する CLI を追加（既存値の読み込み、シークレットマスク表示、選択肢サポート）。
    - validate_config.py
      - 起動前に .env と config/*.yaml の基本チェックを行う CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、PyYAML があれば YAML パース検証、KABUSYS_ENV=live 向けのガード（LINE トークン未設定、KILL_FLAG_CLEAR_ON_START の警告）を実装。
      - --strict オプションで警告を FAIL 扱いにできる。

  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
      - スコアが全て 0 の場合は等配分にフォールバックして警告。
    - portfolio/risk_adjustment.py
      - セクター集中制限を適用する apply_sector_cap を実装（売却予定銘柄除外、"unknown" セクターは適用除外）。
      - 市場レジームに基づく資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未知レジームはフォールバックで 1.0）。
    - portfolio/position_sizing.py
      - ポジションサイズ計算 calc_position_sizes を実装（allocation_method: risk_based / equal / score）。
      - 単元株（lot_size）での丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）、cost_buffer を考慮した保守的見積もり、端数の再配分ロジックを含む。

  - リサーチ / ファクター計算
    - research/factor_research.py
      - DuckDB を使ったファクター計算モジュールを追加（momentum / volatility 等）。
      - prices_daily / raw_financials テーブルのみを参照し、各銘柄ごとに mom_1m/3m/6m、ma200_dev、ATR、平均売買代金、出来高比率などを算出。

  - ユーティリティ
    - utils/process_priority.py
      - psutil を使ったクロスプラットフォームのプロセス優先度と CPU affinity 設定ユーティリティを追加。
      - Windows / POSIX (Linux, Darwin, FreeBSD) を区別して適切な優先度を設定し、権限不足や未対応環境では警告を出してスキップ。

  - 運用ツール
    - tools/paper_verification_report.py
      - ペーパートレード用 DB から検証レポートを生成するツールを追加。
      - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。
      - デフォルト基準値を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）し、PASS/FAIL を判定。
      - --from/--to/--db オプションで期間・DB を指定可能。

Changed
- パッケージ初期化
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。公開 API としてサブパッケージ名を __all__ に列挙。

Fixed
- （初回リリースのため該当なし）

Notes / Implementation details
- DB 関係
  - Monitoring 用の sqlite は環境に関係なく settings.sqlite_path（デフォルト data/monitoring.db）を使用する設計。
  - Paper Trading は settings.paper_sqlite_path（デフォルト data/paper_trading.db）で本番と分離。
  - DuckDB 連携は分析処理（factor/research 等）および ExecutionEngine のための共有リソースとして導入。

- 設定ファイルの取り扱い
  - .env 自動ロードはプロジェクトルートが検出できる場合にのみ行う。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env.local は .env を上書きする（ただし OS 環境変数は保護され上書きされない）。

- プロセス制御
  - 起動時に set_process_priority("high") を呼び出してプロセス優先度を高く設定しようとする（失敗時は警告で続行）。

Security
- .env の生成スクリプトは .env を Git にコミットしないよう注意喚起を出力。

Acknowledgements
- 初回公開。今後は変更をセマンティックバージョニングに従って本ファイルに追記します。