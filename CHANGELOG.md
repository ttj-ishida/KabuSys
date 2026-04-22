# CHANGELOG.md

すべての変更は「Keep a Changelog」形式に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- 今後の変更予定や作業中の改善点をここに記載します。

## [0.1.0] - 2026-04-22
初回リリース。以下の主要機能・実装を含みます。

### 追加 (Added)
- パッケージメタ情報
  - バージョン情報を `kabusys.__version__ = "0.1.0"` として追加。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境（KABUSYS_ENV）に関わらず本番用 sqlite_path を使用。
    - 停止制御用の stop_requested.flag を監視してループを終了。
    - 起動時にプロセス優先度を "high" に設定。
    - SQLite / DuckDB 接続の初期化（init_monitoring_db 呼び出し）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用専用 SQLite（デフォルト: data/paper_trading.db）に記録して本番 DB と分離。
    - プロセス優先度を "high" に設定。
    - stop_requested.flag による起動抑止と実行時停止制御（execution.pid を利用）。
    - ExecutionEngine をスレッドで起動し監視するループを実装。

- 設定管理
  - config.py
    - .env の自動ロード機能（.env, .env.local）をプロジェクトルート（.git または pyproject.toml を基準）から行う実装。
    - .env パースの堅牢化（export 形式、クォート内エスケープ、インラインコメントの扱い等）。
    - Settings クラスを実装し、J-Quants / kabuAPI / LINE / DB / 監視閾値 / システム設定をプロパティとして提供。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）や PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START 等の環境変数サポート。
    - settings = Settings() をモジュールスコープで提供。

- 設定関連 CLI
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - 秘匿入力のマスク表示、既存 .env の読み込み・再利用、.env ファイルテンプレート生成機能。
    - デフォルト値、選択肢、説明文を含む複数の設定項目を用意。
  - validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ存在チェック、YAML パース検査（PyYAML がある場合）を実施。
    - --strict オプションで警告も失敗扱いにできる。

- 監視・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを SQLite（デフォルト: data/paper_trading.db）から集計してレポート出力。
    - 各指標の閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義して PASS/FAIL 判定を行う。
    - 日付フィルタ（--from / --to）、--db オプションをサポート。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定 (select_candidates)、等比率配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコアが全て 0 の場合のフォールバック処理（警告 -> 等金額配分）。
  - portfolio/risk_adjustment.py
    - セクター集中を抑制する apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を実装。
    - 未知レジーム／unknown セクターのフォールバック挙動を定義。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method = risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-stock 上限・aggregate cap、available_cash によるスケールダウン、cost_buffer の考慮、端数分配アルゴリズムを実装。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ロギング設定ユーティリティを追加。
    - stdout への StreamHandler と、日次ローテーション（TimedRotatingFileHandler）で logs/<app_name>.log に出力（デフォルト 30 日保持）。
    - ログレベルの解決順（引数 > 環境変数 LOG_LEVEL > デフォルト INFO）。
    - ログディレクトリ作成失敗時のフォールバック（コンソールのみ）を考慮。
  - utils/process_priority.py
    - クロスプラットフォームのプロセス優先度設定と CPU affinity 設定を追加（psutil 使用）。
    - Windows / POSIX (Linux/Mac/FreeBSD) を吸収し、権限不足や未対応 OS の場合は警告を出してスキップ。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。

- データリサーチ
  - research/factor_research.py（初期実装）
    - ファクター計算モジュールの骨子を追加（Momentum, Value, Volatility, Liquidity を想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を用いて計算する方針と定数を定義。
    - calc_momentum の実装開始（処理方針・定数定義あり、詳細な実装は継続予定）。

- パッケージ組織
  - kabusys.portfolio パッケージエクスポートを追加（select_candidates 等を __all__ で公開）。
  - tools パッケージの雛型 __init__.py を追加。

### 変更 (Changed)
- なし（初回リリースのため）。

### 修正 (Fixed)
- なし（初回リリースのため）。

### 注意点 / 既知の制約 (Notes / Known issues)
- factor_research.calc_momentum に関してはファイルの末尾で実装が途中に見られる（開発継続の余地あり）。
- apply_sector_cap の価格欠損（price == 0.0）の場合、現状では露出が過小見積りされうる旨の TODO コメントあり（将来的なフォールバック価格導入が検討対象）。
- process_priority や set_cpu_affinity は権限やプラットフォームにより一部機能が制限される可能性がある（警告を出してスキップする設計）。

### セキュリティ (Security)
- 現状特記事項なし。

---

（注）この CHANGELOG はリポジトリ内のソースコードの実装内容から推測して作成しています。実装の意図やリリース日等は実際の開発履歴に合わせて適宜修正してください。