# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。  
このプロジェクトの初期リリース（v0.1.0）に含まれる主要な機能・設計上の注意点を日本語でまとめています。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-04-16
初回リリース。自動売買システム KabuSys のコアユーティリティ、ポートフォリオ構築、リサーチ、監視・実行ランナー、及びニュース NLP スコアリングなどの初期実装を追加。

### Added
- パッケージ基礎
  - パッケージメタ情報を追加（src/kabusys/__init__.py、__version__ = "0.1.0"）。

- 環境設定 / ロード処理（src/kabusys/config.py）
  - .env と .env.local をプロジェクトルートから自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パースの堅牢化（export プレフィックス、クォート内エスケープ、行内コメント処理などをサポート）。
  - 環境変数アクセス用 Settings クラスを提供。主要プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL, LINE_* トークン類（一部は省略可能）
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH（デフォルトパスと expanduser 対応）
    - PAPER_FILL_MODE（有効値検証）
    - 監視関連のしきい値（CPU/MEM/DISK）や PID / kill flag パス
    - KABUSYS_ENV / LOG_LEVEL のバリデーション（development / paper_trading / live 等）

- プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
  - プラットフォーム差（Windows / POSIX）を吸収して優先度を設定する set_process_priority(level) を追加。
  - CPU コア数を固定する set_cpu_affinity(cpu_count) を追加。
  - アクセス権限エラー等はログ警告でスキップするフェイルセーフ設計。

- 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
  - ExecutionEngine を起動するエントリポイント。
  - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
  - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
  - 停止フラグ（data/stop_requested.flag）検知時にセッション停止。PID ファイル管理。
  - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec 等）を初期化。初期資金は broker.get_available_cash() を基に設定。

- 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
  - SystemMonitor のポーリングループを起動するエントリポイント。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（data/monitoring.db）を使用する設計。
  - 起動時にプロセス優先度を "high" に設定。停止フラグ検知でループを終了し DB 接続をクローズ。

- Paper Trading 検証レポートツール（src/kabusys/tools/paper_verification_report.py）
  - CLI で Paper Trading DB を解析し、稼働率・注文成功率・送信率・レイテンシ等を出力するレポートを追加。
  - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。
  - --from / --to / --db オプション対応。DB が存在しない場合はエラーメッセージを出力。
  - 各種クエリは存在しないテーブルに対して sqlite3.OperationalError をハンドリングしてフォールバック。

- ポートフォリオ構築ライブラリ（src/kabusys/portfolio/*）
  - portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順でフィルタ（signal_rank で同点ブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算。スコア全体が 0 の場合は等金額にフォールバックし警告。
  - risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（既存ポジションのセクター比率が上限を超えている場合に新規候補を除外）。"unknown" セクターは上限適用外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知のレジームは WARNING とともに 1.0 にフォールバック）。
  - position_sizing.py:
    - calc_position_sizes: 各配分方式（risk_based / equal / score）に基づく発注株数計算。単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）に基づくスケーリングを実装。コストバッファ考慮。価格欠損時はスキップ。
  - これらは純粋関数群で DB 参照無し（メモリ内計算）。

- リサーチ・ファクター計算（src/kabusys/research/*）
  - factor_research.py:
    - calc_momentum / calc_volatility / calc_value: DuckDB を使ったモメンタム、ボラティリティ、バリュー系ファクター計算を提供。ウィンドウ要件（例: MA200, ATR20）に満たない場合は None を返す実装。
  - feature_exploration.py:
    - calc_forward_returns: 将来リターン（fwd_1d, fwd_5d, fwd_21d 既定）を一括クエリで取得。
    - calc_ic / rank / factor_summary: IC（Spearman のランク相関）や基本統計量、ランク付けユーティリティを実装。外部依存なし（標準ライブラリのみ）。
  - research パッケージのエクスポートを整備（zscore_normalize は kabusys.data.stats からインポートして再エクスポート）。

- ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント解析し、銘柄ごとの ai_scores テーブルへ書き込むための基幹ロジックを実装。
  - 処理フローの概要:
    - ターゲット日のニュースウィンドウ（JST 前日15:00〜当日08:30）を UTC に変換して抽出する calc_news_window。
    - 記事集約、最大記事数／最大文字数でトリム（銘柄あたり最大 10 記事、3000 文字）。
    - バッチ送信（1 API 呼び出しあたり最大 20 銘柄）、429/ネットワーク/5xx に対する指数バックオフリトライを想定。
    - レスポンスバリデーション・スコアクリッピング（±1.0）・部分成功時の DB 更新戦略（該当コードのみ置換）を想定。
  - OpenAI API キー未設定時は ValueError を送出する設計。
  - （注）ファイル末尾が断片的に切れているため、完全実装の一部が未表示。ただし設計と主要定数・関数は追加済み。

### Changed
- なし（初回リリースのため新規実装中心）。

### Fixed
- MONITOR_POLL_INTERVAL の不正値処理を run_monitoring.py に実装。0 以下や非整数は警告を出してデフォルト値にフォールバック。

### Notes / Known limitations / TODO
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合、現在はスキップする実装。将来的に前日終値や取得原価などのフォールバックを検討する旨の TODO コメントあり。
- apply_sector_cap:
  - "unknown" セクターは上限適用対象外（意図的な挙動）。
- news_nlp.py:
  - ファイルは途中で切れている（提供コード断片）。API 呼び出し部分や DB 書き込みの細部は完全実装を確認する必要あり。
- 環境依存の機能（プロセス優先度・CPU affinity）は権限不足や未対応プラットフォームで警告を出してスキップする実装のため、実行環境で期待通りに効果が出るかは運用環境での検証が必要。

### Security
- OpenAI API キーや各種認証トークンは環境変数で管理する設計。Settings._require により未設定時は早期にエラーとなるため、秘密情報の漏洩には注意して環境を設定してください。

---

今後のリリースでは、news_nlp の完全実装とテスト、ExecutionEngine・SystemMonitor 周りの堅牢性向上、各関数のユニットテスト追加、ドキュメント充実（PortfolioConstruction.md 等参照）を予定しています。