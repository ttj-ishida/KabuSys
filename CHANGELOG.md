# Changelog

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。  

フォーマットの意味:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ関連

なお、以下の内容はコードベースから推測して記載しています。

## [0.1.0] - 2026-04-12

### Added
- 基本パッケージ構成 (kabusys)
  - パッケージメタ情報として `__version__ = "0.1.0"` を追加。

- 環境設定・自動.env読み込み
  - `kabusys.config.Settings` クラスを実装。環境変数経由で各種設定を取得（DBパス、APIトークン、閾値、PID/kill フラグパス等）。
  - 自動的にプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を読み込む機能を実装。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - `.env` パーサーは `export KEY=val`、クォート・エスケープ、インラインコメント等に対応。
  - `KABUSYS_ENV`（development / paper_trading / live）や `LOG_LEVEL` の検証、`PAPER_FILL_MODE`（instant/partial/never/reject）などの検証ロジックを実装。

- 実行用スクリプト
  - `run_execution.py`
    - 実行エンジン起動エントリポイントを追加。
    - `KABUSYS_ENV=paper_trading` の場合は Paper Trading 用の専用 SQLite (`data/paper_trading.db` など) を使用して本番 DB と分離。
    - ブローカークライアントを `BrokerClientFactory` から生成し、`OrderRepository` / `OrderManager` / `RiskManager` / `Reconciler` を組み立てて `ExecutionEngine.run_session()` を実行。
    - 起動時にプロセス優先度を "high" に設定。
    - DuckDB 接続を受け取る（分析用 DB ファイルの参照）。

  - `run_monitoring.py`
    - システム監視ループ起動エントリポイントを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバックし警告ログを出力。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 `sqlite_path` を使用して監視テーブルを初期化。
    - 起動時にプロセス優先度を "high" に設定。

- 監視 DB 初期化ユーティリティ
  - `monitoring.monitoring_db.init_monitoring_db` を用いた監視テーブルの冪等初期化を呼び出す実装（run_scripts 内で利用）。

- プロセス優先度／CPU affinity ユーティリティ
  - `kabusys.utils.process_priority.set_process_priority(level)` を実装。Windows / POSIX (Linux, Darwin, FreeBSD) を吸収して優先度（high/normal/low）を設定。権限不足や未対応 OS の場合は警告を出してスキップ。
  - `set_cpu_affinity(cpu_count)` を実装。指定コア数にプロセスをピン留め可能。引数検証と失敗時の警告を行う。

- ポートフォリオ構築モジュール（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 (`select_candidates`)、等金額配分 (`calc_equal_weights`)、スコア加重配分 (`calc_score_weights`) を実装。スコアが全て 0 の場合は等金額にフォールバックして警告を出力。

  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限の適用 (`apply_sector_cap`)、市場レジームに応じた資金乗数 (`calc_regime_multiplier`) を実装。unknown セクターの扱いやログ出力ポリシーを明示。

  - `kabusys.portfolio.position_sizing`
    - 各銘柄の発注株数計算 (`calc_position_sizes`) を実装。allocation_method に応じて risk_based / equal / score の計算を行い、lot サイズ単位で丸め、aggregate cap（利用可能現金を超えた場合のスケーリング）や cost_buffer（手数料・スリッページの保守見積り）を考慮する。安全弁として上限チェックと残差処理を備える。

- リサーチ／ファクター計算
  - `kabusys.research.factor_research`
    - DuckDB を用いて株価データ（prices_daily）や raw_financials を読み、モメンタム（1/3/6ヶ月、MA200乖離）、ATR(20)、流動性（20日平均出来高・売買代金）、PER/ROE を算出する関数 (`calc_momentum`, `calc_volatility`, `calc_value`) を実装。窓サイズやデータ不足時の None の扱いを明示。

  - `kabusys.research.feature_exploration`
    - 将来リターン計算（forward returns）`calc_forward_returns`、IC（スピアマンランク相関）計算 `calc_ic`、ファクター統計サマリー `factor_summary`、ランク変換 `rank` を実装。外部依存（pandas 等）を使わずに純粋 Python と DuckDB を組み合わせる設計。

  - `kabusys.research.__init__` に主要 API をエクスポート（zscore_normalize を含む）。

- AIニュース NLP スコアリング
  - `kabusys.ai.news_nlp` を追加。raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメントスコア（-1.0〜1.0）を生成して ai_scores テーブルへ書き込むワークフローを実装。
  - 処理のポイント:
    - 日時ウィンドウ（前日15:00 JST〜当日08:30 JST）を厳密に計算する `calc_news_window`。
    - 1銘柄あたりの最大記事数 / 最大文字数によるトークン肥大化対策。
    - 最大20銘柄を1バッチにして JSON Mode で API へ送信。
    - 429 / ネットワーク / 5xx 等は指数バックオフでリトライ（上限あり）。
    - レスポンスのバリデーションとスコアの ±1.0 クリップ。
    - 書き込みは対象コードを限定して部分失敗時の既存データ保護を図る（DELETE→INSERT の部分置換戦略）。

- ツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading の SQLite (`data/paper_trading.db` 等) を読み取り、システム安定性（稼働率）、注文成功率・送信率、リスク却下数、APIレイテンシ（平均・最大・P95）などを集計してコンソール出力する検証レポート機能を提供。
    - しきい値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を行う。
    - 日付フィルタ（--from, --to）や DB パス指定（--db / 環境変数）に対応。DB が存在しない場合のエラーメッセージを実装。
    - P95 の計算や欠損データ時の表示（N/A）に対応。

- DuckDB と SQLite の併用
  - 解析系は DuckDB（`DUCKDB_PATH`）、監視や paper_trading は SQLite を使用する設計を採用。各スクリプト・モジュールはそれぞれの DB 接続を受け取り閉じるように実装。

### Changed
- （初版のため特になし）

### Fixed
- （初版のため特になし）

### Deprecated
- （初版のため特になし）

### Removed
- （初版のため特になし）

### Security
- OpenAI API キーは引数または環境変数 `OPENAI_API_KEY` で解決。未設定時は `ValueError` を送出して明示的にエラー扱いにする実装を採用（安全な失敗挙動）。

Notes / 注意事項:
- 多くの関数は外部リソース（DB テーブル、ブローカー API、OpenAI）に依存します。実行前に環境変数や DB スキーマの整備が必要です（`.env.example` を参照する想定）。
- 一部の機能は権限依存（プロセス優先度設定や CPU affinity）であり、環境によって警告を出してスキップする実装になっています。
- 日付/時刻処理はUTC/タイムウィンドウに注意して実装されています。ルックアヘッドバイアス防止のため現在日時の直接参照を避ける方針が明示されています。

---

将来的なリリースでは、ユニットテストの追加、エラーハンドリングの強化、ログ構成の柔軟化、銘柄ごとの lot_size のマスタ化などが想定されます。必要であれば、変更履歴を Unreleased セクションに置き、次リリース向けの予定項目を追加できます。