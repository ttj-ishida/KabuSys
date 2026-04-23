CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。重要な変更点・追加機能・既知の制約をコードベースから推測してまとめました。

Unreleased
---------
- 継続作業 / 予定
  - research/factor_research.py の実装の続行（ファイル末尾が途中で切れているため、いくつかの計算ルーチンは未完）。
  - 銘柄ごとの単元株（lot_size）を銘柄マスタから取得する機能や、価格欠損時のフォールバック（前日終値等）を position_sizing に追加予定（TODO コメントあり）。
  - テストカバレッジ拡充（DB エラー時の堅牢化、境界値テスト等）。
  - ドキュメント整備（PortfolioConstruction.md 参照箇所の実装注記や CLI の使用例拡充）。

[0.1.0] - 2026-04-23
--------------------
Added
- 基本パッケージ公開
  - パッケージバージョンを設定: kabusys.__version__ = "0.1.0"。
- 設定・環境変数管理
  - Settings クラスを導入して環境変数を型付きで集約（KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH など）。
  - .env/.env.local の自動読み込み機構を実装。OS 環境変数を保護するための上書きルールを実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env のパース強化:
    - export プレフィックスのサポート
    - クォート／エスケープ対応
    - インラインコメントの扱い（クォートあり／なしで挙動を分離）
- 設定ユーティリティ / CLI
  - config_setup.py: 対話式ウィザードで .env を作成・更新するツールを追加（秘密値のマスク表示・デフォルト値・選択肢対応）。
  - validate_config.py: 起動前に .env と config/*.yaml の存在・妥当性を検証する CLI を追加（--strict オプションあり）。PyYAML 未インストール時は YAML 検証をスキップする機能あり。
- 実行／監視プロセス起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定・DB 接続（paper_trading 環境では paper 専用 SQLite を使用）・Broker クライアント生成・ExecutionEngine 起動ループ（停止フラグ対応）。
  - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用。
  - 停止制御ファイル（data/stop_requested.flag, data/execution.pid 等）によるプロセス制御を導入。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定。StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。LOG_DIR/LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: プロセス優先度（high/normal/low）および CPU affinity 設定ユーティリティを追加。Windows/Linux/macOS の差分を吸収し、権限不足や未対応 OS の場合は警告ログを出してスキップ。
- データベース関連
  - duckdb と sqlite3 を併用する設計を採用（duckdb は分析用、sqlite は監視／履歴用）。
  - 監視テーブルの初期化関数 init_monitoring_db（monitoring パッケージ内）を起動時に呼び出してテーブル存在を保証（冪等）。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア降順選定と tie-breaker を実装。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（スコア全て 0.0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限（既存保有のセクター比率が上限を超える場合に新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を実装（未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: risk_based / equal / score の割当方式に対応した株数計算。最大ポジション比率、lot_size による丸め、aggregate cap（利用可能現金を超えた場合のスケールダウン）や remainder による追加配分ロジックを実装。cost_buffer を考慮した保守的見積り対応。
- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 検証レポート生成ツールを追加。稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）を集計して PASS/FAIL 判定（閾値はソース内定義）。
    - DB パスは引数または PAPER_TRADING_SQLITE_PATH 環境変数で指定可能。
- リサーチ
  - research/factor_research.py:
    - ファクター計算の骨子を追加（Momentum/Value/Volatility/Liquidity の計画と所定パラメータ）。DuckDB を用いたデータ参照方針を明記。注: 実装途中部分あり。
- パッケージ初期化
  - kabusys/portfolio/__init__.py, kabusys/tools/__init__.py, kabusys/utils/__init__.py を整備して公開 API を定義。

Changed
- 初期リリースのため「追加」が中心。既存外部仕様との互換性注記は README / ドキュメントで追記予定。

Fixed
- 多数のエラー耐性改善
  - ログディレクトリ作成失敗時にプロセスが停止しないように修正（ファイルハンドラ作成例外を捕捉してコンソール出力にフォールバック）。
  - process_priority / cpu_affinity の権限不足や未実装 API でのクラッシュ防止（警告ログに置換）。
  - .env ファイル読み込みでファイルオープン失敗時に警告を出すようにして起動継続可能に。

Security
- .env は機密情報を含むため Git にコミットしない旨を config_setup.py のヘッダに明示。
- config_setup.py ではシークレット項目をマスク表示して対話（入力プロンプト）できるように実装。

Notes / Known Issues
- factor_research.py の末尾が実装途中で切れているため、ファクター計算の一部機能は未完成です（Unreleased にて対応予定）。
- position_sizing の TODO: 将来的に銘柄別単元を導入する設計拡張が計画されている（現状は全銘柄同一 lot_size を想定）。
- apply_sector_cap は "unknown" セクターに対しては上限制約を適用しない設計（ドメイン上の意図的判断）。価格が 0.0 の場合はエクスポージャーが過小評価される可能性があるため、フォールバック価格ロジックの追加を予定。
- run_monitoring は監視用 DB に常に本番 sqlite_path を使用するため、開発環境での分離が必要な場合は環境変数を調整してください。

ライセンスや追加ドキュメント（使用方法、運用手順、デプロイ手順）は別途整備を推奨します。