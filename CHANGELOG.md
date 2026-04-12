# Changelog

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。

なお本リリースはパッケージの初回公開相当として、ソースコードから推測される機能・改善点をまとめています。

## [0.1.0] - 2026-04-12

### Added
- 基本パッケージ情報
  - kabusys パッケージ初期リリース（__version__ = 0.1.0）。
- 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git / pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサーの強化:
    - export プレフィックス対応、クォート文字列内のバックスラッシュエスケープ対応。
    - インラインコメントの扱い（クォートあり／なしでの挙動差）。
    - override / protected を考慮した読み込み（OS 環境変数保護）。
  - Settings クラスで各種環境変数をプロパティとして提供（DBパス、PID/kill flag、閾値、PAPER_FILL_MODE 等）。環境値のバリデーションあり（有効値チェック）。
  - settings = Settings() のシングルトン提供。
- 実行・監視起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを提供。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の別 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離する設計。
    - 起動時にプロセス優先度を High に設定（set_process_priority 呼び出し）。
    - duckdb と sqlite3 の接続を確立し、監視テーブル初期化を行う。
    - ExecutionEngine の組み立てで BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler 等を接続し run_session() を呼ぶ。
    - RiskManager に対するデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker, max_drawdown 等）をコード上で明示。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に依らず本番 sqlite_path を使用する旨の動作（明示）。
    - 起動時にプロセス優先度を High に設定。
- 監視 DB 初期化ユーティリティ（monitoring.monitoring_db 参照：init_monitoring_db を使用）
  - 監視テーブルの冪等な初期化を各起動スクリプトで実行することで存在を保証。
- ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level)：
    - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収して優先度（nice/HIGH_PRIORITY_CLASS 等）を設定。
    - 許可なし・未対応 OS の場合は警告してスキップ。
    - エラー（AccessDenied 等）時は警告ログを出して継続するフェールセーフ。
  - set_cpu_affinity(cpu_count)：
    - カレントプロセスを最初の N コアにピン留めする機能（None でスキップ、1 未満で ValueError）。
- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates(): BUY シグナルの上位選定（score 降順、同点は signal_rank 昇順）。
    - calc_equal_weights(), calc_score_weights(): 等金額配分／スコア加重配分（全スコア 0 の場合は等配分にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap(): 既存保有のセクター別エクスポージャーが上限を超える場合、同セクターの新規候補を除外。unknown セクターは制限外。
    - calc_regime_multiplier(): market regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知値は警告のうえ 1.0 フォールバック）。
  - position_sizing:
    - calc_position_sizes(): リスクベース／等配分／スコア配分に基づく株数決定、lot_size（単元）丸め、1 銘柄上限・aggregate cap、cost_buffer を考慮したスケーリングと残差配分ロジックを実装。
    - aggregate cap 超過時はスケールダウンし、fractional remainder を利用して lot 単位で追加配分するアルゴリズムを採用。
- 研究・リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum(), calc_volatility(), calc_value(): DuckDB 接続を受け取り prices_daily/raw_financials を参照して各種ファクター（モメンタム、ATR、売買代金、PER/ROE など）を計算。
    - 欠損データへの対応（ウィンドウ内行数不足で None を返す等）。
  - feature_exploration:
    - calc_forward_returns(): 将来リターンの一括取得（LEAD を利用して複数ホライズンを同時に計算）。
    - calc_ic(): Spearmanランク相関（IC）計算。データ不足時は None。
    - factor_summary(), rank(): 基本統計量・ランク変換ユーティリティ。
  - research パッケージは data.stats.zscore_normalize をエクスポートして統合提供。
- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント（-1.0〜1.0）を ai_scores テーブルへ書き込むワークフローを実装。
  - 特徴:
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算するユーティリティ（calc_news_window）。
    - 1 銘柄あたり最大記事数・最大文字数によるトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 最大バッチサイズ _BATCH_SIZE（20）で分割して API 呼び出し。
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライ（_MAX_RETRIES）。
    - レスポンスのバリデーション、スコアを ±1.0 にクリップ、部分失敗時には既存スコアを保護するために対象 code のみ置換する戦略（DELETE→INSERT の限定更新）。
    - API キー解決: 引数または環境変数 OPENAI_API_KEY。未設定時は ValueError。
- ツール（kabusys.tools.paper_verification_report）
  - ペーパートレード用の検証レポート生成 CLI を追加。
  - 機能:
    - 指定期間（--from / --to）で検証レポートを生成（デフォルト DB: data/paper_trading.db）。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）を算出して PASS/FAIL 判定を出力。
    - P95 の計算、N/A 表示、DB 存在チェック、DuckDB ではなく SQLite (paper_trading.db) を使用。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。
- モジュールのエクスポート整理
  - kabusys.portfolio と kabusys.research の __init__ で主要 API をまとめて公開。

### Changed
- なし（初回公開のため「変更」は特に記載なし。ただしコード内にフェールセーフや堅牢化の意図的実装あり）。

### Fixed
- .env 読み込み時のファイル IO エラーに対して警告を出し自動ロードを継続する仕様（テスト時にファイルが無い/読み込み失敗しても起動を阻害しない）。

### Known issues / Notes
- News NLP モジュールは OpenAI への実際の API 通信を行うため、API コストとレート制限に注意が必要。API キー未設定時は例外で早期通知される。
- position_sizing の価格欠損（price が 0.0 や None）の場合、現状はスキップしている。コメントに将来的なフォールバック価格（前日終値や取得原価）導入案あり。
- apply_sector_cap は "unknown" セクターを制限対象外とする設計（意図的）。
- run_monitoring は KABUSYS_ENV に依らず常に本番 sqlite_path を使用するため、テスト実行時は注意が必要。
- process_priority / set_cpu_affinity は OS と権限によって無効化される場合がある（警告ログで通知）。

---

今後のリリースでは、テストカバレッジ、ドキュメント（API リファレンス・設計書へのリンク）、および運用に関する追加の改善 (例: 銘柄別 lot_size 管理、より細かなエラーハンドリング、AI バッチ失敗時の部分再試行戦略) を計画しています。