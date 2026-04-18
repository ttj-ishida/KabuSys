# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-18

初回リリース。本リリースでは自動売買システムの起動スクリプト、設定管理、検証ツール、ポートフォリオ構築ロジック、各種ユーティリティ、および Paper Trading 検証用スクリプトを含む基盤機能を導入します。

### 追加 (Added)
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するメインスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory を使用して実ブローカー／モックを切替可能。
    - エンジンは別スレッドで実行し、data/stop_requested.flag の検知で安全停止。
    - 起動時にプロセス優先度を "high" に設定し、PID ファイルを書き込む仕組みを備える。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を利用する仕様（監視データは一元管理）。
    - data/stop_requested.flag による停止、例外を捕捉して次ポーリングまで待機する堅牢化。

- 設定管理
  - src/kabusys/config.py
    - Settings クラスを導入し、環境変数を型安全に取得する API を提供。
    - .env 自動読み込み機能を導入（プロジェクトルート検出: .git または pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
    - .env の行パーサは export プレフィックス、クォート文字、バックスラッシュエスケープ、インラインコメントをサポート。
    - 各種設定（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID ファイル等）、閾値やフラグに対するプロパティを提供。
    - PAPER_FILL_MODE 等の列挙的な設定値検証を実装。

- 設定ユーティリティ・検証
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - シークレット入力はマスク表示、確認プロンプト、.env のテンプレート出力を提供。
  - validate_config.py
    - 起動前チェック CLI を追加（--strict オプションで警告を FAIL 扱いにできる）。
    - 必須環境変数チェック、KABUSYS_ENV・LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML があればパースも実施）、本番環境用の追加ガードを実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等を算出し PASS/FAIL 判定を出力。
    - --from / --to / --db オプションをサポート。デフォルト DB は data/paper_trading.db。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（スコア降順・タイブレークロジック）および等金額・スコア加重の重み計算を提供。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
    - unknown セクターの扱いやレジームマップ（bull/neutral/bear）を定義。
  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap のスケーリング、cost_buffer を考慮した保守的計算、残差に基づく追加配分ロジックを実装。
    - 価格欠損時のスキップ、current_positions に対する差分発注を返す設計。

- ユーティリティ
  - utils/logging_setup.py
    - setup_logging を導入。標準出力（stdout）用 StreamHandler と 日次ローテーションの TimedRotatingFileHandler（30日保持）をルートロガーに設定。
    - 既存ハンドラをクリアして二重登録を防止。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py
    - set_process_priority と set_cpu_affinity を提供。Windows と POSIX の差分を吸収し psutil 経由で優先度/CPU affinity を設定。権限不足や未対応環境では警告を出してスキップする。

- リサーチ（未完）
  - research/factor_research.py
    - ファクター計算モジュール（モメンタム / MA / ATR / ボリューム等）の骨子を追加。DuckDB を用いた prices_daily/raw_financials 参照設計を採用。モメンタム計算関数の実装開始（ファイル末尾は未完）。

- パッケージ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

### 変更 (Changed)
- ロギングの挙動
  - コンソール出力は stderr ではなく stdout を使用するように変更（cron/スケジューラとの相性向上）。
  - ログレベルの解決順を明文化（引数 > 環境変数 LOG_LEVEL > デフォルト INFO）。
- .env の自動読み込みロジック改善
  - プロジェクトルートを __file__ の親階層から探索する方式に変更し、配布環境でも CWD に依存せずに動作するように改善。
  - OS 環境変数は保護（protected）して .env.local の上書きを制御。

### 修正 (Fixed)
- MONITOR_POLL_INTERVAL の不正値ハンドリング
  - run_monitoring のポーリング間隔取得で 0 以下や非数値を検知した場合、デフォルト（60 秒）にフォールバックして警告ログを出力するように改善。
- ログハンドラ二重登録回避
  - setup_logging が既存ハンドラを閉じてから削除するようにして、複数回呼び出した際の重複出力を防止。
- セクター上限ロジックの整合性
  - apply_sector_cap は "unknown" セクターに対しては上限適用を行わない（除外しない）仕様を明確化。
- position_sizing のスケーリング
  - aggregate cap 超過時のスケールダウン処理と lot_size 単位での再配分アルゴリズムを追加し、端数処理の再現性と安全弁を確保。

### ドキュメント・注記 (Notes)
- config_setup.py と validate_config.py は起動前に環境設定を整えるための CLI を提供。特に本番環境（KABUSYS_ENV=live）では LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値に注意するよう警告を出す。
- paper_verification_report.py は複数の指標（稼働率 / 成功率 / 送信率 / P95 レイテンシ）に対して閾値を定義しており、簡易的な PASS/FAIL 判定を行うユーティリティとして利用可能。
- research/factor_research.py は計算ロジックの骨子を導入済みだが、完全実装にはさらなるテストと DuckDB 側のスキーマ確認が必要（ファイル末尾が未完）。
- position_sizing と apply_sector_cap 内で一部 TODO（価格取得のフォールバック、銘柄別 lot_size 対応等）が残っている。実運用前にこれらの拡張を検討してください。

### 既知の制限 (Known issues)
- process_priority / set_cpu_affinity は権限により失敗する可能性があり、その場合は警告ログでスキップするだけで継続します。必要に応じて運用側で十分な権限を付与してください。
- logging_setup のファイルハンドラ作成でディレクトリ作成に失敗した場合、ファイル出力は無効化されます（stdout は継続）。ログディレクトリの権限等に注意してください。
- research/factor_research の一部実装が未完。ファクター計算の完全動作確認とテストが必要です。

---

今後の予定（例）
- research/factor_research.py の完全実装と単体テスト追加
- strategy モジュールの信号生成・バックテスト用ユーティリティ追加
- 各コンポーネントのユニットテストおよび CI 設定の導入

（注）本 CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のリリースノート作成時にはコミット履歴・変更 PR 等を参照して正確な差分を記載してください。