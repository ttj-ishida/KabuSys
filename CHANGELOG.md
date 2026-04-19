CHANGELOG
=========

この CHANGELOG は Keep a Changelog のフォーマットに準拠しています。  
コードベースから推測できる「注目すべき変更点」を日本語で記載しています。実際のコミット履歴がないため、リリースや日付はコード内のバージョンや現在の状況から推定しています。

[Unreleased]
-------------
（今後の変更予定・未リリースの項目があればここに追加してください）

[0.1.0] - 2026-04-19
-------------------
初回公開（推定） — KabuSys v0.1.0

Added
- 実行・監視用の起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。BrokerClientFactory を用いてブローカークライアントを生成し、ExecutionEngine をデーモンスレッドで実行。停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による制御に対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番用 sqlite_path を使用する設計。
- 設定管理・ウィザード・検証ツール
  - config.py: 環境変数と .env(.env.local) の自動ロード、堅牢な .env 解析（コメント・クォート・export対応）、Settings クラス（多数のプロパティとバリデーション）を追加。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - config_setup.py: 対話式ウィザードで .env を作成/更新できる CLI を追加（シークレット項目のマスク表示、既存値の再利用、保存確認）。
  - validate_config.py: .env および config/*.yaml の事前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV・LOG_LEVEL の妥当性検査、DB パスの親ディレクトリチェック、PyYAML があれば YAML パース検証、KABUSYS_ENV=live 時の追加警告、--strict オプションで警告を FAIL 扱いにする機能を搭載。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder: シグナル選定（select_candidates）および重み計算（calc_equal_weights, calc_score_weights）を追加。
  - portfolio.risk_adjustment: セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた資金乗数 calc_regime_multiplier を追加。未知レジーム時はフォールバック（1.0）し警告を出す。
  - portfolio.position_sizing: allocation_method（risk_based / equal / score）に沿った株数計算を実装。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）によるスケーリング、cost_buffer（手数料・スリッページ想定）を考慮した配分アルゴリズムを追加。price 欠損時のスキップやスケール時の残差処理（remainders）を実装。
- ロギング・プロセス管理ユーティリティ
  - utils.logging_setup: ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定する setup_logging を追加。ログレベル/ログディレクトリの解決順を定義し、ファイル出力失敗時はコンソールのみで継続する耐障害性を実装。
  - utils.process_priority: プラットフォーム差分を吸収する set_process_priority（high/normal/low）と set_cpu_affinity を追加。Windows / POSIX の違いを吸収し、権限不足などで失敗した場合は警告を出してスキップする。
- Paper Trading 向け検証ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から集計し、稼働率・注文成功率・送信率・レイテンシ（P95）等を算出するレポート生成スクリプトを追加。閾値（稼働率 99%、成功率 90%、送信率 95%、P95 latency 200ms）で PASS/FAIL を判定。コマンドラインで --from/--to/--db をサポート。
- 研究用ファクター計算（骨子）
  - research.factor_research: Momentum 等のファクター計算モジュールの骨子を追加（DuckDB 接続を受けて prices_daily / raw_financials を参照する設計、モメンタム期間・ATR などの定数定義）。（モジュールの末尾は未完の可能性あり）

Changed
- データベース運用方針の明確化
  - 監視モジュールは KABUSYS_ENV に関係なく本番用 sqlite_path を使用して監視データを記録するよう設計（監視は常に本番 DB を対象に想定）。
  - 実行エンジンは paper_trading 環境時に専用 SQLite（paper_sqlite_path、デフォルト data/paper_trading.db）を使用して本番 DB と完全分離する仕組みを採用。
- 環境変数取り扱いの改善
  - .env の読み込みで OS 環境変数を保護する protected 機能を導入（.env.local は上書き可能だが OS のキーは上書きしない）。
  - PAPER_FILL_MODE のバリデーションを導入（instant/partial/never/reject のみ受け付ける）。
  - Settings.env / log_level に厳密なバリデーションを追加。

Fixed
- ロギング設定の二重登録防止
  - setup_logging は既存ハンドラを flush/close してからクリアすることで、複数回初期化時の二重出力を回避。
- プロセス優先度設定の堅牢化
  - 未対応 OS や権限不足での失敗をハンドリングし、致命的エラーにならないよう警告でスキップする実装に修正。

Security
- シークレット値の取り扱い改善
  - config_setup の対話で J-Quants トークンや kabu API パスワードをシークレット扱い（表示をマスク）にし、.env に直接平文で保存することを注意喚起（.env を Git にコミットしないよう README/ファイルヘッダで注意書き）。

Notes / その他
- 停止制御はファイルフラグ方式（data/stop_requested.flag, data/kill.flag）を採用。run_execution と run_monitoring はこのフラグを監視して安全に終了する。
- 多くの機能がファイルパス（duckdb, sqlite, log_dir 等）や挙動を環境変数で上書き可能。主要な環境変数の名前はコード内ドキュメント / config_setup の項目で確認可能。
- research.factor_research の末尾が途中で切れている（start_da... のような未完のシンボルが見える）ため、実装の続きまたは整合性チェックが必要。

今後の提案（参考）
- factor_research の完全実装とテスト追加（DuckDB クエリの正当性検証）。
- .env の機密情報を OS のシークレットストア（例: vault, keyring）と連携するオプション。
- 単体テスト・CI の導入。validate_config を CI で実行して設定不備を自動検出する仕組みの導入を推奨。

---

注: 上記は提供されたソースコードの内容から推測して作成した CHANGELOG です。実際のコミットやリリースノートがある場合は、それに合わせて正確な日付・著者・詳細を更新してください。