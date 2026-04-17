# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このファイルはリポジトリの現在のコードベースから推測して作成した初期リリース向けの変更履歴です。

全般的な注意:
- 日付はリリース作成日 (2026-04-17) を使用しています。
- 環境依存の挙動やデフォルト値はコード内のコメント／実装をもとに記載しています。

## [0.1.0] - 2026-04-17

### Added
- パッケージ基盤を追加
  - パッケージ名: KabuSys、バージョン `0.1.0`（src/kabusys/__init__.py）。
  - DuckDB / SQLite を使ったデータ保存と分析基盤をサポート。

- 環境設定・管理
  - Settings クラス（src/kabusys/config.py）を追加し、環境変数経由でアプリケーション設定を取得。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml から自動検出。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーの強化:
    - `export KEY=val` 形式をサポート。
    - シングル/ダブルクォート中のバックスラッシュエスケープ処理を考慮。
    - クォートなし行のインラインコメント取り扱い（直前がスペース/タブの場合のみコメントと認識）。
  - 必須値取得ヘルパー `_require()` を追加し、未設定時は ValueError を発生させる。

- 設定ウィザード CLI
  - `kabusys.config_setup`（src/kabusys/config_setup.py）:
    - 対話式ウィザードで .env を初期作成・更新。
    - デフォルト値・選択肢・シークレット入力をサポート。
    - 生成される .env に注釈を付与（'' .env は絶対に Git にコミットしない旨の注意を記載）。

- 設定検証 CLI
  - `kabusys.validate_config`（src/kabusys/validate_config.py）:
    - .env と config/*.yaml の存在・整合性チェック。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリチェック。
    - PyYAML 未インストール時は YAML の内容検証をスキップして警告。
    - `--strict` オプションで警告を FAIL 扱いにする。

- 実行エントリ・監視エントリ
  - ExecutionEngine 起動スクリプト `run_execution.py`（src/kabusys/run_execution.py）を追加:
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を呼び出し）。
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory でブローカークライアントを生成（MockBrokerClient を作成することで paper_trading をサポートする前提）。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てとスレッド実行制御（stop flag による安全停止）。
    - execution.pid ファイル管理（pid_file を受け取る）。

  - SystemMonitor ポーリングループ起動スクリプト `run_monitoring.py`（src/kabusys/run_monitoring.py）を追加:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 0 以下や不正な値はデフォルトにフォールバックし警告をログ出力。
    - 監視は環境に関わらず本番用 sqlite_path を使用（monitoring 用 DB 初期化を保証する init_monitoring_db を呼び出し）。
    - 停止フラグファイル (data/stop_requested.flag) を監視して安全にループを終了。

- 監視 DB 初期化ユーティリティを呼び出す仕組み（init_monitoring_db を run_* から呼出し、監視テーブルが存在することを保証）。

- プロセス優先度 / CPU 固定ユーティリティ
  - set_process_priority と set_cpu_affinity を実装（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX 系（Linux, Darwin, FreeBSD）で差異を吸収。
    - アクセス権限不足などで失敗した場合は警告を出しスキップ。
    - set_process_priority("high"|"normal"|"low") を提供。
    - set_cpu_affinity(n) で最初の n コアに固定（引数検証あり）。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）:
    - select_candidates: スコア降順 + タイブレークで signal_rank を使用。
    - calc_equal_weights / calc_score_weights（スコアが全て 0 の場合は等配分にフォールバックして警告）。

  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）:
    - apply_sector_cap: セクター別既存エクスポージャーを計算し、max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: regime ("bull","neutral","bear") による乗数（それ以外は 1.0 にフォールバックして警告）。

  - position_sizing（src/kabusys/portfolio/position_sizing.py）:
    - calc_position_sizes: allocation_method ("risk_based","equal","score") に対応。
    - risk_based: リスク許容率、stop_loss に基づく株数計算。
    - equal/score: weight に基づく配分、per-position 上限、lot_size（デフォルト 100）で丸め。
    - aggregate cap（available_cash）を超える場合はスケールダウンし、残余キャッシュで端数分を lot 単位で再配分するアルゴリズムを実装。
    - cost_buffer を用いて手数料／スリッページを保守的に考慮。
    - 価格欠損（<=0）の場合は該当銘柄をスキップ。

- 研究・ファクター計算
  - factor_research（src/kabusys/research/factor_research.py）:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を DuckDB (prices_daily) に対して計算。
    - calc_volatility: ATR（20日）・相対 ATR、20日平均売買代金、出来高比率を計算するクエリを実装。
    - DuckDB を用いて SQL ウィンドウ関数で効率的に算出する設計。

- ツール
  - Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）:
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から統計を抽出してレポートを出力。
    - 判定基準（デフォルト）:
      - 稼働率 (uptime) >= 99.0%
      - 注文成功率 (fill rate) >= 90.0%
      - 送信率 (send rate) >= 95.0%
      - P95 レイテンシ <= 200 ms
    - レポートは総ポーリング数、エラー数、稼働率、注文数/成功率、送信率、リスク却下数、平均/最大/P95 レイテンシを出力。
    - コマンドライン引数で期間 (--from / --to) と DB パス (--db) を指定可能。

### Changed
- 初期リリースのため履歴なし（初回公開）。

### Fixed
- 初期リリースのため履歴なし（初回公開）。

### Deprecated
- なし。

### Removed
- なし。

### Security
- 環境変数・機密情報の取り扱いに注意:
  - .env 出力では JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD をプレーンで書き出すが、config_setup において .env を Git にコミットしない旨の注意を明記。
  - validate_config による本番（KABUSYS_ENV=live）チェックで LINE トークン未設定や Kill Switch 設定の警告を行い、本番失敗リスクを軽減。

---

開発者向けメモ（実装からの推測）
- run_* スクリプトは stop flag / kill flag / pid ファイルを用いる運用を想定しており、安全停止と外部制御を重視した設計。
- Paper Trading と Live の DB を分離することでテストと本番のデータ混在を防止。
- 多くの機能は副作用を持たない純粋関数（portfolio / research）で実装されており、ユニットテストが容易な構造になっている。
- OS 権限や psutil の可用性に応じて優先度設定や CPU affinity はフォールバックするため、クロスプラットフォーム運用を意識した設計。

もし特定の変更点を詳細に追記したい場合（たとえば CLI の usage 例や各モジュールの API シグネチャ変更履歴など）、対象ファイルや期待する表現（簡潔／詳細）を教えてください。