# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。  
このプロジェクトのバージョンは src/kabusys/__init__.py の __version__ に一致します。

## [0.1.0] - 2026-04-27

### 追加 (Added)
- 実運用向けの起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するメインスクリプト。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、本番 DB と分離された data/paper_trading.db を利用する。
    - 起動時にブローカーから利用可能現金・保有ポジションを取得して起動時総資産を計算し、リスク設定（config/risk_config.yaml）を初期資産に基づいて読み込む。
    - 起動時にリコンシリエーションを実行し、Execution Startup Summary（サマリ生成・表示・保存）を行う。
    - デーモンスレッドでエンジンを実行し、data/stop_requested.flag により安全に停止可能。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
    - 停止フラグ（data/stop_requested.flag）検出でループを終了。
  - run_pre_market_report.py
    - Pre-Market Report の CLI。--save / --json オプションに対応。
    - DuckDB は read_only モードで接続。SQLite は URI read-only 接続を利用してレポートを作成。
- 設定管理 / ユーティリティ
  - src/kabusys/config.py
    - .env の自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順序と上書き保護（OS環境変数保護）に対応。
    - 複数の設定プロパティを提供（DB パス、PID/kill フラグパス、モニタ閾値、paper_trading 用設定など）。
    - PAPER_FILL_MODE（"instant"|"partial"|"never"|"reject"）などの検証ロジックを実装。
  - src/kabusys/config_setup.py
    - 対話式 .env 作成・更新ウィザード。
    - デフォルトや選択肢、シークレットマスク表示等に対応し .env を生成。
  - src/kabusys/validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI。
    - --strict オプションで警告を失敗扱いにできる。
    - 本番環境向けのガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の注意喚起など）を実装。
- レポート / 運用ツール
  - src/kabusys/operations/execution_startup_report.py
    - リコンシリエーション結果から Execution Startup Summary を生成・整形・保存する機能を提供（JSON / CLI / Markdown）。
    - READY / READY_WITH_WARNINGS / BLOCKED の判定ロジックを実装。
  - src/kabusys/operations/night_batch_report.py
    - 夜間バッチ結果のサマリ生成モジュール（ジョブ結果・更新件数・翌営業日のサマリを扱うデータモデルと判定ロジックを実装）。
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプト（期間指定 --from/--to, DB 指定 --db に対応）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL を判定するしきい値を実装（デフォルト閾値: 稼働率 99%、成立率 90% 等）。
    - P95 計算や各種 SQL クエリを用いた統計取得ロジックを実装。

### 変更 (Changed)
- DB 周りの扱いを明確化
  - 実行（execution）と監視（monitoring）で DB の扱いを分離。
    - paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離するように変更。
  - run_pre_market_report は DuckDB を読み取り専用で接続し、SQLite も read-only モードで接続するように変更。
- ログ / プロセス制御
  - 起動時にセットする共通処理として setup_logging と set_process_priority("high") を導入し、実行スクリプトで適用。
  - PID ファイル・停止フラグ（stop_requested.flag）を用いた外部制御に対応。
- .env パーサーの堅牢化
  - _parse_env_line にてクォート付き値のエスケープ処理やインラインコメント処理、export KEY=val 形式をサポート。
  - 自動読み込みの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト等で利用可能）。
- リスク設定の厳格化
  - _load_risk_config（run_execution.py）で config/risk_config.yaml の必須キー検証、値の型変換、および範囲チェックを実施（0<値<=1, 整数は >=1 など）。
  - max_position_pct と max_utilization の関係チェック（max_position_pct <= max_utilization）。
- レポートの保存場所と形式を標準化
  - execution_startup_report.save_report により artifacts/execution_startup/{startup_date}/ に summary.json, report.md, warnings.json を出力するように実装。

### 修正 (Fixed)
- 例外処理と堅牢性の向上
  - run_monitoring.py のポーリングループで monitor.check_once() の例外をキャッチしてログ出力し、次回ポーリングまで待機するように変更（監視の高可用性を確保）。
  - run_execution.py のリポジトリ/コンポーネント初期化中に発生する例外やファイル欠如（risk_config.yaml 未存在、YAML パースエラー）に対して明示的なエラーメッセージを出すように改善。
  - config._load_env_file は読み込みエラー時に警告を出し失敗してもプロセスを継続する。
- CLI の終了コード設計
  - run_pre_market_report はレポートが BLOCKED の場合は非ゼロ終了コード（1）を返すようにした。

### 既知の制限 / 注意事項 (Known issues / Notes)
- night_batch_report.py のファイル末尾が途中で終わっている可能性があり（コードスニペットでの切れ）、最終的なビルド・保存ロジックの確認が必要です。実装を取り込む際は該当モジュールの完全性を確認してください。
- 一部モジュールは外部ライブラリ（PyYAML, duckdb）に依存します。validate_config では PyYAML が未インストールの場合に YAML 内容検証をスキップしますが、実行環境では必要ライブラリをインストールしてください。
- .env ファイルは機密情報を含むため、config_setup での注意書きにもある通り絶対に Git にコミットしないでください。

---

今後の変更は Unreleased セクションに記載予定です。必要であれば、各追加機能・挙動についてより詳しい変更点（例: 各 CLI の出力例、環境変数一覧、SQL スキーマの変更点など）を追記します。