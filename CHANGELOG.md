# Changelog

すべての重要な変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- なし

## [0.1.0] - 2026-04-13
初回リリース。自動売買システム KabuSys のコア機能群を追加しました。主な追加点は以下のとおりです。

### 追加 (Added)
- 基本パッケージ
  - パッケージ初期化情報を追加（kabusys.__version__ = "0.1.0"）。
  - public API エクスポートを整理（kabusys.portfolio, kabusys.research, kabusys.data.stats などをエクスポート）。

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート検出（.git または pyproject.toml を基準）で .env 自動ロードを実行。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化に対応。
  - .env パーサを実装（クォート、エスケープ、コメント、export 形式に対応）。
  - 各種設定プロパティを用意（J-Quants / kabuAPI / LINE / DB パス / 監視パス / スレッショルド / 環境種別 / ログレベル 等）。
  - 環境変数の必須チェック用 _require を提供。

- 実行・監視スクリプト
  - run_execution.py:
    - ExecutionEngine の起動エントリポイントを追加。
    - 環境に応じて paper_trading 用 DB を分離（KABUSYS_ENV=paper_trading 時は data/paper_trading.db を使用）。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を起動。
    - duckdb, sqlite 接続の初期化とクローズ処理を実装。
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path（monitoring DB）を参照する設計。
    - プロセス優先度の設定（後述のユーティリティ利用）。

- プロセス設定ユーティリティ (kabusys.utils.process_priority)
  - set_process_priority(level) を実装し、Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定。
  - set_cpu_affinity(cpu_count) を実装（最初の N コアに固定）。アクセス権限や未対応環境では警告ログを出して安全にスキップ。

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選択するユーティリティ。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装（スコア全0時は等分にフォールバックして警告）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限を適用して候補を除外するロジックを実装（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を定義（bull/neutral/bear、未知レジームは 1.0 でフォールバック）。
  - position_sizing:
    - calc_position_sizes: 各銘柄の発注株数算出（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash を越える場合スケーリング）を実装。
    - cost_buffer による保守的見積り（スリッページ・手数料想定）と残差分の lot 単位での再配分ロジックを実装。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB の prices_daily を使って計算。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を算出（target_date 以前の最新財務データを取得）。
    - 設計方針として DuckDB のみ参照し、外部 API へのアクセスは行わない。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンに対する将来リターン（デフォルト: 1,5,21 営業日）。
    - calc_ic: Spearman ランク相関（IC）を実装（欠損や有効レコード数が 3 未満の場合は None）。
    - rank / factor_summary: ランク変換・基本統計量集計ユーティリティを実装。
    - 外部ライブラリに依存せず標準ライブラリで実装。

- AI ニュース NLP (kabusys.ai.news_nlp)
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し、銘柄ごとのスコアを ai_scores テーブルに書き込む処理を実装。
  - 処理フロー:
    - タイムウィンドウ計算（JST 基準で前日 15:00 〜 当日 08:30 相当の UTC 範囲）。
    - 記事集約（1銘柄あたり最大記事数・最大文字数でトリム）。
    - 20 銘柄単位でバッチ送信、429/ネットワーク/5xx 系は指数バックオフで再試行。
    - レスポンス検証とスコアの ±1.0 クリップ。
    - 部分失敗時にも既存データを保護するため、書き込みは対象コードに限定して差し替えを行う設計。
  - API キー未設定時には ValueError を送出する安全策を実装。

- ツール (kabusys.tools)
  - paper_verification_report:
    - Paper Trading 用の検証レポート生成スクリプトを追加（コマンドラインで期間指定可能）。
    - 稼働率・注文成功率・送信率・P95 レイテンシなどの指標を算出し、閾値に基づいて PASS/FAIL を判定。
    - デフォルトの DB は data/paper_trading.db。--db オプションや PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能。
    - P95 計算、NULL 安全な集計、DB が存在しない場合の親切なエラーメッセージを実装。

### 変更 (Changed)
- （初版のため過去バージョンとの差分なし）

### 修正 (Fixed)
- （初版のため修正履歴なし）

### 注意事項 / 設計上の制約
- portfolio の関数群はすべて純粋関数（メモリ内計算のみ）で DB 参照しない設計。
- research モジュールも DuckDB の prices_daily / raw_financials のみに依存し、発注 API へアクセスしない。
- process_priority / cpu_affinity は実行環境（OS・権限）によっては実行できない場合があり、その場合は警告ログを出して安全にスキップします。
- 一部関数に TODO / 将来拡張メモが含まれる（例: price 欠損時のフォールバック価格、lot_size の銘柄別対応など）。
- モニタリングは run_monitoring が本番 sqlite_path を参照する仕様のため、テストや paper_trading の監視 DB を分離したい場合は別途調整が必要。

### セキュリティ (Security)
- OpenAI API キーは引数または OPENAI_API_KEY 環境変数から取得。未設定の場合は明示的に失敗させることで誤った動作を防止。

---

（補注）実装の詳細はソース内の docstring / コメントに従っています。必要であれば、各機能ごとにより細かいリリースノート（例: 関数シグネチャ、デフォルト値、例外条件）を追記します。