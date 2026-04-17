# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  

注: 以下は提示されたコードベースから推測して作成した変更履歴です。実際のコミット履歴ではありません。

## [Unreleased]

### Added
- 起動用スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag によるフラグ検出で行う。起動時にプロセス優先度を High に設定する。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用し MockBrokerClient と分離して動作する。プロセス優先度設定、停止フラグ検出（data/stop_requested.flag）、PID ファイル管理を実装。

- 設定・環境管理
  - config.py: .env 自動読み込み機構を実装（プロジェクトルートは .git または pyproject.toml で検出）。.env/.env.local のロード順序と保護（OS 環境変数の上書き保護）を実装。複雑な .env のパース（export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメント）に対応。Settings クラスを提供し、各種設定プロパティ（DB パス、paper_trading 関連、監視しきい値、ログレベル、環境判定等）を定義。
  - config_setup.py: .env を対話式に作成・更新するウィザードを追加。シークレットのマスク表示、デフォルト、選択肢、保存テンプレートを提供。

- 設定検証 CLI
  - validate_config.py: 起動前に .env および config/*.yaml の存在や妥当性を検証する CLI を追加。必須環境変数の有無、プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、PyYAML がない場合のパーススキップ、KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告）などを検出。--strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: 候補選定（スコア降順・タイブレーク）select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコアが 0 の場合は等金額にフォールバック）を追加。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap（当日売却予定の銘柄を除外するオプションあり）、市場レジームに基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマップ）を追加。
  - portfolio/position_sizing.py: position sizing ロジック calc_position_sizes を追加。allocation_method（risk_based / equal / score）に対応、lot_size（単元株）考慮、max_position_pct / max_utilization / cost_buffer を踏まえた aggregate cap 判定とスケールダウン、端数処理（lot 単位で残差分を再配分）などを実装。
  - portfolio/__init__.py でパブリック API をエクスポート。

- 実行系の補助
  - utils/process_priority.py: psutil を使ったプロセス優先度設定 set_process_priority と CPU affinity 固定 set_cpu_affinity を追加。Windows / POSIX 差分を吸収し、アクセス権限不足等は警告でフォールバックする。

- リサーチ（ファクター計算）
  - research/factor_research.py: DuckDB 接続を使ったファクター計算モジュールを追加。モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（ATR20、相対 ATR、20日平均出来高等）を計算する関数を実装。SQL（ウィンドウ関数）ベースで prices_daily テーブルを参照する設計。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py: ペーパートレード DB から稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計してレポートを出力するツールを追加。閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を実装。DB が存在しない場合のエラーメッセージや、テーブル欠如に対する例外耐性あり。

### Changed
- なし（新規導入のため）

### Fixed
- なし（新規導入のため）

### Security
- .env の取り扱いに関する注意喚起を config_setup の出力に明記（.env を Git にコミットしない旨のテンプレート）。

---

## [0.1.0] - 2026-04-17

初期リリース。上記の機能群をまとめて公開。

### Added
- パッケージ本体
  - パッケージメタ情報: kabusys/__init__.py（__version__ = "0.1.0"）
- 起動スクリプト: run_monitoring.py, run_execution.py
- 設定関連: config.py（自動 .env ロード、Settings クラス）、config_setup.py（対話ウィザード）、validate_config.py（構成検証 CLI）
- ポートフォリオ構築: portfolio/（portfolio_builder, risk_adjustment, position_sizing）
- 実行補助ユーティリティ: utils/process_priority.py
- リサーチ: research/factor_research.py（DuckDB ベース）
- ツール: tools/paper_verification_report.py（ペーパートレード検証レポート）

### Notes
- run_execution は paper_trading モード時に本番 DB と完全に分離された PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用する設計になっています。
- run_monitoring は環境にかかわらずデフォルトの sqlite_path（監視用）を使用して監視データを記録します（モニタリング DB 初期化処理あり）。
- .env の自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 にすることで無効化可能です。

---

今後の改善候補（コード内の TODO/注意点から推測）
- position_sizing: 銘柄ごとの lot_size を stocks マスタから参照する拡張。
- risk_adjustment.apply_sector_cap: price 欠損時のフォールバック（前日終値・取得原価など）導入による精度改善。
- research/factor_research: さらに多くのファクター実装とユニットテストの拡充。
- モニタリングおよび実行エンジン周りの統合テストと運用監視ルールの調整。

もし実際のコミット履歴やリリース日付が必要であれば、git ログ情報を提供していただければより正確な CHANGELOG を生成します。