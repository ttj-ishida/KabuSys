# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-04-18

初回リリース。KabuSys のコア機能と起動スクリプト、環境設定・検証ツール、ポートフォリオ構築ロジック、およびユーティリティ群を実装しました。

### 追加
- コアパッケージ
  - パッケージバージョンを設定: `kabusys.__version__ = "0.1.0"`。
- 起動 / 実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。プロセス優先度の設定、高優先度での起動、paper_trading 環境時は本番 DB と切り離した paper_trading 用 SQLite を使用、BrokerClientFactory 経由のブローカークライアント、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、デーモンスレッドでのエンジン実行、停止フラグ監視（data/stop_requested.flag）、PID ファイル処理を実装。
  - run_monitoring.py
    - SystemMonitor を定期ポーリングで実行する監視ループを実装。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番の sqlite_path を使用する設計。
- 環境設定 / 検証
  - config.py
    - .env 自動読み込み（プロジェクトルートの検出: .git / pyproject.toml を基準）、`.env` / `.env.local` の優先順位管理、OS 環境変数保護、豊富なキーアクセス用 `Settings` クラス（各種パス、閾値、フラグなど）、入力値検証（`KABUSYS_ENV` / `LOG_LEVEL` / `PAPER_FILL_MODE` など）を実装。
    - `.env` 行解析は引用符・エスケープ・コメント対応を含む堅牢なパーサを実装。
  - config_setup.py
    - 対話式ウィザードで `.env` を初期作成／更新する CLI を実装。シークレット項目はマスク表示、保存時にテンプレートで出力、保存前に確認プロンプトを表示。
  - validate_config.py
    - 起動前チェック用 CLI を実装。必須環境変数、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パス、config/*.yaml の存在と YAML パース（PyYAML があれば実行）などを検証。`--strict` オプションで警告を失敗扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順・タイブレーク）、等金額配分、スコア加重配分（全スコア 0 の場合は等分にフォールバックして警告）。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（既存ポジションのセクターエクスポージャー計算による候補除外）、市場レジームに応じた投下資金乗数（bull/neutral/bear）。
  - portfolio/position_sizing.py
    - 発注株数決定ロジック（risk_based / equal / score）、単元株丸め、ポジション上限、aggregate cap によるスケールダウンと端数処理（残余キャッシュでの追加配分アルゴリズム）。
- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティ（コンソール stdout と日次ローテートファイルハンドラ）。ログディレクトリ / レベルの解決順を実装し、ディレクトリ作成失敗時はファイル出力を安全にスキップ。
  - utils/process_priority.py
    - プラットフォーム抽象化したプロセス優先度設定（Windows の HIGH_PRIORITY_CLASS / POSIX の nice）と CPU affinity 設定を実装。アクセス権限や未対応環境では安全にフォールバックして警告を出す。
- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均／最大／P95）を算出し、定めた閾値で PASS/FAIL を判定。コマンドライン引数で期間フィルタ／DB パスを指定可能。
- リサーチ
  - research/factor_research.py（実装開始）
    - モメンタム等のファクター計算基盤を実装（DuckDB 経由で prices_daily / raw_financials を参照する設計）。モメンタム指標（1M/3M/6M、MA200 乖離など）の計算関数を実装（ファイル末尾で一部実装途中の箇所あり）。

### 変更
- ロギング
  - コンソール出力は stdout を使用するように統一（cron / スケジューラからのリダイレクトを考慮）。
  - 既にルートロガーにハンドラがある場合は一旦クリアしてから再設定（重複防止）。
- データベース / 監視
  - 監視起動スクリプトは常に Settings の sqlite_path（本番監視 DB）を使用する設計（環境に依存しない監視収集のため）。
  - Execution 起動時は paper_trading 環境なら paper_sqlite_path を使用して本番 DB と完全分離。

### 修正（バグ修正・堅牢性向上）
- 環境変数パーサ（config._parse_env_line）
  - 引用符付き値のバックスラッシュエスケープ対応、内側の引用符の扱い、インラインコメントの取り扱い、`export KEY=val` 形式対応などを追加して .env パースを堅牢化。
- MONITOR_POLL_INTERVAL の取り扱い
  - 不正な値（0 以下や非整数）の場合は警告を出してデフォルト（60 秒）にフォールバックするように変更（time.sleep に渡す際の ValueError 回避）。
- calc_score_weights
  - 全スコアが 0.0 の場合に等金額配分へフォールバックし、警告ログを出すように修正（ゼロ除算回避）。
- position_sizing / risk_adjustment
  - 価格欠損（price が None/0）の場合には該当銘柄をスキップする安全処理を追加。aggregate cap のスケーリング処理と lot 単位での端数処理を実装して総コスト超過時に安定的にスケールダウンするよう改善。
- process_priority / set_cpu_affinity
  - 権限不足や未対応プラットフォームでの例外を捕捉し警告にフォールバックするよう強化。
- logging_setup
  - ログディレクトリ作成に失敗した場合はファイルハンドラを無効化し、コンソール出力のみで継続するよう修正（起動失敗回避）。
- validate_config
  - config/*.yaml の検証は PyYAML が利用可能な場合のみ実行し、未インストール時は警告を出してスキップ。

### 既知の問題 / TODO
- research/factor_research.py の一部（calc_momentum の終端など）がファイル内で途中実装のままになっている箇所があります。追加のファクター計算や最適化は継続作業予定。
- position_sizing の price 欠損時の扱いについては TODO コメントにある通り、将来的に前日終値や取得原価等のフォールバック価格を導入予定。
- 細かなエラーハンドリングや監視メトリクスの追加（SystemMonitor の詳細ログ化など）は今後の改善項目です。

---

（注）この CHANGELOG はコードベースの内容から推測して作成しています。実際の意図や開発履歴と差異がある場合があります。