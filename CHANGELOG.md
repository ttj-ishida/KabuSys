# CHANGELOG

すべての注目すべき変更点をこのファイルに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

## [0.1.0] - 2026-04-18

### 追加 (Added)
- 初回リリース: KabuSys (日本株自動売買システム) のコアユーティリティ群を導入。
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite DB を使用することで本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory を用いて本番/モックのブローカークライアントを切り替え。
    - ExecutionEngine をスレッドで起動し、data/stop_requested.flag による外部停止フラグ検知と安全停止処理を実装。
    - 起動時にプロセス優先度を "high" に設定。
    - PID ファイル (data/execution.pid) の管理を想定した構成。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視データを記録。
    - 停止フラグ (data/stop_requested.flag) によるループ終了・KeyboardInterrupt のハンドリングを実装。
    - duckdb を分析用 DB として接続。
- 設定管理
  - config.py
    - .env の自動ロード機能を提供（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env/.env.local の読み込み順と保護（OS 環境変数を保護）を実装。
    - .env 行パーサーは `export KEY=val`、クォート、バックスラッシュエスケープ、インラインコメント等に対応。
    - Settings クラスを実装し、J-Quants トークン・kabu API パスワード・DB パス・Paper Trading 設定・監視閾値・実行環境 (KABUSYS_ENV) などをプロパティで取得可能。
    - PAPER_FILL_MODE（paper trading の fill モード）に対するバリデーション（instant/partial/never/reject）。
    - 環境判定用のユーティリティプロパティ（is_live / is_paper / is_dev）。
- 設定ツール
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - デフォルト・選択肢表示、シークレットマスク、既存 .env 読込、確認→保存フローを実装。
    - .env のテンプレート書き出しをサポート（ファイルに注釈付きで書き出す）。
  - validate_config.py
    - 起動前チェック CLI を追加（必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在と YAML パース、ライブ環境向けの追加警告）。
    - --strict オプションで警告も失敗扱いにできる。
    - PyYAML が未インストールの場合は YAML 検証をスキップして警告を表示。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - シグナル選定 (select_candidates)、等配分 (calc_equal_weights)、スコア重み (calc_score_weights) を追加。スコア合計が 0 の場合は等配分へフォールバック。
  - portfolio.risk_adjustment
    - セクター集中制限を適用する apply_sector_cap を追加（売却予定銘柄除外、"unknown" セクターは制限対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear のマッピング、未知レジームは 1.0 でフォールバック）。
  - portfolio.position_sizing
    - 株数決定ロジック calc_position_sizes を追加（allocation_method: risk_based / equal / score）。
    - 単元株丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash によるスケールダウン）、cost_buffer の考慮、残差配分ロジックを実装。
    - lot_size の将来的な拡張についての TODO コメントあり。
- ユーティリティ
  - utils.logging_setup
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定する統一ロギングセットアップを追加。
    - ログディレクトリ作成に失敗した場合はファイル出力を無効化して stdout のみで継続。
    - ログレベル解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）。
  - utils.process_priority
    - プラットフォーム差分を吸収してプロセス優先度を設定するユーティリティを追加（Windows と POSIX をサポート、CPU affinity 設定も提供）。
    - 権限不足や未対応 OS の場合に警告を出して安全にスキップ。
- ツール
  - tools.paper_verification_report
    - Paper Trading 用検証レポート生成 CLI を追加。
    - システム稼働率、注文成功率（Filled / Created）、送信率（Sent / Created）、リスク却下数、レイテンシ指標（avg/max/P95）を集計して PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ、DB パス解決（--db / 環境変数 / デフォルト）を実装。
    - 既定の合格基準（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）を設定。
- 分析
  - research.factor_research
    - DuckDB を利用したファクター計算モジュールを追加（モメンタム / MA200 / ATR / 流動性 等を想定）。（モジュールは一部実装中）

### 変更 (Changed)
- ログ出力方針: コンソール出力は stderr ではなく stdout を使用（Task Scheduler / cron 等で stdout/stderr を一本化して扱いやすくするため）。
- .env 自動ロードはプロジェクトルートが検出できない場合にスキップ（パッケージ配布後の CWD 非依存性を確保）。

### 修正 (Fixed)
- MONITOR_POLL_INTERVAL の不正値（0 以下や非数）に対して警告してデフォルトにフォールバックするロジックを追加。
- .env パーサーはクォート内のバックスラッシュエスケープやインラインコメントの取り扱いを改善し、より堅牢に値を読み取るようにした。

### 注意・既知の制約 (Notes / Known issues)
- portfolio.risk_adjustment.apply_sector_cap の価格欠損時（price が 0.0）の扱いについて注釈あり（現状は過少見積りの可能性があるため将来的に前日終値や取得原価でのフォールバックを検討）。
- position_sizing の単元株数は現状グローバルな lot_size パラメータでのみ扱っている。将来的に銘柄別 lot_map を導入する予定（TODO）。

### セキュリティ (Security)
- なし

---

（注）本 CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のコミット履歴や変更履歴と差異がある可能性があります。