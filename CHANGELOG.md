# Changelog

すべての重要な変更はこのファイルに記録します。形式は "Keep a Changelog" に準拠します。

現在の日付: 2026-04-24

## [Unreleased]
- なし

## [0.1.0] - 2026-04-24
初回リリース。

### 追加 (Added)
- 実行エントリ/デーモン
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視コンポーネントは KABUSYS_ENV に関わらず本番用の sqlite_path を使用。
    - 停止フラグファイル (data/stop_requested.flag) による安全停止をサポート。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用 SQLite（data/paper_trading.db）に記録して本番 DB と分離。
    - PID ファイル管理・停止フラグによる安全停止をサポート。
    - 実行スレッドをデーモンで起動し、停止フラグ検知で engine.stop() を呼ぶループを実装。

- 設定管理 / 起動支援
  - config.py: 環境変数読み込み・設定管理モジュールを追加。
    - プロジェクトルートを .git / pyproject.toml で検出して自動的に .env/.env.local を読み込む（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可）。
    - .env 解析で `export KEY=val` 形式、クォート（'"/"）とエスケープ、インラインコメント処理をサポート。
    - 各種設定プロパティを定義（J-Quants、kabuAPI、DuckDB/SQLite パス、Paper Trading 関連、監視閾値、環境判定等）。
    - `PAPER_FILL_MODE` の検証（許容値: instant/partial/never/reject）。
    - `KABUSYS_ENV` と `LOG_LEVEL` の値検証。

  - config_setup.py: .env 初期作成・対話式ウィザードを追加。
    - 対話的に .env を生成・更新、シークレットは表示をマスク、生成後にファイルへ書き込み。
    - デフォルト値・選択肢付き項目を用意。

  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在チェック（PyYAML があればパース検証）。
    - `--strict` オプションで警告も失敗扱いにできる。
    - live 環境向けのガードチェック（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険設定の警告）。

- ユーティリティ
  - utils/logging_setup.py: ログ設定ユーティリティを追加。
    - stdout への StreamHandler（標準出力）と、日次ローテーション（TimedRotatingFileHandler）でファイル出力を設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - ログレベル解決: 引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"。
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）間の差分吸収を行い、`set_process_priority("high"|"normal"|"low")` を提供。
    - `set_cpu_affinity(n)` による最初の n コアに固定する機能を提供。
    - 権限不足や未対応プラットフォーム時は警告ログを出して安全にスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順でソート（同点は signal_rank 昇順でタイブレーク）。
    - calc_equal_weights: 等金額配分を返す。
    - calc_score_weights: スコア比率で正規化。全スコアが 0 の場合は等金額にフォールバックして警告出力。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクターごとの既存エクスポージャーが閾値を超える場合、新規候補を除外。unknown セクターは制限の対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバックし警告。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて発注株数を決定。lot_size（単元）丸め、単銘柄上限、aggregate cap（利用可能現金を超える場合のスケールダウン）を実装。コストバッファ考慮、残余で端数配分ロジックを追加。

- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成ツールを追加。
    - SQLite（Paper Trading DB）からシステム安定性、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計してレポート出力。
    - デフォルト閾値: 稼働率 >=99%、成立率 >=90%、送信率 >=95%、P95 レイテンシ <=200ms。判定を PASS/FAIL で出力。
    - コマンドラインで期間指定（--from / --to）および DB パス指定（--db）可能。

- リサーチ
  - research/factor_research.py: ファクター計算モジュールを追加（Momentum 等の計算ロジックを実装開始）。
    - DuckDB 経由で prices_daily / raw_financials を参照する設計（未完の箇所あり）。

- パッケージ情報
  - __init__.py: パッケージバージョン __version__ = "0.1.0" を追加。主要サブパッケージを __all__ に公開。

### 変更 (Changed)
- ログ出力の標準化
  - ログの StreamHandler を stderr ではなく stdout に向けることで、cron / Task Scheduler 等で stdout/stderr をまとめて扱いやすくした。

- 環境変数自動読み込みの挙動
  - .env の読み込み順を OS 環境 > .env.local（上書き）> .env（既存を尊重）とし、OS 環境は保護（.env.local でも上書きされない）。

### 修正 (Fixed)
- MONITOR_POLL_INTERVAL の扱い
  - 環境変数の不正値や 0 以下を検出してデフォルト（60 秒）にフォールバックするようにし、time.sleep に渡して ValueError になるのを防止。

- DB 初期化の冪等性
  - monitoring 用テーブルの初期化（init_monitoring_db）を起動時に実行し、テーブルが存在しない場合に備える。

### 注意点 (Notes)
- 監視（run_monitoring）は常に本番用 sqlite_path を参照します。テストや開発で本番 DB を汚したくない場合は注意してください。
- Paper Trading は paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離しています。Paper Trading を使う場合は KABUSYS_ENV を適切に設定してください。
- validate_config の警告には本番環境（KABUSYS_ENV=live）用の重要な指摘（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START＝1 の危険性）が含まれるため、本番運用前に必ず実行してください。
- research/factor_research.py は設計に基づく実装を含みますが、ファイル末尾に未完の箇所が存在します（今後完成予定）。

### 既知の制限 (Known issues)
- portfolio.position_sizing の lot_size は現状すべての銘柄で共通の固定値（デフォルト 100）。将来的に銘柄別単元をサポート予定。
- apply_sector_cap のエクスポージャー計算は price_map の欠損時に過少見積りとなる可能性があり、将来的に価格フォールバックを導入予定。

---

今後のリリースでは以下を予定しています（例）:
- research/factor_research の完全実装（全ファクター計算・最適化）
- 単元情報・銘柄マスタを取り込んだ position_sizing の拡張
- CLI / デーモン運用のユニットテスト追加とリリースパイプライン整備

（必要があれば、さらに詳細な変更点や開発履歴を追加します。）