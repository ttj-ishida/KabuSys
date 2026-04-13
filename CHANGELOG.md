CHANGELOG
=========

すべての変更は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）の形式に準拠しています。  
日付はリポジトリから推測できる最新の時間軸（ローカル環境: 2026-04-13）を使用しています。

Unreleased
----------
（なし）

[0.1.0] - 2026-04-13
-------------------

Added
- 基本情報
  - パッケージ初期リリース。パッケージバージョンは kabusys.__version__ == "0.1.0"。

- 実行エントリ / デーモン
  - run_monitoring.py を追加。
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバックし警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用して初期化（monitoring 用テーブルを作成）。
    - DuckDB との接続を利用。
    - 起動時にプロセス優先度を "high" に設定する処理を呼び出す。

  - run_execution.py を追加。
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離（settings.is_paper に基づく）。
    - BrokerClientFactory によるブローカークライアント生成（MockBroker を含む想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine.run_session() を実行。
    - 起動時にプロセス優先度を "high" に設定。

- 設定・環境読み込み
  - config.py を追加。
    - .env / .env.local の自動ロード機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
    - .env パーサ実装:
      - export KEY=val 形式対応、シングル/ダブルクォート中のバックスラッシュエスケープ対応、インラインコメント処理（クォートあり／なしの差異を考慮）。
      - override / protected（OS 環境変数の保護）オプションをサポート。
    - Settings クラスを公開（settings = Settings()）。
    - 各種環境変数プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、ログレベル、PID/KILL フラグパス、閾値など）。
    - バリデーションを実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の有効値チェック）。

- モニタリング / ツール
  - monitoring.monitoring_db の初期化呼び出しを複数箇所で使用（起動時の冪等なテーブル作成）。
  - tools/paper_verification_report.py を追加。
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシなどを集計して CLI で検証レポートを出力。
    - コマンドラインオプション --from/--to/--db をサポート。
    - P95 計算、閾値（稼働率、成功率、送信率、P95 レイテンシ）の定義と PASS/FAIL 判定を実装。
    - DB が存在しない場合やテーブルが不足している場合にフォールバックして N/A を出力。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選抜（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限を適用（当日売却予定銘柄を除外、"unknown" セクターは上限非適用）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear → 1.0/0.7/0.3、未知は 1.0 にフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に応じた発注株数計算。
    - 単元株丸め、1 銘柄上限（max_position_pct）、aggregate cap によるスケーリング、cost_buffer を用いた保守的見積り、残余キャッシュでの追加配分ロジック等を実装。
    - lot_size 固定（将来的に銘柄別拡張可能）と入力検証・ログ出力。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度設定（psutil 利用）。対応レベル: high/normal/low。権限不足等は警告でスキップ。
    - set_cpu_affinity(cpu_count): 最初の N コアにプロセスを固定する機能（引数検証、権限不足時は警告でスキップ）。

- リサーチ（DuckDB ベースの因子計算・解析）
  - research.factor_research
    - calc_momentum, calc_volatility, calc_value: prices_daily / raw_financials テーブルを用いてモメンタム、ボラティリティ、バリュー系ファクターを計算（ウィンドウ条件や欠損扱い等の仕様を明記）。
  - research.feature_exploration
    - calc_forward_returns: 将来リターンの計算（horizons 引数、入力検証、1 クエリ実行）。
    - calc_ic: スピアマンランク相関（IC）をコード単位で結合して算出（有効レコードが 3 未満なら None）。
    - rank / factor_summary: ランク変換（同順位は平均ランク）と要約統計量（count/mean/std/min/max/median）。
  - research.__init__ で主要 API をエクスポート（zscore_normalize の再エクスポート含む）。

- AI / ニュース NLP
  - ai.news_nlp
    - raw_news から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）にバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算の実装（calc_news_window）。
    - バッチサイズ、1 銘柄当たりの記事数・文字数制限、429/ネットワーク/5xx に対する指数バックオフとリトライ、レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗を考慮した DB 書換ポリシーなどを設計に反映。
    - API キー未設定時に ValueError を送出（api_key 引数 or OPENAI_API_KEY 環境変数）。
    - 実行はフェイルセーフ（API 失敗時はログを出して継続）。

Changed
- （初版のため改定履歴なし）

Fixed
- （初版のため修正履歴なし）

Security
- OpenAI API キーなどの機密情報は環境変数経由で取得する設計。config の .env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テストや安全性確保のため）。

Notes / 実装上の注意（ドキュメント的補足）
- DB パスのデフォルト:
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
- run_monitoring は監視 DB に対して常に本番 sqlite_path を用いるので、開発環境での運用には注意が必要（意図的な設計）。
- position_sizing・risk_adjustment は純粋関数群で DB 参照を行わずメモリ内計算に限定しているためユニットテストが容易。
- .env パースはシェルライクな基本的ケースに対応しているが、複雑なシェル展開はサポートしない。
- ai.news_nlp は OpenAI の呼び出しが含まれるため、実行にはネットワーク接続と適切な API キーが必要。API レスポンスの仕様変更やレート制限に備えてログとリトライの挙動を用意している。

今後の想定（参考）
- stocks マスタで銘柄ごとの lot_size を持たせる拡張（position_sizing の lot_map）。
- position_sizing の価格フォールバック（前日終値や取得原価）によるエクスポージャー過少見積りの改善。
- ai.news_nlp の部分失敗時におけるトランザクション的整合性の強化（より厳密なロールバック/差分適用）。
- モニタリング結果の長期保存・可視化パイプライン（DuckDB との連携強化）。

--- 
以上。必要であれば各項目をさらにファイル単位・コミット単位で分解してより詳細な CHANGELOG を作成できます。どの粒度で出力するか指定してください。