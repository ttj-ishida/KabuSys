# Changelog

すべての変更は Keep a Changelog の仕様に準拠しています。  
日付はコードベースから推測した初回リリース (v0.1.0) リリース日を設定しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-12

### Added
- 実行用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて本番 DB / paper_trading 用 DB を切り替え、BrokerClientFactory を用いてブローカークライアントを生成、ExecutionEngine を構築して run_session を実行する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。
- 設定・環境読み込み
  - config.py: .env 自動読み込み機能 (.env, .env.local) を実装。プロジェクトルートの判定ロジック（.git または pyproject.toml）を導入し、CWD に依存しない読み込みを実現。
  - Settings クラス: 各種設定プロパティ（DB パス、PID/KILL フラグ、閾値、env/log_level、paper trading 関連など）を定義。環境変数の存在チェックや値バリデーションを行う。
- .env パーサ
  - export プレフィックス対応、クォートされた値のバックスラッシュエスケープ処理、インラインコメントの扱い、コメント判定ロジックを実装。
  - .env 読み込み時に OS 環境変数を保護する機構（protected set）を追加。
- モニタリング / ツール
  - monitoring DB 初期化ユーティリティ（init_monitoring_db）を呼び出す実行フローを追加。
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。稼働率・注文成功率・送信率・レイテンシ（P95）などを算出し、PASS/FAIL で判定する。コマンドライン引数で期間や DB パスを指定可能。
- ポートフォリオ構築モジュール
  - portfolio_builder.py: シグナルのソート・候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
  - risk_adjustment.py: セクター集中制限 apply_sector_cap、レジームに応じた投下資金乗数 calc_regime_multiplier を追加。
  - position_sizing.py: 各種配分方式（risk_based / equal / score）に対応した株数計算ロジックを追加。単元株丸め、per-position 上限、aggregate cap のスケールダウン、cost_buffer の考慮、残差処理ロジックを実装。
  - portfolio/__init__.py で上記 API を公開。
- リサーチ / ファクター計算
  - research/factor_research.py: モメンタム、ボラティリティ、バリュー系ファクター（mom_1m/3m/6m、ma200_dev、atr_20、atr_pct、avg_turnover、volume_ratio、per、roe）を DuckDB を用いて計算する関数を追加。
  - research/feature_exploration.py: 将来リターン計算 (calc_forward_returns)、IC（スピアマン順位相関）計算 (calc_ic)、ランク付けユーティリティ (rank)、ファクター統計サマリー (factor_summary) を追加。pandas 等に依存しない実装。
  - research/__init__.py にて主要関数を公開（zscore_normalize を含む）。
- AI ニュース NLP スコアリング
  - ai/news_nlp.py: raw_news を OpenAI (gpt-4o-mini) でバッチセンチメント解析し ai_scores テーブルへ書き込む処理を追加。バッチサイズ、記事数・文字数トリム、429/ネットワーク/5xx への指数バックオフ、レスポンスバリデーション、スコアの ±1.0 クリップ、部分成功時の DB 更新戦略（コードを限定して置換）などを備える。
  - calc_news_window 関数で JST ベースのニュース収集ウィンドウを UTC naive datetime で計算。
- ユーティリティ
  - utils/process_priority.py: プロセス優先度設定（Windows / POSIX 対応）と CPU affinity 設定ユーティリティを追加。set_process_priority と set_cpu_affinity を提供。
- パッケージメタ情報
  - __init__.py に __version__ = "0.1.0" を設定。

### Changed
- 実行時のプロセス優先度
  - run_execution/run_monitoring の起動時に最初に set_process_priority("high") を呼び出すようにして、重要プロセスとして優先度を上げる挙動を導入。
- DB 接続の分離
  - run_execution: paper_trading 環境（KABUSYS_ENV=paper_trading）の場合、専用の paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離する仕様に変更。
  - run_monitoring: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明確化。
- .env 自動ロードの優先順位
  - 自動ロードは OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動ロードを無効化。
- PAPER_FILL_MODE の検証
  - PAPER_FILL_MODE の有効値を明示（"instant" | "partial" | "never" | "reject"）し、無効値は ValueError を送出するように変更。
- settings.env / log_level の検証
  - KABUSYS_ENV は {"development", "paper_trading", "live"} に制限。LOG_LEVEL も定義済みセットに制限することで無効値時に明確なエラーを出すように変更。
- Paper 検証ツールの出力
  - レポートは P95 計算や各種指標の N/A 表示を整備し、FAIL の判定基準を閾値（稼働率/成功率/送信率/P95 レイテンシ）に基づいて出力するようにした。
- DuckDB / SQLite の利用
  - ファクター計算・AI スコアリングで DuckDB を利用する設計。監視・実行系は SQLite（および DuckDB はキャッシュ等用途）を併用する仕様。

### Fixed
- .env パーサの堅牢化
  - export プレフィックスやクォート内のバックスラッシュエスケープ、インラインコメント処理などのパースロジックを改善し、より実用的な .env フォーマットに対応。
- P95 計算の空リスト対応
  - paper_verification_report の _p95 関数で空リストに対して None を返すようにし、呼び出し側のフォーマット処理で N/A を出力するように修正。
- ニュースウィンドウの UTC 変換ロジック
  - target_date に対する JST ベースのウィンドウ計算を明文化し、DB クエリでの時間判定に一貫性を持たせた。
- 安全性 / フェイルセーフ
  - AI スコアリングで API キー未設定時に早期に ValueError を出すようにし、API エラー時はログを残して処理をスキップするフェイルセーフ挙動を追加。
  - process_priority / cpu_affinity の失敗（権限不足や未実装）を例外で止めずログ警告でスキップするように変更。

### Removed
- なし

### Security
- ai/news_nlp.score_news は OpenAI API キーが未設定の場合に ValueError を送出して処理を中断するため、キー漏洩に関する扱いを明確化。また .env の自動読み込みは環境変数（OS）を protected として上書きを避ける設計になっている。

### Migration notes
- 環境変数名・振る舞い
  - MONITOR_POLL_INTERVAL を用いて監視ポーリング間隔を変更可能。負値や 0 を与えると警告を出してデフォルト（60 秒）にフォールバックします。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると .env 自動ロードを無効化できます（テスト用）。
  - PAPER_FILL_MODE に不正な値を入れている場合、起動時に ValueError となるため、"instant" / "partial" / "never" / "reject" のいずれかに修正してください。
  - paper_trading 用 DB を分離しているため、過去の paper_trading データはデフォルト data/paper_trading.db に保存されます。必要に応じて PAPER_TRADING_SQLITE_PATH でパスを指定してください。
- 実行時挙動
  - 起動スクリプト実行時にプロセス優先度を "high" に設定しようとします。権限不足等で設定できない場合は警告が出ますが起動自体は継続します。

---

この CHANGELOG はコードリポジトリの現在の状態から推測して作成しています。リリースノートに含めたい追加情報（著名な bugfix、セキュリティアラート、互換性の詳細など）があれば追記します。