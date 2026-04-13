CHANGELOG
=========

この CHANGELOG は「Keep a Changelog」準拠の形式で、提示されたコードベースの内容から実装された変更点・機能を推測して記載したものです。日付はコード内の参照や現時点（2026-04-13）を基準に推定しています。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

なお、実際のコミット履歴ではなくソースコードからの推測に基づく要約である点にご留意ください。

## [Unreleased]
- 今後のリリース予定のためのプレースホルダ。

## [0.1.0] - 2026-04-13
初回リリース。日本株自動売買システム「KabuSys」のコア機能を提供する初期実装。

追加 (Added)
- 基本パッケージ情報
  - pakage version を src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。

- 設定管理 (src/kabusys/config.py)
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env/.env.local の読み込み順序 (OS 環境変数 > .env.local > .env) と、環境変数上書き制御機構を実装（protected set による保護）。
  - Export 形式やクォート／エスケープ、行末コメントなどを考慮した .env パーサを実装。
  - 必須環境変数チェックのための _require() を提供。
  - 各種設定プロパティを実装:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - LINE API 関連
    - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
    - PAPER_FILL_MODE（有効値検証）
    - PID/KILL フラグパス・閾値(cpu/memory/disk)・ログレベル・環境（development/paper_trading/live）判定ユーティリティ

- 実行ランナー
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（不正値は警告してデフォルト 60 秒へフォールバック）。
    - Monitoring は環境に依らず本番 sqlite_path を使用する旨の挙動を実装。
    - プロセス優先度を高（"high"）に設定する処理を先頭で実行。
    - sqlite3 / DuckDB 接続初期化および init_monitoring_db 呼び出しの追加。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite DB を使用（本番 DB と分離）。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler の組み立て。
    - ExecutionEngine のセッション実行（engine.run_session()）。
    - 起動時にプロセス優先度を高に設定。

- 監視関連
  - monitoring_db.init_monitoring_db を用いた監視テーブル初期化を実装（冪等）。

- ポートフォリオ構築（src/kabusys/portfolio）
  - portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N を返す。
    - calc_equal_weights: 等金額配分器。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等分配にフォールバックして警告ログを出力。
  - risk_adjustment.py:
    - apply_sector_cap: セクター集中制限ロジック（既存保有のセクター別時価を計算して新規候補を除外）。unknown セクターは上限適用対象外。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームは警告して 1.0 にフォールバック。
  - position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に従う株数決定ロジックを実装。
    - 単元株（lot_size）で丸め、1 銘柄上限や aggregate cap（利用可能現金を超える場合のスケーリング）を実装。
    - cost_buffer（手数料・スリッページ見積り）を加味した保守的なコスト評価。
    - risk_based モードでの stop_loss に基づくリスクベース算出。

- リサーチ（src/kabusys/research）
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を DuckDB を使って計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算（true range の NULL 伝播制御を実装）。
    - calc_value: raw_financials から最新財務情報を取り出し PER/ROE を計算。
  - feature_exploration.py:
    - calc_forward_returns: 将来リターン（複数ホライズン）をまとめて取得する効率的クエリを実装。horizons 引数のバリデーションあり。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装（欠損や少数データの扱いを明確化）。
    - rank, factor_summary: ランキング関数および基本統計 (count/mean/std/min/max/median) を純粋関数で実装。
  - research.__init__ に zscore_normalize などをエクスポート。

- ニュース NLP（AI 統合） (src/kabusys/ai/news_nlp.py)
  - OpenAI (gpt-4o-mini) を用いたニュースセンチメントスコアリング機能を実装。
    - ニュースウィンドウ計算（JST 基準で前日 15:00 ～ 当日 08:30 を対象、UTC 変換）。
    - raw_news / news_symbols を銘柄別に集約し、1 銘柄あたりの最大記事数／文字数でトリム。
    - 最大 20 銘柄単位でバッチ化して API 呼び出し。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装（最大リトライ数設定）。
    - レスポンス検証、スコアクリッピング（±1.0）、部分成功時のテーブル置換戦略（DELETE→INSERT）などフェイルセーフ設計。
    - OpenAI API キーの解決（引数 > 環境変数 OPENAI_API_KEY）。

- ユーティリティ (src/kabusys/utils/process_priority.py)
  - set_process_priority: Windows/Linux/macOS の差を吸収して優先度を設定（psutil 利用）。権限不足や未サポート環境では警告してスキップ。
  - set_cpu_affinity: 指定コア数へ CPU affinity を設定するユーティリティ。引数検証と権限例外ハンドリングを実装。

- ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading 用検証レポート生成スクリプトを追加。
    - CLI 対応（--from/--to/--db）。
    - システム安定性 / 注文成功率 / シグナル精度 / レイテンシ指標（平均/最大/P95）を算出して整形表示。
    - P95 計算ユーティリティ、閾値定義（稼働率/成功率/送信率/P95 レイテンシ）を追加。
    - DB 欠如やテーブル欠如（OperationalError）に対する堅牢なフォールバック処理。

変更 (Changed)
- DuckDB と sqlite3 の併用設計: execution / monitoring ランナー・リサーチ関数等で DuckDB を読み取り分析、SQLite をトランザクションログ／監視保存に使用する設計を明示。
- .env パーシング挙動を改善し、export キーワードやクォート中のエスケープに対応。

修正 (Fixed)
- MONITOR_POLL_INTERVAL の不正値（0 以下・非整数）に対する回復処理を実装（警告ログ＋デフォルト 60 秒へフォールバック）。
- DuckDB に対する executemany 空パラメータ回避に関する注意コメント（ai/news_nlp 参照）。
- ファクタ / リサーチ関数における NULL 値伝播やデータ不足時の安全な None 返却を実装してクラッシュを回避。

既知の注意点（仕様上の設計注記）
- apply_sector_cap: price_map に価格が欠損（0.0）の場合、エクスポージャーが過少評価されてブロックが外れる可能性があり、将来的に前日終値などのフォールバック導入を検討する旨の TODO がある。
- calc_position_sizes: 将来的には銘柄別 lot_size のサポートを想定している（現状は全銘柄共通の lot_size を使用）。
- news_nlp: 実行に OpenAI API キーが必須。API 失敗時は基本的にそのチャンクをスキップして継続するフェイルセーフ設計。

セキュリティ (Security)
- 環境変数読み込みで OS 環境を protected として上書きを防ぐ設計により、ローカル .env による意図しない上書きを軽減。

開発メモ
- 大きな設計方針として「DuckDB を分析用に利用しつつ、実行系（発注・ログ）は SQLite 等で分離」するアーキテクチャを採用している。
- 関数群は可能な限り副作用を排し純粋関数化しており、ユニットテストと差し替え容易性を意識した実装になっている。

今後の予定（推奨）
- テストカバレッジの強化（特に OpenAI API 周りの失敗ケース）。
- price_map 欠損時の堅牢化（セクターエクスポージャーと position sizing のフォールバック価格導入）。
- 銘柄別単元株（lot_size）サポートの追加。
- 実運用に向けたログレベル設定の統合（Settings.log_level の適用タイミングの統一）。

以上。必要であれば、各機能ごとにさらに詳細な変更点（関数単位の説明や想定入出力例）を追記できます。どの粒度での CHANGELOG を希望するか教えてください。