# Changelog

すべての注目すべき変更点をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

最新リリース: 0.1.0

## [0.1.0] - 2026-04-13

初期公開リリース。本リポジトリは日本株自動売買システム「KabuSys」のコアユーティリティ群・実行用スクリプト・研究用モジュールを含みます。

### 追加 (Added)
- パッケージ基礎
  - pkg: kabusys
  - バージョン: 0.1.0 を `src/kabusys/__init__.py` に定義。

- 実行スクリプト
  - run_execution.py
    - ExecutionEngine の起動エントリーポイント。起動時にプロセス優先度を設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite（data/paper_trading.db）へ分離して動作。
    - ブローカークライアント生成（BrokerClientFactory）、OrderRepository、OrderManager、RiskManager、Reconciler の組み立てと ExecutionEngine の実行を行う。
    - duckdb 接続を使用。
    - DB の監視テーブルを冪等に初期化する `init_monitoring_db` を呼び出す。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様。
    - 起動時にプロセス優先度を設定し、sqlite3 / duckdb 接続を確立して SystemMonitor.check_once() を定期実行。

- 設定管理
  - config.py
    - .env 自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml を起点）。
    - .env / .env.local のロード順序（OS 環境変数 > .env.local > .env）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロードを無効化可能。
    - .env の行パースは export 形式、クォート、エスケープ、コメントを考慮。
    - Settings クラスを提供。多くの環境変数アクセサ（J-Quants、kabu API、LINE、DB パス、監視閾値、PID/kill flag パス、環境判定など）をプロパティとして定義。
    - PAPER_FILL_MODE のバリデーション実装（"instant" | "partial" | "never" | "reject"）。
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)：スコア降順、同点は signal_rank でタイブレーク。
    - 重み計算: calc_equal_weights（等配分）、calc_score_weights（スコア加重、全スコア 0 の場合は等配分にフォールバック）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap：セクター集中制限に基づく候補排除。売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier：市場レジームに応じた投下資金乗数（bull/neutral/bear をマップ、未知のレジームは警告して 1.0 にフォールバック）。

  - portfolio/position_sizing.py
    - calc_position_sizes：allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数決定。lot_size（単元株）丸め、per-position および aggregate cap（available_cash）でのスケールダウン処理、cost_buffer を考慮した保守的見積り、端数配分ロジックの実装。
    - risk_based: risk_pct と stop_loss_pct に基づく株数算出。
    - aggregate cap を超えた場合のスケーリングと lot_size 単位での追加配分を実装。

  - portfolio/__init__.py による公開 API エクスポート。

- 研究・ファクター計算
  - research/factor_research.py
    - momentum, volatility, value ファクター計算関数を実装（DuckDB を用いた SQL）。
    - mom_1m/3m/6m、ma200_dev、atr_20、atr_pct、avg_turnover、volume_ratio、per、roe 等を計算。
    - 処理は target_date に対する必要期間のみをスキャンするよう設計。

  - research/feature_exploration.py
    - 将来リターン（calc_forward_returns: デフォルト horizons=[1,5,21]）の計算。
    - IC（calc_ic）計算（Spearman ランク相関）と rank/統計サマリー（factor_summary）。
    - pandas 等に依存せず標準ライブラリのみで実装。horizons のバリデーションあり。

  - research/__init__.py による公開 API エクスポート（zscore_normalize を data.stats からインポート）。

- AI（ニュース NLP）
  - ai/news_nlp.py
    - raw_news + news_symbols から銘柄ごとに記事を集約し、OpenAI API（gpt-4o-mini）へバッチ送信してセンチメントを算出、ai_scores テーブルへ書き込み。
    - バッチサイズ、最大記事数／文字数トリム、リトライ（429/ネットワーク/5xx）と指数バックオフ、レスポンスバリデーション、スコアクリップ（±1.0）を実装。
    - タイムウィンドウ計算（JST 前日15:00～当日08:30 を UTC に変換）を実装しているためルックアヘッドバイアスを回避。
    - OpenAI API キー未設定時は ValueError を送出。
    - 部分失敗に備え、書き込みは影響範囲を限定（該当コードのみ削除→挿入）する設計。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成 CLI。デフォルト DB は data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 指標: 稼働率（uptime）、注文成功率（fill）、送信率（send）、レイテンシ（平均・最大・P95）、リスク却下数。
    - Pass/Fail 判定基準を定義（稼働率 >= 99%、注文成功率 >= 90% 等）。
    - CLI 引数: --from/--to/--db。日付フィルタは ISO8601 UTC で内部処理。
    - P95 計算、欠損時の扱い、SQLite のテーブル不存在を考慮したフェールセーフ実装。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度（nice/API）設定のユーティリティ。Windows と POSIX（Linux/Mac/FreeBSD）差を吸収。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。
    - アクセス権限不足や未対応 OS 時はログ警告して安全にスキップ。

- DB/モニタリング
  - monitoring.monitoring_db.init_monitoring_db 呼び出しにより監視テーブルを冪等に初期化するフローを run_* スクリプトで確保。
  - sqlite3（監視）と duckdb（分析）を用途に応じて併用。

### 変更 (Changed)
- 設計方針の明確化（ドキュメント文字列・関数 docstring の充実）
  - 各モジュールが参照するテーブルや外部依存（prices_daily/raw_financials/raw_news 等）を明記。
  - 研究モジュール・AI モジュール内で「本番 API にはアクセスしない」方針を明記。

### 修正 (Fixed)
- （初期リリースにつきコード内で指摘されている TODO を残した上で、既知の安全弁や例外処理を適切に追加）
  - .env 読み込み失敗時に warnings.warn を行い自動ロード継続。
  - process_priority 等でアクセス権例外をキャッチしてログ警告し処理継続するよう対策。

### 注意事項 / 既知の制約 (Known issues)
- apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャーが過少見積りされセクターブロックが外れる可能性がある旨を TODO として記載。将来的なフォールバック価格導入を想定。
- position_sizing:
  - lot_size は現状グローバルで固定（デフォルト 100）。将来的に銘柄別 lot_map を導入する予定（TODO）。
- ai/news_nlp:
  - 実行には OpenAI API キーが必要。API 呼び出しはレートやコストに注意。
  - JSON Mode のレスポンス検証を行うが、部分的な API 失敗が発生する可能性があり、処理は可能な限りロバストに設計されている（失敗したチャンクはスキップ）。
- research/feature_exploration.calc_forward_returns:
  - horizons の最大値は 252 日に制限。入力検証で超過値は ValueError。

### セキュリティ (Security)
- 環境変数に機密情報（API トークン等）を要求する箇所があるため、.env ファイルや環境変数の管理に注意してください（Settings は必須キー未設定で ValueError を出す設計）。

---

将来的なリリースでは、実行系の統合テスト、銘柄別 lot_size 対応、欠損価格時のフォールバック、AI モデルの運用最適化（リトライ/バッチロジックの改良）などを予定しています。