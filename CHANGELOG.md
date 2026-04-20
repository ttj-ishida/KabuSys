# Changelog

すべての重要な変更点を Keep a Changelog の形式に従って記録します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

現在のバージョン: 0.1.0

## [Unreleased]

## [0.1.0] - 2026-04-20
最初の公開リリース。自動売買システム本体の基礎的なモジュール群と運用用ユーティリティを追加しました。

### 追加 (Added)
- コアパッケージ初期化
  - pakage version を `__version__ = "0.1.0"` として設定（src/kabusys/__init__.py）。

- 実行・監視プロセス起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV が `paper_trading` の場合は paper-trading 用の専用 SQLite（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と分離。
    - エンジンはスレッドとして実行。停止判定は `data/stop_requested.flag` を監視して行う。
    - 実行時 PID ファイル (`data/execution.pid` など) の扱いをサポート。
  - システム監視起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト: 60 秒）。
    - 監視は環境にかかわらず本番用の `sqlite_path` を使用する設計。
    - 停止フラグ (`data/stop_requested.flag`) の存在でループを終了。

- 設定管理・自動ロード
  - Settings クラスにより環境変数から設定値を取得する仕組みを追加（src/kabusys/config.py）。
    - .env 自動読み込み機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
    - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - 複数の設定プロパティを提供（DB パス、API トークン、Paper Trading 周り、監視閾値、PID/kill flag パス等）。
    - `PAPER_FILL_MODE` の許容値チェック（`instant` / `partial` / `never` / `reject`）を実装。
    - `KABUSYS_ENV` の許容値チェック（`development` / `paper_trading` / `live`）。
  - .env ファイルのパース機能を強化
    - `export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュによるエスケープ、行内コメントの扱いなどに対応。

- 設定検証 CLI
  - `python -m kabusys.validate_config` による起動前の設定検証ツールを追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ確認、config/*.yaml 存在およびパース検証（PyYAML がインストールされている場合）など。
    - `--strict` オプションで警告を失敗扱いにできる。
    - 本番 (`KABUSYS_ENV=live`) に関するガード文言（LINE 通知未設定や kill flag の自動クリア設定）を追加。

- 環境設定ウィザード
  - `.env` を対話式に作成・更新するウィザードを追加（src/kabusys/config_setup.py）。
    - J-Quants / kabu API / DB パス / ログレベル / Kill Switch 等の主要設定を対話的に入力・保存。
    - 秘匿値は表示をマスクして扱う。
    - 最終確認後に `.env` を書き出す（デフォルトパス: プロジェクト直下の `.env`）。

- ロギングユーティリティ
  - 一貫したログ設定を提供するユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - コンソール出力は stdout（StreamHandler）に統一。
    - ファイル出力は日次ローテーション（TimedRotatingFileHandler）で保存（デフォルト: `logs/<app_name>.log`、30 日保持）。
    - 環境変数 `LOG_DIR` / `LOG_LEVEL` によるカスタマイズをサポート。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続。

- プロセス優先度・CPU 固定ユーティリティ
  - Windows / POSIX の差を吸収する `set_process_priority`、`set_cpu_affinity` を追加（src/kabusys/utils/process_priority.py）。
    - `set_process_priority("high" | "normal" | "low")` でプロセス優先度を設定（可能な範囲で）。
    - `set_cpu_affinity(n)` で最初の n コアにピン固定（権限や OS により失敗時は警告でスキップ）。
    - 実行スクリプトから起動時に優先度を高く設定する運用を採用（run_execution/run_monitoring が呼び出し）。

- ポートフォリオ構築関連（純粋関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順ソート（同点時は signal_rank でブレーク）、上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重（スコア合計が 0 の場合は等配分へフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター別エクスポージャを計算し、指定上限（デフォルト 30%）を超えるセクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じて乗数を返却（`bull`=1.0, `neutral`=0.7, `bear`=0.3）。未知のレジームは 1.0 にフォールバックして警告を出す。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - allocation_method に応じた発注株数計算（`risk_based` / `equal` / `score`）。
    - 単元（lot_size）で丸め、1 銘柄上限・aggregate 上限（available_cash）を考慮したスケーリングロジックを実装。
    - cost_buffer による保守的なコスト見積もり（スリッページ・手数料を想定）を加味。
    - 不足価格情報や価格が 0 の場合は該当銘柄をスキップする安全策を実装。

- Execution コンポーネントの組み立て
  - Broker 抽象化ファクトリ（src/kabusys/execution/broker_factory.py を想定）等を用いて BrokerClient, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine を組み合わせて起動する初期実装（run_execution.py から呼び出し）。（※ 実際の詳細実装ファイルは本差分の一部として参照されているが、このリリースでは組み合わせ・起動ロジックを整備）

- 監視用 DB 初期化呼び出し
  - 起動時に監視用テーブルの存在を保証するための init_monitoring_db 呼び出しを実装（run_monitoring / run_execution）。

- Paper Trading 検証レポート
  - `python -m kabusys.tools.paper_verification_report` によるレポート出力ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - Paper Trading 用 SQLite（環境変数 `PAPER_TRADING_SQLITE_PATH`、デフォルト: `data/paper_trading.db`）を読み、以下の指標を算出:
      - 稼働率（uptime_pct）、ポーリング数、エラー数
      - 注文成功率（Filled / Created）、送信率（Sent / Created）
      - リスク却下数（risk_logs）
      - レイテンシ: 平均・最大・P95（P95 は全値を取得して計算）
    - Pass/Fail のしきい値を定め判定（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）。
    - 日付フィルタ（--from / --to）および --db オプションをサポート。

- 研究用ファクターモジュール（部分実装）
  - DuckDB 接続を受けて各種ファクター（Momentum / Value / Volatility / Liquidity）を計算するためのモジュール骨子を追加（src/kabusys/research/factor_research.py）。
    - モメンタム計算関数 calc_momentum のシグネチャと設計注釈を実装（実装途中で一部トランケートあり）。

### 変更 (Changed)
- なし（初回リリースのため既存からの変更扱いはありません）

### 修正 (Fixed)
- なし（初回リリース）

### 注意事項 / 運用メモ
- 監視（run_monitoring）は環境にかかわらず Settings.sqlite_path（本番監視 DB）を使用します。テスト用途で監視を分離したい場合は DB 設定の上書きやコードの調整が必要です。
- .env 自動ロードはプロジェクトルートを基準に行います。CI / テスト環境で自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- process priority / CPU affinity の設定は OS と権限に依存します。失敗した場合は警告が出て処理は継続されます。
- Paper Trading 用 DB は本番 DB と分離されますが、運用時に誤った DB を指定しないよう `.env` の `PAPER_TRADING_SQLITE_PATH` を確認してください。
- research/factor_research.py は設計に基づいた実装を進めていますが、関数の一部が実装途中の状態です。利用時は対応状況を確認してください。

### 既知の制限（今後対応予定）
- position_sizing の lot_size は全銘柄共通の想定（将来的に銘柄別 lot_map をサポート予定）。
- apply_sector_cap は価格が欠損（0.0）だとエクスポージャーが過少見積もられる可能性があり、フォールバック価格の導入を検討中。
- ログ出力設定でディレクトリ作成に失敗した場合はファイル出力が無効化されるが、より明確なエラーハンドリングの追加を検討。

---

開発に関する問い合わせや次のリリースで対応してほしい項目があればお知らせください。