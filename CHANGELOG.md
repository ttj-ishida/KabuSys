Keep a Changelog
=================

このファイルは Keep a Changelog の書式に準拠しています。
フォーマット: https://keepachangelog.com/ja/1.0.0/

0.1.0 - 2026-04-19
------------------

初回公開リリース。KabuSys の基本的なランタイム・ユーティリティ、実行／監視スクリプト、設定管理、ポートフォリオ構築ロジック、検証ツール群を含みます。

### Added
- 実行・監視エントリポイント
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、本番 DB と完全に分離した paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用する設計をサポート。
    - 停止フラグ (data/stop_requested.flag) を監視し、安全に停止できるループを実装。
    - PID ファイル (data/execution.pid) を扱う。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下は無効としてデフォルトへフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（監視 DB の明確な利用方針）。
    - 停止フラグ (data/stop_requested.flag) 検出でループ終了。

- 設定関連
  - config.py
    - 環境変数/`.env` の自動読み込み（OS 環境変数を保護する仕組みあり）。読み込み順: OS > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途想定）。
    - .env パーサを実装（export プレフィックス、クォート、エスケープ、インラインコメントの扱いに対応）。
    - Settings クラスで各種設定をプロパティとして提供（DB パス、PID/KILL フラグパス、閾値等）。PAPER_FILL_MODE の妥当性チェックを実装。
  - config_setup.py
    - 対話式ウィザードで .env の作成・更新を支援。
    - 秘密値はマスクして表示、保存前に確認プロンプトを表示。
  - validate_config.py
    - 起動前チェック CLI。必須環境変数や KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在および YAML パース（PyYAML があれば）を検証。
    - --strict を指定すると警告も失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーへ設定。
    - LOG_DIR/LOG_LEVEL の環境変数や引数で上書き可能。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - stdout を使うことでスケジューラ実行時のリダイレクト運用に配慮。
  - utils/process_priority.py
    - Windows/Linux/macOS を吸収したプロセス優先度設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定するユーティリティを提供。
    - 権限不足や未対応環境を考慮して失敗時は警告ログでフォールバック。

- ポートフォリオ構築ライブラリ（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - シグナル選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコアがすべて 0 の場合は等配分にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（当日売却予定銘柄を除外するオプションあり）。
    - 市場レジームに応じた投下倍率 calc_regime_multiplier（"bull"/"neutral"/"bear" をサポート、未知レジームは 1.0 でフォールバック）。
    - セクター計算時の price 欠損に関する TODO コメントを追加（将来的なフォールバック価格導入の注記）。
  - portfolio/position_sizing.py
    - position サイズ決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1 銘柄上限・総投下上限・コストバッファ考慮、aggregate cap 超過時のスケーリングと残差に対する追加配分アルゴリズムを実装。
    - TODO: 将来的な銘柄別 lot_size サポートを想定した設計注記。

- データ分析 / 研究ユーティリティ
  - research/factor_research.py
    - DuckDB 接続を受けて定量ファクター（Momentum、MA200 乖離、ATR 等）を計算するためのモジュール骨組みを追加（prices_daily / raw_financials テーブル参照設計）。
    - 日数定数やスキャン範囲の定義を含む（モメンタム用の短期〜長期窓、ATR/VOLUME ウィンドウなど）。
    - （ファイル末尾で計算関数の実装が続く設計になっていることを確認。）
  - DuckDB 統合
    - DuckDB 接続処理を実行/監視スクリプトや研究モジュールで受け渡し可能な形で統一。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプト。
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを計算して PASS/FAIL 判定を行う。
    - デフォルトしきい値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - P95 計算ロジック、期間フィルタの SQL 生成を実装。DB パスは引数/環境変数/デフォルトの順で解決。

### Changed
- パッケージバージョンを __version__ = "0.1.0" として設定。
- 各種デフォルト値と環境変数の既定値を明確化（MONITOR_POLL_INTERVAL=60、SQLITE_PATH/DUCKDB_PATH のデフォルト等）。

### Fixed
- 環境変数パーサの挙動を強化（クォート内のエスケープ・インラインコメント処理・export プレフィックス対応）して .env の柔軟な記述に対応。
- run_monitoring のポーリング間隔取得で不正値（0 以下や非整数）を検出しデフォルトにフォールバックするようにして time.sleep での例外を防止。

### Notes / TODO
- portfolio/risk_adjustment.apply_sector_cap: price が欠損 (0.0) の場合にエクスポージャーが過小見積りされ得る点を注記。前日終値などのフォールバック価格導入を将来的に検討。
- position_sizing: 現状は全銘柄共通の lot_size を想定。将来的に銘柄別単元をサポートする設計拡張を検討中。
- research/factor_research.py はファクター算出ロジックの実装が続く想定（ファイル末尾での実装継続を確認）。必要に応じて追加実装/テストが必要。

セキュリティ
------------
- .env は絶対にリポジトリへコミットしない旨を config_setup のヘッダコメントで明示。
- 設定ウィザードは秘密値をマスクして表示する（表示は ****）。

互換性
------
- 初期リリースのため後方互換性の観点は今後の変更により考慮します。設定名／環境変数名はリファレンスを参照してください。

作者
----
KabuSys プロジェクト（ソースコード内の各モジュール実装に基づく推測）

--- 

注: 上記 CHANGELOG は提示されたコードベースの内容から推測して作成しています。追加の変更履歴（コミットメッセージやリリースノート）がある場合は、合わせて反映してください。