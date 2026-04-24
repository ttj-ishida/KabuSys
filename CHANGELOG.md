CHANGELOG
=========

すべての注目すべき変更はここに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

リリース日付はコードベースのタイムスタンプやコメントから推測して付与しています。

Unreleased
----------

（なし）

0.1.0 - 2026-04-24
-----------------

Added
- 初期リリース: KabuSys 自動売買フレームワークのコア機能を実装。
  - 実行/監視用起動スクリプト
    - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の専用 SQLite（data/paper_trading.db）と本番 DB を分離して運用可能。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する。
  - 設定管理 / ユーティリティ
    - config.py: .env 自動読み込み（プロジェクトルート検出）と堅牢な .env 行パーサを実装。quoted 値のエスケープ、inline コメント処理、export KEY=... 形式に対応。各種設定プロパティ（DB パス、PAPER_FILL_MODE、閾値、env 判定など）を提供。
    - config_setup.py: 対話式 .env 作成ウィザードを実装（項目定義・読み込み・確認・書き込み）。
    - validate_config.py: 起動前設定検証 CLI を実装。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パース（PyYAML 利用時）および本番向けガードチェックを実行。--strict オプションを提供。
  - ロギング・プロセス制御
    - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。コンソール出力は stdout を使用、日次ローテーション（TimedRotatingFileHandler）で 30 日保持。ログディレクトリ作成失敗時にファイル出力をスキップするフォールバックあり。
    - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加。Windows / POSIX(nice) を抽象化。CPU affinity 設定関数も実装。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py: シグナル選択（スコア降順）・等金額配分・スコア加重配分を実装。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を実装。
    - portfolio/position_sizing.py: 各種配分方式（risk_based / equal / score）に基づく株数計算、単元株（lot_size）丸め、aggregate cap に基づくスケーリング等を実装。
    - portfolio/__init__.py で主要関数を公開。
  - リサーチ / ツール
    - research/factor_research.py: ファクター計算モジュールの骨組み（モメンタム、MA200、ATR 等）を実装（calc_momentum など。ファイル末尾に計算用定数等を含む）。
    - tools/paper_verification_report.py: Paper Trading 向け検証レポート生成スクリプトを実装。稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を出力。--from/--to/--db オプションをサポート。

Changed
- デフォルトのログ出力設計
  - stdout を標準出力に使うようにし、cron/task scheduler 等でのリダイレクト運用を考慮。
- .env の自動読み込み動作
  - OS 環境変数を保護するため protected セットを利用して .env.local の上書き挙動を制御。
  - プロジェクトルート検出は .git または pyproject.toml を基準とすることで CWD に依存しない堅牢な設計に。

Fixed / Robustness
- run_monitoring.py: MONITOR_POLL_INTERVAL の不正値に対して警告を出しデフォルトにフォールバックする処理を追加（time.sleep に負の値を渡さないように保護）。
- run_execution.py / run_monitoring.py:
  - 起動時にプロセス優先度を "high" に設定する処理を追加（最初に呼び出すことで実行中リソースの優先度を確保）。権限不足時は警告ログを出すフォールバックあり。
  - 停止フラグ（data/stop_requested.flag）検知による優雅なシャットダウン処理を実装。ExecutionEngine は別スレッドで実行され、停止フラグ検知で engine.stop() を呼び出して終了を試みる。
  - SQLite / DuckDB の接続は finally ブロックで確実にクローズするように改善。
- config._parse_env_line: 引用符付き文字列中のバックスラッシュエスケープや対応する閉じクォートの探索、インラインコメントの無視などを正しく処理するようにした。
- validate_config.py: PyYAML 未インストール時に YAML 検証をスキップして警告を出すようにし、yaml パース失敗時のエラーメッセージを収集するように改善。
- portfolio/position_sizing.py:
  - 投下金額超過時のスケールダウンロジックを追加。残余キャッシュを用いて lot_size 単位で追加配分するフェアな再配分アルゴリズムを実装。
  - 価格欠損時のスキップ処理により例外発生を抑制。

Security
- .env の生成テンプレート（config_setup）が .env を絶対に Git にコミットしないよう注意書きを追加。

Notes / Known limitations
- research/factor_research.py はファクター計算ロジックの骨組みを含むが、完全実装や最適化（スキャン範囲など）は今後の作業対象。
- apply_sector_cap は price_map に 0.0（価格欠損）を与えた場合にエクスポージャーが過少評価される可能性があり、将来的にフォールバック価格（前日終値・取得原価等）の導入を検討中（TODO コメントあり）。
- PAPER_FILL_MODE の有効値は "instant" | "partial" | "never" | "reject" に限定され、無効値は起動時に ValueError を発生させる。

Commit / Release notes（推測）
- このバージョンは初期機能の揃ったアルファ/ベータ相当のリリースと想定されます。CLI（設定ウィザード・設定検証）、監視/実行の起動スクリプト、ポートフォリオ構築・リスク制御・ポジションサイジング、ロギング・プロセスユーティリティ、Paper Trading の検証ツールおよびファクターモジュールの雛形を含みます。

--- 

今後の提案（例）
- factor_research の完全実装およびユニットテスト追加
- ExecutionEngine / BrokerClient の E2E テスト、paper_trading のシミュレーション拡張
- metrics / observability（Prometheus 等）統合、ログ構造化（JSON）オプション
- config の型安全化（dataclass / pydantic）および設定値の単体テスト追加

以上。必要であれば各機能ごとにより詳細な変更点（ファイル単位の差分や想定される CLI 使い方、既知の注意点）を追記します。