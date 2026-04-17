# CHANGELOG

すべての重要な変更を記録します。本ファイルは Keep a Changelog の仕様に準拠します。  

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-17
初回リリース — 基本機能の実装と CLI ツール群を追加。

### 追加 (Added)
- アプリケーション設定読み込みモジュールを実装（kabusys.config）
  - プロジェクトルート（.git または pyproject.toml）を起点に自動で .env/.env.local を読み込む機能を提供。
  - .env パーサは export 形式やシングル／ダブルクォート、エスケープ、インラインコメントを考慮して正しくパース。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると自動ロードを無効化可能。
  - Settings クラスを通じて各種設定値（J-Quants / kabu API / DB パス /監視閾値など）をプロパティで取得可能に。

- 設定ウィザード CLI を追加（kabusys.config_setup）
  - 対話式で .env の初期作成・更新が可能。
  - 多数の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 通知設定等）をサポート。
  - 生成される .env は自動的に説明行付きで書き出され、Git へのコミットを避ける旨の注意を記載。

- 設定検証 CLI を追加（kabusys.validate_config）
  - .env と config/*.yaml の基本的な妥当性検査を実施。
  - 必須環境変数の未設定検出、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在・パースチェック（PyYAML がインストールされていない場合は警告）など。
  - --strict オプションで警告も失敗扱いにして exit(1) にするモードを提供。

- 実行用スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いて実ブローカーまたは MockBroker を切り替え。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて Engine を起動。別スレッドで実行し、データディレクトリ内の stop flag による安全停止を実装。
    - 実行中は高優先度（set_process_priority("high")）で起動。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境に関わらず本番 sqlite_path を使用して監視テーブルを初期化。
    - stop フラグおよび KeyboardInterrupt による安全終了を処理。

- 監視 DB 初期化ユーティリティを追加（monitoring.monitoring_db の初期化を呼び出す形で利用）

- Paper Trading 検証レポート生成ツールを追加（kabusys.tools.paper_verification_report）
  - paper_trading の SQLite DB からシステム稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計してレポート出力。
  - パス／期間指定オプション（--db, --from, --to）を提供。
  - Pass/Fail の閾値（稼働率、注文成立率、送信率、P95 レイテンシ）に基づく判定を行う。

- ポートフォリオ構築関連の純粋関数群を追加（kabusys.portfolio）
  - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - risk_adjustment: セクター集中制限適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
  - position_sizing: 発注株数計算（calc_position_sizes） — risk_based / equal / score の各配分方式、単元株（lot_size）丸め、aggregate cap によるスケールダウンを実装。

- 研究用ファクタ計算モジュールを追加（kabusys.research.factor_research）
  - DuckDB 接続を受け取り prices_daily 等のテーブルから Momentum（1M/3M/6M、MA200乖離）や Volatility（ATR、平均売買代金、出来高比率）を算出する関数を実装。

- プロセス優先度・CPU affinity ユーティリティを追加（kabusys.utils.process_priority）
  - Windows / POSIX（Linux/Mac/FreeBSD）に対応して nice 値または Windows 優先度クラスを設定。失敗時は警告を出力してスキップ。
  - set_cpu_affinity による CPU コアのピン留め機能を提供（権限や OS の制約で失敗する可能性あり）。

- パッケージ初期化とバージョン定義（kabusys.__init__.py: __version__ = "0.1.0"）

### 変更 (Changed)
- （初版のため履歴的変更は無し）

### 修正 (Fixed)
- （初版のため履歴的修正は無し）

### 注意点 / 既知の制限 (Notes)
- .env の自動読み込みはデフォルトで有効（OS 環境変数は優先）。テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化推奨。
- validate_config は PyYAML がインストールされていない環境でも動作するが、YAML パース検証はスキップされ警告が出る。
- position_sizing / apply_sector_cap に関連していくつかの TODO/制限がソース内に明示されている:
  - price が欠損 (0.0) の場合のフォールバック価格（前日終値など）が未実装で、エクスポージャーが過小見積りされる可能性あり。
  - lot_size は現状すべての銘柄で共通とし、将来的に銘柄別の単元対応へ拡張予定。
- process_priority の設定は権限不足や一部 OS で動作しない場合があり、その場合はログに警告が残るだけで処理は継続する設計。
- Paper Trading と本番 DB は明確に分離される（設定次第）。paper_trading モードは MockBroker を使用し、データは paper_trading 用 SQLite に保存される。

### セキュリティ (Security)
- J-Quants リフレッシュトークン（JQUANTS_REFRESH_TOKEN）および kabu API パスワード（KABU_API_PASSWORD）は必須。これらは .env に保存するが、.env を絶対にリポジトリへコミットしないよう注意喚起あり。

## 破壊的変更 (Breaking Changes)
- なし（初回リリース）

---

将来のリリースでは以下を検討:
- 銘柄ごとの lot_size 対応、価格フォールバックロジックの強化、監視周りの監視項目追加、テストカバレッジとドキュメント拡充。