CHANGELOG
=========

このファイルは Keep a Changelog の様式に準拠しています。
リリース日付はコード内の実装状況から推測して付与しています。

フォーマット:
- Unreleased: 開発中の変更（現在は空）
- 各リリースは追加(Added)、変更(Changed)、修正(Fixed) 等のカテゴリで記載

Unreleased
----------
- なし

[0.1.0] - 2026-04-17
--------------------
初期リリース — KabuSys の基本機能を実装しました。主な追加点は以下の通りです。

Added
-----
- 基本パッケージメタ情報
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として追加。

- 設定管理
  - src/kabusys/config.py
    - .env の自動読み込み機能を実装（プロジェクトルート判定: .git または pyproject.toml）。
    - export 付き行、クォート／エスケープ、インラインコメントの扱いなどを考慮した .env パーサを実装。
    - OS 環境変数を保護するための上書きルール（.env.local > .env、既存 OS 環境変数は保護）を実装。
    - Settings クラスで主要な環境変数アクセスをラップ（J-Quants / kabu API / DB パス /監視閾値 / 環境種別等）。
    - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）。
    - KABUSYS_ENV のバリデーション（development/paper_trading/live）。

- 環境設定ウィザード CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - シークレット項目のマスク表示、選択肢・デフォルトの扱い、既存 .env の読み込み・再利用などを実装。
    - .env を書き出す _write_env() を実装（注意書きやセクション化されたテンプレートを出力）。

- 設定検証 CLI
  - src/kabusys/validate_config.py
    - 必須環境変数や KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在とパース検証（PyYAML が無ければ検証をスキップして警告）。
    - 本番環境向けの追加ガード（LINE 通知設定の有無、KILL_FLAG_CLEAR_ON_START の危険性など）。
    - --strict モードで警告を失敗扱いにできる。

- 実行エンジン起動スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading 時は専用の paper_sqlite_path を使用して本番 DB と分離（デフォルト: data/paper_trading.db）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - RiskManager に対するデフォルト RiskConfig（max_position_pct, max_utilization, rate_limit_per_sec 等）を設定。
    - エンジンの PID ファイル管理、data/stop_requested.flag による外部停止制御、スレッドでの実行と安全停止処理を実装。
    - 監視テーブルの初期化（init_monitoring_db）を起動時に実行（冪等）。

- 監視ループ起動スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor を定期実行するポーリングループ（デフォルト 60 秒）。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（不正値は警告してデフォルトにフォールバック）。
    - 監視は常に本番 sqlite_path を使用する（環境に依存しない挙動）。
    - stop フラグ（data/stop_requested.flag）の検知で終了。例外時はログ出力のうえ次ポーリングまで継続。
    - 起動直後にプロセス優先度を "high" に設定する仕組みを利用。

- 監視 DB 初期化フック
  - run_*.py から init_monitoring_db(sqlite_conn) を呼び出すことで監視テーブルが存在することを保証（冪等に実行）。

- Paper Trading 検証レポート
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）からデータを集計して検証レポートを出力。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出。閾値判定に基づく PASS/FAIL を表示。
    - P95 の算出、日付フィルタ（--from / --to）、DB パス指定オプションを実装。
    - デフォルト閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）。

- ポートフォリオ構築ライブラリ（純粋関数）
  - src/kabusys/portfolio/
    - portfolio_builder.py
      - 候補選定（select_candidates）、等配分・スコア加重（calc_equal_weights / calc_score_weights）を実装。スコアが全て 0 の場合は等配分にフォールバック。
    - risk_adjustment.py
      - セクター集中制限 apply_sector_cap（既存保有によるセクター暴露を計算し過剰セクターの新規候補を除外）。
      - レジーム乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知レジームはフォールバックして警告）。
    - position_sizing.py
      - calc_position_sizes を実装。allocation_method に "risk_based"/"equal"/"score" をサポート。
      - 単元（lot_size）丸め、1 銘柄上限・aggregate cap、cost_buffer による保守的見積り、スケールダウンと端数処理（残差配分）を実装。

- 研究・ファクター計算
  - src/kabusys/research/factor_research.py
    - DuckDB 接続を使ったファクター計算（prices_daily / raw_financials のみ参照）。
    - モメンタム（1M/3M/6M, MA200 乖離）、ボラティリティ（ATR）、流動性指標などの計算を実装（SQL ウィンドウ関数を利用）。
    - データ不足時の None 扱いやスキャン期間のバッファを考慮。

- プロセス優先度・CPU affinity ユーティリティ
  - src/kabusys/utils/process_priority.py
    - set_process_priority(level) を実装（Windows / POSIX を吸収、psutil を使用）。
    - set_cpu_affinity(cpu_count) を実装（最初の N コアに固定、例外時は警告してスキップ）。
    - psutil の権限不足や未対応 OS に対して安全にフォールバックし、警告ログを出力。

Changed
-------
- （初期リリースのため該当なし）

Fixed
-----
- 複数の堅牢化・フォールバック処理を追加
  - .env パーサでクォートやエスケープされた値、インラインコメントを正しく扱うようにして不正な .env に対する耐性を向上。
  - MONITOR_POLL_INTERVAL の不正値（0 や非数）を検出してデフォルトにフォールバックし、time.sleep の ValueError を回避。
  - psutil による優先度設定が失敗した場合に例外を握りつぶして警告ログで通知するようにし、プロセスがクラッシュしないように変更。
  - position_sizing のスケールダウン処理で端数配分（lot 単位）を再現性を持って処理。

Security
--------
- .env ファイルの取り扱いに関する注意を config_setup.py に記載（.env を決して Git にコミットしない旨のテンプレートヘッダを出力）。

Notes / Implementation details
------------------------------
- run_monitoring は監視用 DB として常に settings.sqlite_path を利用する点に注意（環境に依存しない監視設計）。
- run_execution は paper_trading モードで専用 DB を使うことで本番 DB と完全分離する設計を採用。
- 多くの関数は副作用がない純粋関数として実装されており、ユニットテストが容易な設計になっています（portfolio/* 等）。
- DuckDB を分析用途に使い、prices_daily などのテーブルに対して SQL を直接発行する設計。
- CLI ツール（config_setup, validate_config, tools.paper_verification_report）は Python モジュールとして実行可能。

今後の予定（想定）
------------------
- ExecutionEngine / SystemMonitor の詳細な内部実装の追加（ログ出力強化、メトリクス公開、より細かいリスク制御等）。
- 単体テスト、型注釈の拡充、CI 設定の整備。
- stocks マスタに単元情報を持たせる等、position_sizing の拡張（現在は全銘柄共通 lot_size を仮定）。

---

注: 本 CHANGELOG は提示されたソースコードから機能を推測して作成したものであり、実際のリポジトリ履歴（コミットメッセージ等）に基づくものではありません。必要ならば特定のファイルや変更点について詳しい説明や別リリースの分割を行います。