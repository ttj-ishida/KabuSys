# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

全てのリリースはセマンティックバージョニングに従います。  

[Unreleased]: https://example.com/compare/HEAD
[0.1.0]: https://example.com/compare/v0.0.0...v0.1.0

## [0.1.0] - 2026-04-18

### 追加 (Added)
- 基本アプリケーションパッケージを追加
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）。
- 起動スクリプト
  - run_execution.py: 実行エンジン起動スクリプトを追加。プロセス優先度を上げ、SQLite / DuckDB に接続し、Broker クライアント・OrderManager・RiskManager 等を組み立てて ExecutionEngine を起動する。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（data/paper_trading.db をデフォルト）を使用し、MockBrokerClient を利用して本番 DB と分離する挙動をサポート（停止フラグ・PID 書き込み対応）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用する。停止はプロジェクト直下の data/stop_requested.flag ファイルで検知。
- 設定管理
  - config.py: .env 自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）を実装。.env / .env.local の読み込み順序・オーバーライド保護（OS 環境変数保護）を実装。複雑な .env パース（export プレフィックス、クォート文字列のエスケープ、インラインコメント扱い）に対応。Settings クラスでアプリ設定をプロパティとして提供（各種パス・閾値・フラグ・紙トレード設定など）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
- 設定ユーティリティ CLI
  - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援する CLI を実装。主要な環境変数項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE トークン、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）を対話的に設定し .env を書き出す。
  - validate_config.py: 起動前に環境変数・config/*.yaml の基本チェックを行う CLI を実装。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML の存在とパース確認（PyYAML が存在しない場合はスキップ）、本番時の追加ガードチェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START など）。--strict オプションを追加（警告を FAIL 扱いにする）。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: ルートロガーに対し StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日分保持）を設定するユーティリティを実装。ログレベル・ログディレクトリは引数・環境変数・デフォルトの順で解決。ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソールのみで継続。
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを実装（Windows の priority class / POSIX の nice 値を使用）。例外時は警告を出してスキップ。CPU affinity を最初の N コアに固定する set_cpu_affinity() も実装。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全ゼロ時のフォールバックとログ出力を含む。
  - portfolio/risk_adjustment.py: セクター集中制限を行う apply_sector_cap() と市場レジームに応じた投資乗数 calc_regime_multiplier() を実装。regime の未定義値は警告してフォールバック。
  - portfolio/position_sizing.py: 株数計算ロジックを実装。allocation_method として "risk_based"/"equal"/"score" をサポート。単元株（lot_size）丸め、1 銘柄上限・aggregate cap のスケーリング、cost_buffer（手数料・スリッページ考慮）による保守的コスト見積もり、残余キャッシュを用いた端数配分の安定化ロジックを実装。
  - portfolio/__init__.py で上記関数を公開。
- リサーチ（ファクター計算）
  - research/factor_research.py: DuckDB 接続を受けてファクター（モメンタム、移動平均乖離、ATR、流動性等）を計算する設計を実装。モメンタム計算関数 calc_momentum() の骨組みを含む（営業日ベースの窓長やスキャン範囲の定数を定義）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 向け検証レポート生成ツールを追加。Paper Trading 用 SQLite（環境変数 PAPER_TRADING_SQLITE_PATH または --db）から各種指標（稼働率 / 注文成功率 / 送信率 / リスク却下数 / 平均・P95 レイテンシ）を集計し、PASS/FAIL 判定（しきい値はソース内定義）で結果を表示。P95 計算や日付フィルタ（ISO8601 UTC 変換）を実装。
- DB 初期化ユーティリティ
  - monitoring/monitoring_db.py （起動箇所から参照）を通じて監視テーブル初期化処理が呼ばれるようになっている（init_monitoring_db を利用）。
- Execution / Monitoring の停止制御
  - 起動済みプロセスの停止はプロジェクト data ディレクトリ内の stop_requested.flag（および実行用の execution.pid）ファイルで制御する仕組みを導入。

### 変更 (Changed)
- ロギングの設計方針
  - StreamHandler を stderr ではなく stdout に向けるように変更（cron / Task Scheduler でのリダイレクト運用を考慮）。
- .env 読み込みの挙動明確化
  - OS 環境変数を保護する protected 機構を導入し、.env.local は既存 OS 環境を上書きできるが protected によって安全に扱う。

### 修正 (Fixed)
- （現段階のスナップショットでは明示的なバグ修正履歴は無し。ただし各モジュールは例外処理やフォールバックを多く取り入れて堅牢性を高めている。）

### 既知の問題 (Known issues)
- research/factor_research.py の一部実装が途中で終了している（ソース末尾が切れているため、完全なファクター計算実装は未完）。
- position_sizing の price 欠損時の扱いに TODO コメントあり（価格欠損時にエクスポージャーが過少見積りされる可能性）。
- ログディレクトリ作成失敗時はファイルローテーションが無効化されるが警告のみで継続する設計（意図的）。運用時にログ書き込み権限を確認すること。

### セキュリティ (Security)
- シークレットに関する考慮:
  - config_setup の対話入力で secret 項目（トークン・パスワード）はマスク表示するが .env は平文で保存されるため、.env を絶対に Git にコミットしない旨の注意をドキュメント内に明示。

---

注: 上記はリポジトリ内のソースコードおよび docstring / コメントから推測してまとめた CHANGELOG です。必要に応じて実際のコミット履歴やリリースノートと照合のうえ、文言を調整してください。