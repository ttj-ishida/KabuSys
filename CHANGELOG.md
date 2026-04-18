# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースの内容から推測して作成した初期の変更履歴です。

## [Unreleased]

- ドキュメント／警告追加
  - 各モジュール内に注意事項や将来的な改善案（TODO）を明記。
  - position_sizing.calc_position_sizes の将来的拡張（銘柄別単元対応）や、
    risk_adjustment.apply_sector_cap の価格欠損時の挙動について注記を追加。

- テスト・運用上の補助
  - .env の自動読み込みを無効化する環境変数（KABUSYS_DISABLE_AUTO_ENV_LOAD）を明示。
  - run_monitoring / run_execution の停止フラグ（data/stop_requested.flag）および PID 管理の挙動を整理（ログ出力強化）。

---

## [0.1.0] - 2026-04-18

### Added
- 基本モジュールの追加（KabuSys v0.1.0 初回リリース）
  - パッケージ初期化: `src/kabusys/__init__.py` にバージョン情報（`__version__ = "0.1.0"`）を追加。

- 環境・設定管理
  - Settings クラス（`src/kabusys/config.py`）
    - .env/.env.local 自動読み込み（プロジェクトルートの検出は .git または pyproject.toml ベース）。
    - 環境変数ラッパー（J-Quants, kabu API, LINE, DB パス, 監視閾値 など）。
    - PAPER_FILL_MODE の検証（有効値: "instant"|"partial"|"never"|"reject"）。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証ロジック。
    - is_live / is_paper / is_dev のヘルパープロパティ。

  - .env 読み込みの堅牢化
    - クォートやエスケープ、インラインコメントの扱いに対応するパーサを実装。
    - OS 環境変数を保護して .env.local で上書きできる仕組みを提供。

- CLI ユーティリティ
  - 設定ウィザード: `src/kabusys/config_setup.py`
    - 対話式で .env を生成／更新。主要な項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE トークン、LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）をサポート。
    - 既存 .env の読み込みと Enter による既存値再利用、シークレット項目のマスク表示。
  - 設定検証: `src/kabusys/validate_config.py`
    - 必須環境変数やパス、config/*.yaml の存在・パース（PyYAML があれば中身の検証も実施）を検査。
    - `--strict` オプションで警告を FAIL 扱いにするモードを提供。
    - 本番環境用の追加ガード（LINE 設定の未設定や Kill Switch の自動クリア設定など）をチェック。

- 実行・監視エントリポイント
  - 実行エンジン起動スクリプト: `src/kabusys/run_execution.py`
    - ExecutionEngine の起動フローを実装（BrokerFactory 経由のブローカクライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite DB を使用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）検出で安全に停止。
    - 起動時にプロセス優先度を "high" に設定。
  - 監視ループ起動スクリプト: `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する点に注意。
    - 停止フラグや KeyboardInterrupt を監視して正しくクローズ。

- モジュール群（投資ロジック・ユーティリティ）
  - portfolio モジュール（src/kabusys/portfolio/）
    - portfolio_builder.py
      - select_candidates（スコア降順選択）、calc_equal_weights、calc_score_weights（スコアが全て 0 の場合は等配分にフォールバック）。
    - risk_adjustment.py
      - apply_sector_cap（セクター集中上限の適用、"unknown" セクターは上限適用対象外）、calc_regime_multiplier（レジームに応じた投下資金乗数）。
    - position_sizing.py
      - calc_position_sizes（risk_based / equal / score の配分方式を実装、lot_size 単位で丸め、aggregate cap のスケーリングおよび残差の配分ロジックを実装）。
  - research モジュール
    - factor_research.py
      - DuckDB 接続を使ったファクター計算ユーティリティ群（モメンタム、ボラティリティ等の指標を算出する関数のベース実装）。
      - モメンタム（1M/3M/6M、MA200乖離）、ATR、平均出来高などを計算。
  - tools
    - paper_verification_report.py
      - ペーパートレーディング用 SQLite（デフォルト data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ（P95）などを集計してレポートを出力。
      - PASS/FAIL 判定基準（稼働率 99% など）の実装。

- DB 関連
  - デフォルトパスの明記: DUCKDB_PATH (data/kabusys.duckdb), SQLITE_PATH (data/monitoring.db), PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)。
  - init_monitoring_db 呼び出しを行い監視テーブルの存在を保証（冪等処理）。

- ユーティリティ
  - process_priority（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定する関数 `set_process_priority`。
    - CPU affinity を最初 N コアに固定する `set_cpu_affinity`。
    - 権限不足や未対応 OS 時に例外ではなく警告でスキップする堅牢設計。

### Changed
- （初出なので変更履歴は無し）コードベースの設計上の分離:
  - 実行（Execution）と監視（Monitoring）の DB 分離（paper_trading 用 DB を明確に分ける設計）。
  - 設定読み込みの優先順位を明確化: OS 環境変数 > .env.local > .env。

### Fixed
- .env パースの改善
  - export プレフィックス対応、クォート内部のバックスラッシュエスケープ、インラインコメントの取り扱いなどの改善により .env のパース堅牢性を向上。

### Removed
- （初出なので削除は無し）

### Security
- 機密情報（J-Quants token, kabu API password, LINE トークン）は .env に保存する前提で、config_setup の出力でシークレット項目をマスク表示するなど取り扱いに注意喚起を追加。
- .env は絶対に Git にコミットしない旨の注記を config_setup に明記。

---

## 既知の制約・注意点（コード内コメントからの抜粋）
- apply_sector_cap:
  - price_map に価格が欠損（0.0）がある場合にエクスポージャーが過小評価される可能性がある。前日終値や取得原価でのフォールバックを検討する必要あり。
- calc_position_sizes:
  - 現在はグローバルな lot_size を使用。将来的には銘柄別単元（stocks マスタ）に対応する予定。
- run_monitoring:
  - 監視は常に本番 sqlite_path を使用するため、paper_trading 環境でも監視データが本番 DB に書き込まれる点に注意。
- PAPER_FILL_MODE の不正値は ValueError を発生させるため、環境変数設定時は有効値を使用すること。

---

この CHANGELOG はコードを解析して推測に基づいて作成しています。実際のリリース履歴や日付、細かな変更は開発記録（git commit, タグ等）に従って更新してください。