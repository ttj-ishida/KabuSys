# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
リリースは SemVer に準拠しています。

## [0.1.0] - 2026-04-21

### 追加 (Added)
- 初回公開: KabuSys 自動売買フレームワークの基礎機能を実装しました。
  - パッケージメタ情報
    - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。
  - 起動スクリプト
    - src/kabusys/run_execution.py
      - ExecutionEngine を起動する CLI スクリプトを追加。
      - KABUSYS_ENV に応じて paper_trading 用 DB（data/paper_trading.db）を使用する仕組みを実装。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行う。
      - エンジンは別スレッドで実行され、data/execution.pid を PID ファイルとして使用（pid_file オプション）。
      - プロセス停止はプロジェクトルート下の data/stop_requested.flag を監視して行う（グレースフルシャットダウン）。
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループを起動するスクリプトを追加。
      - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
      - 監視 DB は環境にかかわらず本番 sqlite_path を使用して初期化（init_monitoring_db）。
      - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
  - 設定管理
    - src/kabusys/config.py
      - .env 自動読み込み機能を実装（プロジェクトルートの .env / .env.local を優先読み込み、OS 環境変数は保護）。
      - 高度な .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い等）。
      - Settings クラスを実装し、J-Quants / kabuAPI / LINE / DB / 監視閾値 / システム設定などのプロパティを提供。値検証（env 値や列挙値チェック）を行う。
  - 設定ユーティリティ
    - src/kabusys/config_setup.py
      - 対話式 .env 作成ウィザードを実装。既存 .env の読み込み、項目ごとの説明・デフォルト提示、シークレット項目のマスク表示、保存確認を実装。
      - .env 書き込みフォーマット（コメント付きテンプレート）を用意。
    - src/kabusys/validate_config.py
      - 起動前に .env と config/*.yaml を検証する CLI を実装（--strict オプションで警告を FAIL 扱いにできる）。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、PyYAML がない場合のスキップ、KABUSYS_ENV=live 時の追加ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
  - ロギング・プロセス管理ユーティリティ
    - src/kabusys/utils/logging_setup.py
      - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定する汎用ユーティリティを追加。
      - LOG_LEVEL / LOG_DIR の解決順を定義し、ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみ継続。
    - src/kabusys/utils/process_priority.py
      - プラットフォーム差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。Windows と POSIX（Linux/Mac/FreeBSD）をサポート。psutil を利用し失敗時は警告でフォールバック。
      - CPU affinity を最初の N コアに固定する関数も提供（設定失敗時は警告でスキップ）。
  - ポートフォリオ構築関連（純粋関数群）
    - src/kabusys/portfolio/portfolio_builder.py
      - BUY シグナルから候補選定（スコア降順・同点タイブレーク）、等金額配分、スコア重み配分を実装（score が全て 0 の場合は等配分にフォールバック）。
    - src/kabusys/portfolio/risk_adjustment.py
      - セクター集中制限（apply_sector_cap）を実装。既存ポジションのセクター別エクスポージャを計算し、上限超過セクターの新規候補を除外。
      - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear; 未知レジームはフォールバックで 1.0）。
    - src/kabusys/portfolio/position_sizing.py
      - 株数決定ロジックを実装。allocation_method（risk_based / equal / score）に対応。損切り率・risk_pct に基づく risk_based、単元株（lot_size）丸め、1銘柄上限・合計投資上限（available_cash）に対するスケーリング（端数の再配分）を実装。コストバッファを考慮した保守的見積りも可能。
    - src/kabusys/portfolio/__init__.py で上述関数群を公開。
  - Research / ファクター計算（基礎）
    - src/kabusys/research/factor_research.py
      - Momentum / Value / Volatility / Liquidity 指標計算の方針と定数定義を追加。DuckDB を用いた prices_daily / raw_financials 参照での計算設計を開始（ファイル冒頭に定数と calc_momentum の骨組みを実装、詳細実装は継続）。
  - ツール
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading の検証レポート生成ツールを実装。稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL を判定する。しきい値はコード内で定義（稼働率 99% など）。--from / --to / --db オプションに対応。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- .env 読み込み失敗時に警告を出すようにして、例外でアプリをクラッシュさせない設計に変更（config._load_env_file）。
- MONITOR_POLL_INTERVAL の不正値に対して警告を出しデフォルトにフォールバックする仕様を run_monitoring に追加（ユーザ操作ミスに対する堅牢化）。
- logging_setup: 既にハンドラが設定されている場合、一度 flush/close してから削除することで二重ハンドラ設定を防止。

### 注意事項 (Notes)
- .env 自動ロードはデフォルトで有効。テストや特殊用途で無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 設定の検証・ウィザード（validate_config / config_setup）を使って本番（KABUSYS_ENV=live）での設定ミスを事前に検出することを推奨します。
- run_monitoring は監視用 DB（sqlite_path）を環境にかかわらず本番の sqlite_path を使って初期化します。Paper Trading の評価用 DB は run_execution 側で紙トレード用 DB を使う設計です。
- process_priority と CPU affinity の設定は権限やプラットフォームによって失敗する場合があり、その場合は警告を出して処理を継続します（安全志向）。
- research/factor_research.py の一部（calc_momentum 以降）は実装継続中のため、まだ未完成の関数が含まれる可能性があります。

### セキュリティ (Security)
- なし

---

今後の予定（例）
- factor_research の完全実装（各ファクター計算ロジックの完成・テスト）
- ExecutionEngine / RiskManager の単体テスト強化とモックブローカーの拡張
- ロギングおよび監視指標のメトリクス出力（Prometheus 等）対応検討

（必要であれば、コミット履歴や差分に基づきさらに細かいリリースノートを生成します。どの粒度がよいか教えてください。）