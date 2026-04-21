# Changelog

すべての変更は Keep a Changelog の形式に従います。  
Semantic Versioning を想定しています。

## [Unreleased]

- ドキュメント化・テスト用の小さな改善や未解決の TODO を追加。
  - portfolio/position_sizing.py の将来拡張（銘柄ごとの lot_size マップ化）や
    risk_adjustment.apply_sector_cap の価格フォールバックに関する注記が残っています。
  - research/factor_research.py は実装途中の断片が含まれており（末尾で切れている）、
    完了・整備が必要です。

---

## [0.1.0] - 2026-04-21

初回公開リリース。

### 追加 (Added)

- 起動スクリプト・運用ツール
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境（KABUSYS_ENV）に関わらず本番の sqlite_path を使用して監視データを記録。
    - 停止リクエストはプロジェクトの data/stop_requested.flag ファイルを監視して行う。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用の専用 SQLite DB を使用（`data/paper_trading.db` をデフォルト）。
    - 停止フラグ（data/stop_requested.flag）と PID 管理（data/execution.pid）に対応。
    - BrokerClientFactory 経由で本番/モックのブローカークライアントを切り替えられる設計。
- 設定関連
  - config.py:
    - 環境変数ラッパー Settings クラスを実装。各種設定（DB パス、API トークン、監視閾値、環境判定等）をプロパティで提供。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動ロードを実装（OS 環境変数を保護して上書き制御）。
    - .env の自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - Paper Trading 用の設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）をサポートし、入力チェックを実施。
  - config_setup.py: 対話式ウィザードで .env を作成/更新する CLI を追加（シークレット入力マスク、選択肢、デフォルト表示など）。
  - validate_config.py: .env と config/*.yaml の起動前検証ツールを追加。`--strict` オプションで警告も失敗扱いにできる。
- ロギング・プロセス制御
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定するユーティリティを追加。
    - ログディレクトリ自動作成および作成失敗時のフォールバック（コンソール出力のみ）に対応。
  - utils/process_priority.py:
    - クロスプラットフォームでのプロセス優先度設定ユーティリティを追加（Windows / POSIX に対応）。
    - CPU affinity を設定する set_cpu_affinity() を追加。
- ポートフォリオ構築関連（純粋関数）
  - portfolio/portfolio_builder.py:
    - select_candidates(): スコア降順で候補選定。
    - calc_equal_weights(), calc_score_weights(): 等金額・スコア加重の重み計算（スコア合計がゼロの場合は等配分にフォールバックして警告）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap(): セクター集中制限の適用（既存保有を考慮、当日売却予定銘柄を除外可、"unknown" セクターは制限対象外）。
    - calc_regime_multiplier(): 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知レジームはフォールバックして 1.0）。
  - portfolio/position_sizing.py:
    - calc_position_sizes(): allocation_method に応じた発注株数計算（risk_based / equal / score）。
    - 単元株（lot_size）丸め、max_position_pct / max_utilization による個別・総合上限、cost_buffer を考慮した保守的見積り、合計超過時のスケーリングと再配分ロジックを実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成スクリプトを追加。システム稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL を判定。
    - P95 計算、期間フィルタ（--from / --to）、DB パスの引数/環境変数対応を実装。
- research/factor_research.py（骨格）
  - DuckDB を用いたファクター計算モジュールの設計方針と一部定数、calc_momentum の仕様を記述。実装の一部が未完（実装継続予定）。

### 変更 (Changed)

- .env 読み込み・解析
  - .env パーサーを堅牢化:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープと閉じクォートの検出をサポート。
    - クォートなし値のインラインコメント扱いルールを改善（'#' の直前に空白がある場合のみコメントとして扱う）。
  - _load_env_file(): override フラグと protected（OS 環境変数保護）を導入し、上書きポリシーを明確化。
- run_monitoring.py / run_execution.py
  - 両スクリプトで起動時に set_process_priority("high") を呼ぶようにして、重要プロセスの優先度を上げる運用を想定。
  - DB 接続や duckdb 結合は起動時に初期化し、finally で確実にクローズするように変更。
  - run_execution.py は paper_trading 環境時に paper_sqlite_path を使用することで本番 DB から分離。
  - 停止フラグ検知時のログメッセージを追加（起動抑制や安全停止のため）。
- validate_config.py
  - 起動前チェックを充実化:
    - 必須環境変数の存在チェック、プレースホルダ検出。
    - DB パスやログレベル、KABUSYS_ENV の値検証。
    - config/*.yaml の存在チェックと、PyYAML がある場合はパース検証（未インストール時はスキップして警告）。
    - 本番（live）環境時のガードチェック（LINE 通知設定や Kill Flag の自動クリア設定に対する警告）。
- logging_setup.py
  - 標準出力には stdout を利用する設計（cron/Task Scheduler でのリダイレクトを想定）。
  - 既存ハンドラの二重登録を避けるため、再設定時は既存ハンドラを flush/close してから削除するように変更。
- パフォーマンス・安定性向上
  - position_sizing のスケーリング処理で残差（fractional remainder）に基づく安定的な再配分アルゴリズムを採用し、再現性のため二次キーとしてコードを利用するようにした。
  - process_priority.set_process_priority / set_cpu_affinity は権限不足や未対応 OS の場合に警告を出して処理をスキップするようにして堅牢化。

### 修正 (Fixed)

- calc_score_weights(): 全銘柄スコア合計が 0.0 の場合に警告を出して等金額配分にフォールバックするよう修正（ゼロ除算回避）。
- paper_verification_report.py:
  - P95 計算の実装を追加（空リスト時は None を返す）。
  - レポート生成でテーブルや列が存在しない場合に sqlite3.OperationalError を捕捉して堅牢に動作するようにした。
- .env 書き込み（config_setup）:
  - 生成される .env のテンプレートと書式を整備。重要な注意（.env を Git にコミットしない等）を追記。

### 既知の問題 (Known issues)

- research/factor_research.py の実装が未完のままファイル末尾で途切れているため、実運用では未実装の機能がある点に注意。
- apply_sector_cap() にて price が欠損（0.0）の場合にセクターエクスポージャーが過少見積りされる可能性がある。将来的に前日終値や取得原価によるフォールバックを検討する TODO が残っている。
- position_sizing の将来的拡張（銘柄別 lot_size のサポートなど）は未実装。
- .env の自動ロードはプロジェクトルートが検出できない場合はスキップされる。意図しない挙動を避けるため CI/テスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` の設定を推奨。

### セキュリティ (Security)

- .env に API トークン・パスワードを保存する設計のため、config_setup のヘッダに「.env は絶対に Git にコミットしない」旨の注意を追加済み。
- ログにはシークレットを平文で出力しない運用を想定（config_setup ではシークレット値を表示時にマスク）。

---

開発・運用に際しての次の推奨作業:
- research/factor_research.py の完全実装とユニットテストの追加。
- apply_sector_cap の価格フォールバック実装（前日終値等）。
- position_sizing の銘柄別 lot_size サポートと追加の境界ケーステスト。
- CI での validate_config の導入（--strict モードを利用したチェック）。