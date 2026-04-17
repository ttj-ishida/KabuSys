# Changelog

すべての重大な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に準拠します。  
このプロジェクトはセマンティックバージョニングを採用します。

## [Unreleased]

### Added
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプトを追加。
  - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視用 DB は実行環境に依存せず production 用の sqlite_path を使用する仕様。
  - 停止フラグファイル（data/stop_requested.flag）を検知して安全にループを終了。
  - プロセス優先度を起動時に "high" に設定する処理を組み込み。

- run_execution.py
  - ExecutionEngine 起動スクリプトを追加。
  - `KABUSYS_ENV=paper_trading` 時は paper_trading 用の SQLite DB（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
  - BrokerClientFactory によりブローカークライアントを抽象化して切り替え可能。
  - Engine の起動 / 停止処理（スレッド実行、停止フラグ監視、PID ファイルの取り扱い）を実装。
  - 起動時にプロセス優先度を "high" に設定。

- config.py
  - 環境変数・設定管理モジュールを追加。
  - .env/.env.local の自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml ベース）を実装。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - 複雑な .env パースに対応（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱い等）。
  - 各種設定プロパティ（API トークン、DB パス、paper_trading の設定、監視しきい値、環境判定など）を提供。入力値検証を含む。

- portfolio モジュール群
  - portfolio_builder: シグナル選択（スコア降順、同点は signal_rank でブレーク）と重み計算（等重・スコア加重）を実装。
  - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を実装。
  - position_sizing: 各種配分方式（risk_based / equal / score）に基づく株数決定ロジックを実装。lot_size（単元）調整、aggregate cap（利用可能現金に応じたスケールダウン）、cost_buffer による保守的見積り、端数配分ロジックを含む。
  - すべて純粋関数として DB 参照を行わない設計（メモリ内計算）。

- utils.process_priority
  - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加。
  - Windows と POSIX（Linux/Mac/FreeBSD）に対応、`set_process_priority(level)` と `set_cpu_affinity(cpu_count)` を提供。
  - 権限不足や未対応環境を考慮した警告処理を実装。

- research モジュール群
  - factor_research: モメンタム（1M/3M/6M・MA200乖離）、ボラティリティ（ATR20・avg_turnover・volume_ratio）、バリュー（PER, ROE）の計算を DuckDB を用いた SQL/ウィンドウ関数で実装。
  - feature_exploration: 将来リターン計算（複数ホライズン）、IC（Spearman ランク相関）計算、ファクター統計サマリー（count/mean/std/min/max/median）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージの __all__ を整備（外部から呼び出しやすくエクスポート）。

- tools.paper_verification_report
  - Paper Trading 検証レポート生成スクリプトを CLI として追加。
  - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を算出し PASS/FAIL 判定を出力。
  - デフォルト DB は data/paper_trading.db、コマンドライン引数 `--from`, `--to`, `--db` をサポート。
  - P95 計算、空データに対するフォールバックや OperationalError の安全ハンドリングを実装。

- ai.news_nlp
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し、銘柄別 ai_scores テーブルへ書き込む設計を追加。
  - API バッチ（最大 20 銘柄）、最大記事数・文字数による trimming、429/5xx/ネットワークエラーの指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリッピング、部分更新（対象コードのみ DELETE → INSERT）など堅牢性を考慮した処理設計を導入。
  - ニュース集計ウィンドウ（JST 基準→UTC 変換）を calc_news_window() で提供。
  - 注意: score_news 関数は API キー必須（引数 or OPENAI_API_KEY 環境変数）。

- パッケージ初期化
  - kabusys/__init__.py に __version__="0.1.0" を設定。

### Changed
- なし（初期導入相当の追加が主体）

### Fixed
- config.py の .env パーサにおいて、引用符内のバックスラッシュエスケープや行内コメント処理などに対応し、実運用での .env 設定読み込みの堅牢性を高めた。

### Deprecated
- なし

### Removed
- なし

### Security
- ai.news_nlp.score_news は OpenAI API キーを必要とする。環境変数や引数を利用して安全にキー管理を行ってください。

---

## [0.1.0] - 2026-04-17

初版リリース。上記機能群をパッケージ化して公開。

- 主な機能
  - Execution / Monitoring の実行スクリプト（run_execution, run_monitoring）
  - 環境設定管理（.env 自動ロード、Settings クラス）
  - ポートフォリオ構築（候補選定・重み・位置サイズ・リスク調整）
  - 研究用ファクター計算（Momentum / Volatility / Value）および特徴量探索ユーティリティ（forward returns, IC, summary）
  - Paper Trading 検証レポート CLI
  - AI ニュース NLP スコアリング（OpenAI インテグレーション、部分実装完了）
  - プロセス優先度 / CPU affinity ユーティリティ

- 安全策・設計上の注意
  - Paper Trading 環境は本番 DB と分離（PAPER_TRADING_SQLITE_PATH を使用）。
  - 設定は OS 環境変数を優先し、.env/.env.local を補完的に読み込む（既存 OS 環境は上書きされない）。
  - DuckDB/SQLite を用いる設計のため DB スキーマやテーブルの存在チェックを呼び出し側で行うこと（tools 側で OperationalError をハンドリング）。

---

注意事項・今後の TODO（コードから推測）
- ai.news_nlp の score_news 実装は大枠が出来ているものの、モジュール末尾の一部が不完全（ファイル切断の痕跡あり）。実行前に実装の完了とテストが必要。
- position_sizing の price 欠損（0.0）時のフォールバック価格（前日終値や取得原価）を将来的に追加検討する旨の TODO が残る。
- 将来的に単元株数（lot_size）を銘柄別に持たせるための拡張（stocks マスタ経由）がコメントで示唆されている。
- Windows / POSIX の優先度設定は権限に依存するため本番環境での動作確認推奨。

---

貢献・バグ報告
- バグ報告や改善提案は issue を立ててください。可能であれば最小再現コードやログを添えていただけると助かります。