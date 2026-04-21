# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
（注: リリース内容はリポジトリ内のソースコードから推測して記載しています。）

全体バージョン: 0.1.0

## [0.1.0] - 2026-04-21

### Added
- 初期リリース。以下の主要コンポーネントを追加。
  - 起動スクリプト / 実行系
    - run_execution.py
      - ExecutionEngine 起動用スクリプトを追加。
      - KABUSYS_ENV=`paper_trading` の場合は専用の MockBrokerClient を使用し、Paper Trading 用 SQLite（デフォルト: `data/paper_trading.db`）に記録することで本番 DB と完全分離。
      - プロセス優先度を設定（`set_process_priority("high")`）。
      - 停止フラグ（`data/stop_requested.flag`）や PID ファイル管理を実装。
      - duckdb / sqlite の接続初期化を行う。
  - 監視関連
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
      - 監視 DB は実行環境に関わらず本番の `sqlite_path` を利用（設計上の意図を明示）。
  - 設定管理 / CLI
    - config.py
      - .env の自動ロード機能（プロジェクトルート検出：`.git` または `pyproject.toml` を基準）。
      - .env パーサは `export KEY=val`、クォート、エスケープ、インラインコメント等に柔軟に対応。
      - Settings クラスを提供し、各種環境変数（DB パス、ログレベル、KABUSYS_ENV、Paper Trading 設定、監視閾値など）をプロパティとして検証付きで取得可能。
      - `paper_fill_mode` の値検証（有効値: `instant|partial|never|reject`）。
    - config_setup.py
      - 対話式ウィザードで .env を作成・更新する CLI を追加（シークレットマスキング、デフォルト値提示、.env 書き込み）。
    - validate_config.py
      - .env と `config/*.yaml` の基本的な妥当性検証 CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、PyYAML があれば YAML のパースチェック、`--strict` オプションによる警告を失敗扱いにする機能を提供。
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading の検証レポート生成 CLI を追加。
      - 稼働率 / 注文成功率 / 送信率 / レイテンシ（平均・最大・P95）等を集計し、しきい値比較（PASS/FAIL 判定）を行う。
      - 日付範囲指定（`--from` / `--to`）や DB パス指定（`--db` / 環境変数 `PAPER_TRADING_SQLITE_PATH`）に対応。
  - ポートフォリオ関連モジュール（純粋関数群）
    - portfolio/portfolio_builder.py
      - 候補選定（スコア降順・同点タイブレーク）、等金額・スコア加重の重み計算（スコア合計が 0 の場合は等金額フォールバック）。
    - portfolio/risk_adjustment.py
      - セクター集中上限の適用（既存ポジションを考慮して新規候補を除外）と市場レジームに応じた投下資金乗数（bull/neutral/bear）。
    - portfolio/position_sizing.py
      - 発注株数算出（`risk_based` と `equal`/`score` の割付方式）、単元株（lot_size）での丸め、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積り）考慮、残差に基づく追加配分ロジックを実装。
  - ユーティリティ
    - utils/logging_setup.py
      - ルートロガー向け統一ログ設定ユーティリティを追加（console stdout ハンドラ + 日次ローテーションファイルハンドラ、ログディレクトリ自動作成とフォールバック）。
    - utils/process_priority.py
      - cross-platform（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定補助。psutil を利用し、権限不足や未対応 OS を考慮して安全にスキップする処理を実装。
  - research/factor_research.py（ファクター計算基盤）
    - ファクター計算（モメンタム、MA200 乖離、ATR、出来高等）のための定数と calc_momentum のスケルトンを追加（DuckDB 経由での prices_daily 参照を想定）。
  - パッケージ情報
    - src/kabusys/__init__.py にてパッケージバージョン `__version__ = "0.1.0"` を設定。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- （初期リリースのため該当なし）

### Notes / Known limitations / TODO（ソースコードから推測）
- sector_exposure 計算時に価格が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性がある旨の TODO が存在。将来的に前日終値や取得原価でのフォールバックを検討する必要あり。
- 単元株（lot_size）は現状グローバル定義で全銘柄共通。将来的に銘柄別 lot_size マップへの拡張が示唆されている。
- logging_setup のファイルハンドラ作成やディレクトリ作成に失敗した場合、コンソール出力のみで継続する設計となっている。
- process_priority / set_cpu_affinity は権限不足や未対応 OS では動作をスキップして警告を出力する。
- research/factor_research.py はファイル末尾が未完（実装途中の可能性あり）。完全なファクター群の実装は今後の作業が必要。
- run_monitoring は監視用 DB に常に本番 sqlite_path を使用する設計（環境に依らず）。運用上の意図に従った挙動だが、開発時のデータ分離に注意が必要。
- validate_config は PyYAML 未インストール時に YAML パースをスキップして警告を出すため、環境によっては config ファイルの検証が限定される。

---

この CHANGELOG はコードの現状からの推測に基づくため、実際の変更履歴（コミットログ等）と差異がある可能性があります。必要であれば、Git のコミット履歴等を元に正確なリリースノートを作成します。