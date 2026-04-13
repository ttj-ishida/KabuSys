CHANGELOG
=========

すべての変更は Keep a Changelog の慣習に準拠して記載しています。

v0.1.0 - 2026-04-13
-------------------

Added
- 初期リリース: KabuSys の基本コンポーネント群を追加。
  - パッケージメタ情報
    - __version__ = "0.1.0"

- 実行・監視スクリプト
  - run_execution.py
    - ExecutionEngine の起動エントリポイント。
    - 起動時にプロセス優先度を "high" に設定。
    - 環境により paper_trading 用の専用 SQLite DB (PAPER_TRADING_SQLITE_PATH / data/paper_trading.db) を使用して本番 DB と分離。
    - BrokerClientFactory により本番/モックブローカークライアントを切り替え。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - duckdb をデータ処理用に利用。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 起動時にプロセス優先度を "high" に設定。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下・非整数）は警告ログを出してデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する点を明示。

- 設定管理
  - config.py
    - .env/.env.local の自動読み込み機構を追加（プロジェクトルートは .git または pyproject.toml を探索して決定）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パースの堅牢化:
      - export プレフィックス対応
      - シングル/ダブルクォートおよびバックスラッシュエスケープ対応
      - インラインコメントの取り扱い（クォート有無での差分処理）
    - Settings クラスを提供し、さまざまな環境変数プロパティをラップ:
      - J-Quants / kabu API / LINE / DB / 監視閾値 / システム設定 等
    - 設定検証:
      - KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等の値検証と不正時の例外・警告。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順・タイブレーク処理を実装。
    - calc_equal_weights, calc_score_weights: 等金額およびスコア加重を実装。全スコアが 0 の場合は等分フォールバック（警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap: 既存ポジションを考慮したセクター集中上限チェック（"unknown" セクターは上限対象外）。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear とフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method("risk_based","equal","score") に応じて発注株数を算出。
    - 単元株（lot_size）で丸め、per-position 上限、aggregate cap（available_cash）でスケールダウン、cost_buffer を考慮した保守的見積りを実装。
    - aggregate スケールダウン時に端数処理として残差に基づく追加配分ロジックを実装。

- 研究（Research）モジュール（DuckDB ベース）
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離の計算。
    - calc_volatility: ATR20・相対ATR・20日平均売買代金・出来高比の計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE 等を計算。
    - すべて DuckDB 接続を受け取り SQL で高速に計算する設計。
  - research.feature_exploration
    - calc_forward_returns: 指定ホライズンの将来リターン（複数ホライズン同時取得）。
    - calc_ic, rank, factor_summary: Spearman IC 計算、ランク付け、統計サマリ関数を実装。
    - 外部ライブラリ非依存（標準ライブラリのみ）。

- AI ニュース NLP
  - ai.news_nlp
    - raw_news を OpenAI (gpt-4o-mini) でセンチメントスコア化して ai_scores テーブルに書き込む。
    - 処理仕様:
      - タイムウィンドウは target_date ベースで計算（前日 15:00 JST 〜 当日 08:30 JST を対象、UTC に変換）。
      - 1 銘柄あたり最大記事数・文字数制限でトークン肥大を抑制。
      - 最大 20 銘柄/バッチで API へ送信。
      - 429 / ネットワーク / 5xx は指数バックオフでリトライ。
      - レスポンスを JSON として検証し、スコアを ±1.0 にクリップ。
      - 実行時に OPENAI_API_KEY の存在を必須とするチェック（引数からの指定も可）。
      - DuckDB 経由で部分的に DELETE→INSERT することで部分失敗時の既存スコア保護を考慮。

- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成 CLI。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 集計指標:
      - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。
    - 判定基準（デフォルト閾値）を定義（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。
    - --from/--to/--db オプション対応。データ不足・テーブル未存在時のフォールバックを実装。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level): Windows / POSIX（Linux, Darwin, FreeBSD）を吸収してプロセス優先度を設定。
    - set_cpu_affinity(cpu_count): 指定コア数への CPU affinity 設定機能を追加。
    - 権限不足や未対応 OS 時は警告を出して処理をスキップするフェイルセーフ。

Changed
- 自動環境変数読み込みのポリシー導入
  - .env/.env.local の自動読み込みロジックを追加し、環境構成の運用を簡素化。
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

- DB 周りの取り扱いの明確化
  - 監視系（run_monitoring）は常に本番用 sqlite_path を参照する設計を明示（監視データは本番 DB に記録する想定）。
  - Execution は paper_trading 環境時に専用の paper DB を使用して発注履歴等を本番と分離。

Fixed
- 環境変数パースの堅牢化（config._parse_env_line）
  - クォート＋バックスラッシュの組合せやインラインコメントの扱いでの誤解釈を改善。
- MONITOR_POLL_INTERVAL の不正値ハンドリング
  - 0 や負数、非整数が指定された場合に ValueError を回避してデフォルト値へフォールバックするように改善。
- position_sizing の aggregate スケールダウン時の端数配分ロジックを実装し、再現性と安全弁を追加。

Security
- 特記なし。

Notes / Breaking changes
- run_monitoring は KABUSYS_ENV に依存せず production sqlite_path を使用するため、開発環境で監視を起動する場合は DB パスの扱いに注意してください（意図的な設計）。
- Settings.require を使うプロパティは未設定時に ValueError を投げるため、CI/デプロイ時に必要な環境変数が揃っていることを確認してください（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。

今後の予定（短期）
- stocks マスタに lot_size を持たせ、銘柄別単元対応へ拡張予定。
- news_nlp の堅牢性向上（部分失敗時のロールバック戦略や外部キュー連携検討）。
- 研究モジュールのベンチマークと DuckDB クエリ最適化。

---END---