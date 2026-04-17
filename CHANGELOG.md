# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-17

### 追加
- プロジェクト初版リリース。
- 実行用スクリプトを追加:
  - run_execution.py — ExecutionEngine を起動するエントリポイント。KABUSYS_ENV に応じた DB 分離（paper_trading 時は専用 DB）や BrokerClientFactory によるブローカー切替、PID ファイル・停止フラグ処理、スレッド実行に対応。
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数による間隔上書き、停止フラグ検出、監視用 DB 初期化を行う。
- 設定関連 CLI を追加:
  - config_setup.py — 対話式 .env 設定ウィザード。デフォルト値・選択肢・シークレット扱いの入力をサポートし、.env ファイルの生成・更新を行う。
  - validate_config.py — 起動前の設定検証ツール。必須環境変数のチェック、KABUSYS_ENV の妥当性確認、DB パスや config/*.yaml の存在・ YAML パース（PyYAML があれば）確認、--strict モードをサポート。
- 環境設定読み込み機能を実装:
  - config.py に .env 自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml 基準）。読み込み優先順位は OS 環境 > .env.local > .env。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント規則などをサポート。
  - Settings クラスを提供し、J-Quants / kabu / LINE / DB / 監視 / システムに関する各種設定プロパティを取得。paper_trading 用 DB パスや PAPER_FILL_MODE の妥当性検証等を実装。
- ポートフォリオ構築モジュールを追加（純粋関数群）:
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等配分/スコア加重（calc_equal_weights / calc_score_weights）。
  - portfolio.risk_adjustment: セクター集中上限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - portfolio.position_sizing: position sizing ロジック（risk_based / equal / score）、単元株丸め(lot_size)、aggregate cap スケーリング、コストバッファ考慮。
  - portfolio パッケージのエクスポートを追加。
- 研究・因子計算モジュールを追加:
  - research.factor_research: DuckDB の prices_daily / raw_financials を参照してモメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20 等）、流動性指標を計算する関数を実装。営業日ベースのウィンドウ処理や欠損値ハンドリングを考慮。
- ユーティリティを追加:
  - utils.process_priority: プラットフォーム横断でのプロセス優先度設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）、CPU affinity 固定機能（set_cpu_affinity）を実装。psutil のアクセス権限不足等を安全に扱う。
- 運用ツールを追加:
  - tools.paper_verification_report.py — Paper Trading 用検証レポート生成ツール。system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ指標（P95）を集計し、閾値に基づいて PASS/FAIL を判定。日付フィルタと DB パス指定オプションをサポート。
- パッケージメタ情報:
  - kabusys.__init__ にバージョン情報 __version__ = "0.1.0" を追加。

### 変更（設計・振る舞い）
- DB 分離ポリシー:
  - 監視（monitoring）は環境にかかわらず本番 sqlite_path を使用する設計とし、paper_trading 実行時のみ paper_sqlite_path（data/paper_trading.db をデフォルト）を使用するよう実装。
- 停止制御:
  - run_execution/run_monitoring はプロジェクト直下 data/stop_requested.flag（または設定されたパス）をチェックして安全に停止する仕組みを持つ。
- ログ・優先度:
  - run_* スクリプト起動時にプロセス優先度を "high" に設定する呼び出しを追加（実行環境で失敗しても警告にとどめる）。
- 設定検証:
  - validate_config は PyYAML が未インストールでも graceful に動作し、YAML 検証をスキップして警告を出す。
- .env 書き込みフォーマット:
  - config_setup により生成される .env はセクション分けされたテンプレートで書き出され、機密項目はマスク表示（表示のみ）する UI を提供。

### 修正（バグ修正 / 安全性向上）
- 環境変数読み込みの堅牢化:
  - _parse_env_line にて引用符つき値のバックスラッシュエスケープやインラインコメントの扱いを改善し、既存 OS 環境変数を保護するための protected オプションを導入。
- ポジションサイズ計算の安全弁:
  - calc_position_sizes にて price が欠損・0 の場合はスキップすることでゼロ割や不適切な算出を回避。aggregate スケーリング時の端数配分ロジックを実装して再現性を確保。
- モニタリングループの堅牢化:
  - run_monitoring のポーリング間隔 MONITOR_POLL_INTERVAL をパースする際に不正値を検知して安全にデフォルトへフォールバックする処理を追加。check_once() 内の例外を捕捉してループを継続するように変更。

### ドキュメント・メッセージ
- 各モジュールに日本語の docstring / コメントを追加し、設計意図・引数・返り値・注意点（TODO や将来の拡張案）を明記。
- config_setup のウィザードや validate_config のヘルプメッセージを整備。

### 既知の制限・注意点
- .env に書き出された機密情報は Git にコミットしないよう README 等で明記する必要あり（config_setup 生成ヘッダにも注意書きを追加）。
- apply_sector_cap は price_map に 0.0 が入るとエクスポージャーが過小評価される潜在的問題に関する TODO を残しており、将来的にフォールバック価格の導入を検討する必要がある。
- process_priority / set_cpu_affinity は環境によっては権限不足により設定が行えない場合がある（警告でスキップ）。

---

今後の予定（例）
- execution / monitoring の単体テストと統合テストの追加。
- stocks マスタに lot_size を持たせ、銘柄別単元対応を実装。
- factor_research の追加ファクター実装と z-score 正規化パイプライン統合。
- ドキュメント（README、運用手順）の整備。