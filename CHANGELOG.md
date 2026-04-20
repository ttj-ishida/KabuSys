KEEP A CHANGELOG
すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従います。  

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
---------
- （現在のコード状態は 0.1.0 リリース相当です。将来の変更はここに追記してください。）

0.1.0 - 2026-04-20
-----------------
概要:
初期公開リリース。本リリースでは日本株自動売買システム KabuSys のコアユーティリティ、実行・監視エントリポイント、ポートフォリオ構築ロジック、設定管理ツールおよび検証・レポートツールを含みます。

Added
- 基本モジュール
  - kabusys パッケージ初期化（__version__ = 0.1.0）。
- 実行・監視用起動スクリプト
  - run_execution.py：ExecutionEngine を起動する CLI スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、Broker クライアント生成、OrderManager / RiskManager / Reconciler の組み立て、スレッドでのセッション実行、停止フラグ検出による安全停止に対応。
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検出時にループを終了。
- 環境・設定管理
  - config.py：Settings クラスを追加。.env/.env.local の自動読み込み（プロジェクトルート検出に基づく）、必須/任意設定の取得メソッド、各種環境変数（DB パス、KABUSYS_ENV、ログレベル、ペーパートレード用 DB パス、PAPER_FILL_MODE 等）を提供。値検証（有効値チェック）と簡易フォールバック実装あり。
  - config_setup.py：対話式ウィザードで .env を生成/更新する CLI を追加。秘密値はマスク表示、既存値の再利用、保存時のテンプレート生成に対応。
  - validate_config.py：起動前の設定検証 CLI を追加（必須環境変数の確認、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パースチェック、live 環境向けガード）。--strict オプションで警告も失敗扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py：setup_logging() を提供。コンソール(stdout) と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。LOG_DIR / LOG_LEVEL に基づく設定。ログディレクトリ作成失敗時はファイル出力をスキップし警告を出す。
  - utils/process_priority.py：set_process_priority()/set_cpu_affinity() を追加。Windows/Linux/macOS の差分を吸収してプロセス優先度・CPU affinity を設定。権限不足等は安全にスキップして警告を出す。
- ポートフォリオ構築ロジック（純粋関数）
  - portfolio/portfolio_builder.py：候補選定（select_candidates）・等重（calc_equal_weights）・スコア加重（calc_score_weights）を実装。スコアが全て 0 の場合のフォールバックを含む。
  - portfolio/risk_adjustment.py：セクター集中制限の適用（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームでのフォールバックと警告あり。
  - portfolio/position_sizing.py：複数の配分方式（risk_based/equal/score）に基づく株数決定、単元株丸め（lot_size）、最大ポジション・投下上限、コストバッファを考慮した aggregate cap によるスケールダウンなどのロジックを実装。残差処理により余りキャッシュでの追加配分を行う。
- Paper Trading 分離設計
  - 実行エンジンは KABUSYS_ENV=paper_trading 時に MockBrokerClient を使用し、専用の PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録することで本番 DB と完全分離。
- モニタリング DB 初期化
  - monitoring_db 初期化呼び出しを run_execution/run_monitoring から行い、監視テーブルの存在を冪等的に保証。
- レポートツール
  - tools/paper_verification_report.py：Paper Trading 用検証レポート生成ツールを追加。期間フィルタ対応、稼働率・注文成功率・送信率・API レイテンシ（平均/最大/P95）・リスク却下数の集計と基準値による PASS/FAIL 判定を出力。P95 の計算、レポート閾値（稼働率 99% 等）を定義。
- 研究モジュール（骨格）
  - research/factor_research.py：DuckDB 接続を受けてモメンタム等のファクターを計算する設計を追加（モジュールと定数群、calc_momentum の実装骨格）。prices_daily / raw_financials の参照設計。

Changed
- ログ出力の標準化
  - StreamHandler は stdout を使用（stderr ではない）。これは cron/task scheduler でのリダイレクト運用を想定した設計意図によるもの。
- .env 読み込みの挙動
  - 自動ロード順序を OS 環境変数 > .env.local > .env と明確化。OS 環境変数は保護され、.env.local は上書き可能だが保護されたキーは上書きされないように実装。

Fixed / Improved
- .env パーシング強化
  - export キーワード対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い（クォートあり/なしでの差分）などを考慮した堅牢なパーサを実装。
- 設定検証の利便性向上
  - validate_config による事前チェックで設定ミスやプレースホルダ値（例: 値が "your_value" や "_here"）を検出して警告/エラーを出すようにした。
- プロセス優先度/affinity の安全ハンドリング
  - 権限不足やプラットフォーム非対応時に例外を握りつぶして警告を出すようにし、起動失敗に繋がらないように改善。
- ポジションサイズ算出の堅牢化
  - 価格欠損や 0 値の取り扱いでログを出しスキップするようにし、aggregate cap のスケーリングと lot_size 単位への丸めを厳密化。残差処理で再現性ある順序付けを行う実装に改良。

Security
- 秘密情報取り扱い
  - config_setup の対話ではシークレット項目をマスク表示。README 等で .env を絶対に Git にコミットしない旨をテンプレートに明記。

Notes / Known limitations
- research.calc_momentum は骨格を含むが（ファイル末尾で）実装が途中（長大な関数の一部が未完）です。研究用ファクター計算の完全実装は今後のリリースで追加予定です。
- 一部のファイル/機能は外部依存（psutil、duckdb、PyYAML 等）に依存します。PyYAML 未インストール時は YAML 検証がスキップされ、該当旨の警告が出ます。
- run_monitoring は Monitoring 用の DB（settings.sqlite_path）を環境にかかわらず本番パスで使用する旨の挙動がコード上に明記されています。運用時は意図した DB パス設定に注意してください。
- PAPER_FILL_MODE の値検証（instant/partial/never/reject）を Settings で行うため、無効値は起動時に ValueError を発生させます。

今後の予定（提案）
- research/factor_research の完全実装（Momentum/Value/Volatility/Liquidity の SQL 最適化）
- execution/engine の詳細なユニットテスト追加（リスクマネージャやスケールダウン挙動の網羅）
- モニタリングのアラート連携（LINE 通知の実装・テスト）
- 単体銘柄ごとの lot_size マスタ対応（stocks マスタに単元情報を持たせる拡張）

（以上）