# Changelog

すべての注目すべき変更点を記録します。  
このファイルは "Keep a Changelog" の慣習に従っています。

次のバージョンに含める変更は Unreleased に記載し、本番リリースは日付付きのセクションで管理してください。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-17
初回公開リリース。本リリースでは自動売買システム KabuSys のコアユーティリティ、実行/監視ランナー、設定管理、ポートフォリオ構築、検証ツール、研究用ファクター計算などの基本機能を実装しています。

### Added
- 実行・監視ランナー
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）へ完全に分離して記録。
    - デーモンスレッドでエンジンを起動し、プロジェクトルートの stop フラグ (data/stop_requested.flag) を監視して安全停止。
    - 実行中 PID を data/execution.pid に記録する仕組み（pid_file パスの注入）。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority.set_process_priority を利用）。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する（監視用 DB の初期化を行う）。
    - 停止フラグ (data/stop_requested.flag) の検出でループを終了。

- 設定管理
  - config.py
    - .env の自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml で検出）。
    - .env/.env.local の読み込み順序を実装（OS 環境変数を保護）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能。
    - Settings クラスを追加し、アプリケーション設定をプロパティ経由で取得可能に（必須変数の取得とバリデーションを含む）。
    - デフォルトパス（DUCKDB_PATH, SQLITE_PATH 等）や PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE のバリデーションを実装。
    - 環境（KABUSYS_ENV）、ログレベル等の検証ロジックと helper プロパティ（is_live, is_paper, is_dev）を追加。

- 設定作成・検証 CLI
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - 各設定項目のラベル、デフォルト、選択肢、説明を表示し、既存 .env を読み込んで再利用可能。
    - シークレット設定は表示をマスクして保存。生成される .env には注意書きを付与（絶対にリポジトリにコミットしない）。
  - validate_config.py
    - 起動前に .env および config/*.yaml の基本的な妥当性チェックを行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、パス存在チェック（親ディレクトリの存在検出で警告）、YAML ファイルの存在およびパース検証（PyYAML が存在する場合）。
    - `--strict` フラグで警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - calc_score_weights は全スコアが 0 の場合に等金額にフォールバックしログ警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中の上限適用 (apply_sector_cap) と市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。
    - apply_sector_cap は既存保有のセクター別時価を計算し、上限超過セクターからの新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier は "bull"/"neutral"/"bear" に対応し、未知のレジームは 1.0 でフォールバック（警告ログ）。
  - portfolio/position_sizing.py
    - 株数決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）単位で丸め、1銘柄上限や aggregate cap（available_cash） を考慮してスケールダウン・端数配分を行う。
    - cost_buffer により実効コスト見積りを保守的に考慮。

- 監視・実行補助ユーティリティ
  - utils/process_priority.py
    - プロセス優先度（nice / Windows 優先度クラス）を OS に依存せず設定するユーティリティを追加。
    - set_cpu_affinity により最初の N コアにプロセスを固定する機能を追加（サポートされない環境では安全にスキップ）。
    - アクセス権限不足等の失敗時に警告ログでフォールバック。

- 検証・レポートツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB から稼働率、注文成功率、送信率、レイテンシ等を集計して検証レポートを生成するスクリプトを追加。
    - デフォルトしきい値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し、PASS/FAIL を判定。
    - 日付フィルタ --from / --to、--db オプション対応。DB が存在しない場合にエラーメッセージを出力。
    - P95 の独自計算、レイテンシ平均/最大・P95 を出力。

- 研究用ファクター計算
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールを追加（Momentum / Volatility 等の計算を提供）。
    - calc_momentum は約1ヶ月/3ヶ月/6ヶ月リターンと MA200 乖離を計算。データ不足時は None を返す設計。
    - calc_volatility（実装途中まで含む）で ATR/平均売買代金等を計算する設計を開始。

- パッケージメタ
  - __init__.py にてバージョンを 0.1.0 に設定し、主要パッケージを __all__ で宣言。

### Changed
- 初版のため該当なし（初回実装）。

### Fixed
- 初版のため該当なし（初回実装）。

### Notes / Breaking changes / 重要な運用上の注意
- .env ファイルは自動読み込みされる（プロジェクトルート検出に成功した場合）。ただし OS 環境変数が優先され `.env.local` は `.env` より優先して上書きされます。テストや特殊な状況では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。
- 本番稼働時は KABUSYS_ENV を必ず `live` に設定する前に validate_config.py で設定検証を行ってください。validate_config は LINE 通知設定や Kill Switch の有効性も警告します。
- .env には機密情報（API トークン・パスワード等）を含みます。絶対に Git 等の VCS にコミットしないでください（config_setup.py のヘッダに注意書きがあります）。
- run_monitoring は監視 DB に対して常に本番 sqlite_path を使用します（KABUSYS_ENV に依らず）。monitoring 用 DB の管理に注意してください。
- run_execution は paper_trading モード時に paper_trading 用 DB にデータを書きます。実際の取引を行う `live` モードでは本番 SQLite パス・kabuステーション API が使用されます。必ず設定を確認してください。
- position_sizing の単元丸めや aggregate cap のアルゴリズムは保守的設計です。実運用する場合は lot_size（銘柄別対応）やコストバッファ等のチューニングが必要です。

---

今後の予定メモ（例）
- research/factor_research の Volatility 部分の完成、追加ファクター（Value, Liquidity 等）の実装完了
- ExecutionEngine / SystemMonitor の詳細ログ・メトリクス拡張
- テストカバレッジの追加（単体テスト、統合テスト）
- 銘柄ごとの lot_size マスタ導入による position_sizing の拡張

----------------------------------------------------------------------------- 
（注）この CHANGELOG は提供されたコードから推測して作成しています。実際の変更履歴・リリースノートはリポジトリ運用方針に従って適宜更新してください。