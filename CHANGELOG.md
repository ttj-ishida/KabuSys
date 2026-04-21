# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
このプロジェクトのバージョニングは Semantic Versioning を想定しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-21

初回公開リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。以下はコードベースから推測してまとめた主な追加点・挙動説明・既知の注意点です。

### 追加 (Added)
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient（BrokerClientFactory 経由）を利用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に記録。実稼働 DB と分離。
    - 実行中の停止はプロジェクトルートの data/stop_requested.flag を監視。PID を data/execution.pid に記録する想定。
    - プロセス優先度を起動直後に `high` に設定する処理を追加（utils.process_priority を使用）。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトを使用。
    - 監視は環境にかかわらず本番 sqlite_path（data/monitoring.db デフォルト）を用いる挙動が実装されている点に注意。
    - 停止フラグ（data/stop_requested.flag）によるループ停止をサポート。

- 設定管理・検証・ウィザード
  - config.py
    - .env 自動読み込み機構（プロジェクトルート検出: .git または pyproject.toml を基準）を実装。環境変数優先で .env → .env.local の順にロード。
    - 複雑な .env パースを備え、export 付きやクォート、インラインコメント、エスケープに対応。
    - Settings クラスを実装し、各種設定（J-Quants, kabuAPI, DB パス、監視閾値、環境判定など）をプロパティで提供。
    - PAPER_FILL_MODE（paper trading のフィルモード）や PAPER_TRADING_SQLITE_PATH 等の環境変数対応。
  - config_setup.py
    - 対話式の .env 作成/更新ウィザードを追加。シークレット項目のマスクや既存値の再利用、保存前確認を実装。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在・パース（PyYAML 利用可の場合）を検証。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテート、30 日保持）をルートロガーに設定する共通ユーティリティを追加。
    - ログレベル/ログディレクトリは引数・環境変数（LOG_LEVEL, LOG_DIR）で上書き可能。ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみ続行。
  - utils/process_priority.py
    - Windows / POSIX（Linux/Mac/FreeBSD）を吸収するプロセス優先度設定関数 set_process_priority を実装（psutil 利用）。CPU affinity を設定する set_cpu_affinity も追加。
    - アクセス不可や未対応 OS の場合は警告を出してスキップする安全設計。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - BUY シグナルの選抜 select_candidates、等金額配分 calc_equal_weights、スコア加重 calc_score_weights を実装。スコアが全て 0 の場合は警告して等分配にフォールバック。
  - portfolio/risk_adjustment.py
    - apply_sector_cap：既存ポジションに基づくセクター露出チェックにより、新規候補を除外するロジックを実装。売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に応じた資金乗数を返す関数を追加。未知レジームは警告して 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes：allocation_method（"risk_based" / "equal" / "score"）に応じて買い付け株数を計算する複雑なロジックを実装。
      - risk_based: 損切り幅・リスク許容率からベース株数を算出し単元株丸め。
      - equal/score: ウェイトと max_utilization を考慮して各銘柄の割当を算出。
      - aggregate cap：利用可能現金を超える場合にスケールダウンし、lot_size（デフォルト 100）単位で残差配分を行う。
      - cost_buffer（スリッページ/手数料見積り）を考慮。
      - 価格欠損・0 の場合はスキップしログ出力。

- モニタリング DB 初期化・DuckDB 統合
  - init_monitoring_db を各スクリプト起動時に冪等で呼び出し、監視テーブルの存在を保証。
  - DuckDB（分析用）接続を統一的に利用（Settings.duckdb_path）。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite を読み取り、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数を集計してレポート出力する CLI を追加。
    - P95 計算、期間フィルタ（--from/--to）、閾値を用いた Pass/Fail 判定を実装。
    - デフォルト DB は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db。

- リサーチ（ファクター）モジュール（初期実装）
  - research/factor_research.py（モメンタム等の指標計算を意図した実装を追加。DuckDB 経由で prices_daily / raw_financials を参照する設計。ファイル末尾に未完の記述（start_da で途切れ）あり）。

### 変更 (Changed)
- パッケージ初期バージョンを設定
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

### 修正 (Fixed)
- なし（初回リリースのため特定のバグ修正履歴は無し）

### 既知の注意点 / TODO
- research/factor_research.py が途中で途切れている（start_da でファイル末尾が中断）。ファクター計算の完全実装は今後の作業が必要。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合の取り扱いに TODO コメントあり（前日終値や取得原価をフォールバックする案が示唆されている）。
  - 単元株数 lot_size は現在全銘柄共通の想定。将来的に銘柄毎の lot_map を受け取る拡張を検討中。
- run_monitoring は「監視は環境にかかわらず本番 sqlite_path を使用する」設計になっているため、paper_trading 実行環境で監視 DB を分離したい場合は運用ルールの調整または実装変更が必要。
- process_priority / cpu_affinity の設定は psutil の権限や OS に依存するため、設定に失敗するケースでは警告によりスキップされる。
- .env 自動読み込みはプロジェクトルートの検出に依存するため、配布後や特定の環境で期待どおりに動作しない場合がある（その場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化可能）。

### セキュリティ (Security)
- なし

---

参考:
- 本 CHANGELOG はコード内容から推測して作成しています。実際のリリースノートとして公開する場合は、各機能の詳細や設計上の決定（特に監視 DB の扱い、paper_trading と本番 DB の分離方針など）をプロジェクト関係者で確認のうえ追記してください。