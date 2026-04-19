CHANGELOG
=========

すべての重要な変更履歴をここに記載します。本ドキュメントは「Keep a Changelog」形式に準拠しています。

v0.1.0 — 2026-04-19
-------------------

初回リリース。システム全体の起動スクリプト、設定管理、検証ツール、ポートフォリオ構築ロジック、ユーティリティ群、およびペーパートレード検証レポート機能を追加しました。

追加 (Added)
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、ペーパートレード用 SQLite（data/paper_trading.db をデフォルト）へ記録する。停止フラグによる安全停止、PID ファイル管理、スレッドでの実行制御を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用する設計。
- 設定管理
  - config.py: Settings クラスを導入。.env 自動読み込み（プロジェクトルート検出：.git または pyproject.toml を基準）、環境変数の厳密チェック（KABUSYS_ENV / LOG_LEVEL 等）、各種パス・閾値・フラグのプロパティを提供。PAPER_FILL_MODE のバリデーションや paper_sqlite_path などペーパートレード向け設定を含む。
  - config_setup.py: .env の対話式ウィザードを追加。既存 .env 読み込み、選択肢・デフォルト表示、シークレットマスク、保存テンプレート出力をサポート。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の検証、DB パスや config/*.yaml の存在（および PyYAML 利用時はパース検証）を実行。--strict オプションで警告を失敗扱いにできる。
- ペーパートレード検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite を集計して稼働率、注文成功率、送信率、レイテンシ (avg/max/P95) を算出するレポート生成スクリプトを追加。閾値による PASS/FAIL 判定を実装。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）と配分重み計算（等金額 calc_equal_weights、スコア加重 calc_score_weights）を追加。スコアが全て 0 の場合のフォールバックを実装。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を追加。unknown セクターの扱い、レジーム未定義時のフォールバックを定義。
  - portfolio/position_sizing.py: 発注株数決定ロジック calc_position_sizes を追加。allocation_method として "risk_based" / "equal" / "score" をサポートし、単元株（lot_size）丸め、最大ポジション比率、利用可能現金に対するスケーリング（aggregate cap）、cost_buffer（手数料・スリッページ見積り）を考慮した比例配分ロジックを実装。
- ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。 stdout 出力の StreamHandler と日次ローテート（TimedRotatingFileHandler、30日保持）のファイルハンドラをルートロガーに設定。既存ハンドラのクリアにより二重出力を回避、ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみ継続。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度（high/normal/low）設定と CPU affinity 設定を提供。Windows / POSIX の差分を吸収し、psutil の権限不足や未対応 OS 時に安全にフォールバック。
- リサーチ（骨格）
  - research/factor_research.py: ファクター計算モジュール（Momentum, Value, Volatility, Liquidity）を追加（DuckDB 接続を受け、prices_daily / raw_financials テーブル参照の設計）。モメンタム計算関数等の骨格を実装（将来的な拡張想定）。
- パッケージ情報
  - src/kabusys/__init__.py にてバージョン __version__="0.1.0" を設定。

変更 (Changed)
- なし（初回リリースのため該当なし）。ただし、設計上のフォールバック動作やデフォルト値（例: MONITOR_POLL_INTERVAL、LOG_LEVEL、データベースパスなど）を明確化。

修正 (Fixed)
- なし（初回リリース）。実装中に見つかった注意点や TODO はソース内コメントとして記載（例: price が欠損の際の露出評価の過少見積り、将来的な lot_size 拡張など）。

注意事項 / 実装上の挙動
- .env 自動読み込みはプロジェクトルートが特定できない場合や環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定した場合にスキップされる。
- run_monitoring は監視用テーブルの初期化を行い、MONITOR_POLL_INTERVAL が不正な値（非正整数等）の場合はデフォルト 60 秒にフォールバックして警告を出す。
- run_execution は KABUSYS_ENV に応じてペーパートレード DB と本番 DB を完全に分離して使用する設計。
- process_priority は権限不足（psutil.AccessDenied 等）や未対応 OS に対して警告を出しつつ処理を継続するため、必ずしも優先度変更が成功するとは限らない。
- logging_setup はログディレクトリ作成に失敗した場合にファイルハンドラの作成をスキップし、コンソールログのみで継続する設計（cron 等での動作を意識して stdout を使用）。

将来の改善点（TODO）
- portfolio/position_sizing: 銘柄毎の lot_size をサポートするための拡張（stocks マスタへの単元情報追加）。
- risk_adjustment: price 欠損時のフォールバック価格（前日終値や取得原価）の導入。
- research/factor_research: 実際の SQL クエリ実装と単体テスト追加。
- validate_config: config/*.yaml のスキーマ検証（PyYAML 利用）を強化。
- テスト: 各モジュールの単体テスト・統合テストの整備。

---

注: 本 CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートは追加のドメイン知識や開発履歴に基づいて調整してください。