CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。  
リリース日はコードベースから推測した日付を付与しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-18
--------------------

Added
- 初期リリース: KabuSys 自動売買システムの基本コンポーネントを追加。
- 起動スクリプト:
  - run_execution.py: 実行エンジン (ExecutionEngine) の起動用スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（既定: data/paper_trading.db）を使用し、本番 DB と分離。  
    - BrokerClientFactory を介してブローカークライアントを生成（Mock を含む実装を想定）。  
    - エンジンはスレッドで実行され、 data/stop_requested.flag により安全に停止可能。PID ファイル機能あり（data/execution.pid）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視用は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する仕様。
- 設定管理:
  - config.py: 環境変数 / .env 自動読み込みと Settings クラスを実装。  
    - プロジェクトルート検出（.git または pyproject.toml）に基づく .env 自動ロード。  
    - .env / .env.local の読み込み順序、OS 環境変数を保護する仕組み、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。  
    - 各種設定プロパティ（DB パス、API トークン、KABUSYS_ENV 検証、PAPER_FILL_MODE 検証等）を提供。
  - config_setup.py: 対話式 .env ウィザードを追加。  
    - シークレット項目をマスク表示、既存 .env の読み込みと更新、.env のテンプレート書き出し機能あり。CLI: python -m kabusys.config_setup
  - validate_config.py: 起動前設定検証 CLI を追加。  
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在確認（PyYAML が無ければ検証をスキップ）など。  
    - --strict により警告を FAIL 扱いにできる。CLI: python -m kabusys.validate_config
- ロギングユーティリティ:
  - utils/logging_setup.py: 統一ロギング設定を提供。  
    - コンソール出力は stdout、ファイル出力は日次ローテーション（TimedRotatingFileHandler）で 30 日保持。  
    - LOG_LEVEL / LOG_DIR / 引数で上書き可能。ログハンドラ二重登録防止のため既存ハンドラをクリア。ディレクトリ作成失敗時はファイル出力をスキップし警告。
- プロセス優先度ユーティリティ:
  - utils/process_priority.py: プラットフォーム差を吸収する優先度設定機能を追加。  
    - Windows（HIGH/NORMAL/IDLE）と POSIX（nice 値）をサポート。AccessDenied 等は警告してスキップ。CPU affinity 設定関数も提供。
- ポートフォリオ構築:
  - portfolio/portfolio_builder.py: 候補選定と重み計算（等金額・スコア加重）を追加。  
    - select_candidates: score 降順、同点は signal_rank でタイブレーク。  
    - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py: セクター集中制限とレジーム乗数を追加。  
    - apply_sector_cap: 既存ポジションからセクター別エクスポージャーを計算し上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。  
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に対する乗数を返す（未知レジームは警告の上 1.0 フォールバック）。
  - portfolio/position_sizing.py: 株数決定ロジックを追加。  
    - allocation_method = "risk_based" / "equal" / "score" をサポート。  
    - lot_size（単元株）で丸め、max_position_pct（1 銘柄上限）、max_utilization（投下上限）、cost_buffer（手数料・スリッページ見積）を考慮した aggregate cap スケーリングを実装。  
    - リスクベース方式では stop_loss_pct と risk_pct に基づく株数算出。価格欠損時のスキップ等の安全弁あり。
- 監視・検証ツール:
  - tools/paper_verification_report.py: ペーパートレード運用の検証レポート生成スクリプトを追加。  
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ 等。閾値（デフォルト）を定め PASS/FAIL 判定を出力。  
    - 日付フィルタ、DB パス解決（オプション --db / 環境変数）をサポート。CLI 実行例を README 的に注記。
- 研究用ファクター計算（基礎）:
  - research/factor_research.py: モメンタム等ファクター計算の基礎を導入（DuckDB 経由で prices_daily 等を参照する設計）。  
    - モメンタム・MA200・ATR 等の計算を設計（関数 calc_momentum 等、計算に必要な窓幅定数を定義）。
- パッケージ情報:
  - __init__.py にてバージョンを 0.1.0 として定義。

Changed
- なし（初回公開のためすべて追加扱い）

Fixed
- なし（初回公開）

Notes / 実装上の注意
- .env 読み込み:
  - .env のパースはクォート内のエスケープや行末コメント処理に対応。export KEY=val 形式も許容。OS 環境変数は保護され、.env.local は .env より優先して上書きされる。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化可能（テスト用途など）。
- 設定バリデーション:
  - validate_config は PyYAML がインストールされていない環境でも動作し、YAML パースチェックをスキップする旨を警告する。
- ログ:
  - ログは標準出力（stdout）に出力されるため cron やスケジューラ環境でのリダイレクト運用が容易。ファイルローテーションは失敗時に自動でフォールバックする。
- プロセス優先度:
  - 権限不足や未対応 OS の場合は安全に警告して処理を継続する設計（停止や例外を起こさない）。
- Execution / Monitoring の停止:
  - data/stop_requested.flag（および config で指定される kill/stop フラグパス）による外部からの安全停止をサポート。起動時にフラグが立っていると ExecutionEngine を起動せず終了する。

今後の予定（示唆）
- factor_research の各ファクター実装完了（Momentum, Value, Volatility, Liquidity の完全実装）。
- ブローカークライアント実装の充実（実ブローカー・モック双方の検証とドキュメント）。
- strategy/execution コンポーネントの E2E テストと追加ユーティリティ。
- ログやメトリクスの外部監視（Prometheus / Grafana 等）との連携強化。

ライセンスやセキュリティに関する記載はリポジトリの別ファイル（LICENSE 等）を参照してください。