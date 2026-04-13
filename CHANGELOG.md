CHANGELOG
=========

すべての重要な変更は Keep a Changelog の方針に従って記載しています。
- フォーマット: https://keepachangelog.com/ja/1.0.0/

履歴
----

### [0.1.0] - 2026-04-13
初回公開リリース。リポジトリ内の主要機能を実装・追加しました（実装内容はコードから推測）。

Added
- 基本構成
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。
  - Settings クラスによる環境変数・設定管理を実装（.env 自動読み込み、優先順位、保護キー対応）。
  - Settings に多数のプロパティを追加（DB パス、PID/KILL フラグ、監視しきい値、環境判定、Paper Trading 関連設定等）。入力検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を行う。

- 実行エントリポイント
  - run_execution: ExecutionEngine を起動する CLI 相当のエントリポイントを追加。
    - BrokerClientFactory を使ったブローカークライアント生成（paper_trading モードでは専用 DB に分離）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - RiskManager のデフォルト RiskConfig を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）。
    - DuckDB / SQLite の接続管理と確実なクローズ処理。
    - プロセス優先度を起動直後に設定。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明示。
    - init_monitoring_db による監視 DB の冪等初期化。

- 監視・プロセス制御ユーティリティ
  - utils.process_priority:
    - set_process_priority(level): Windows / POSIX の差を吸収してプロセス優先度（High/Normal/Low）を設定。未対応 OS はスキップして警告。
    - set_cpu_affinity(cpu_count): 指定コア数への CPU affinity 固定（アクセス拒否等は警告してスキップ）。
    - 例外をキャッチしてデグレード（警告）する実装。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順＋signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）を実装。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクターごとの既存エクスポージャーに基づく候補除外（"unknown" セクターは無視）。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull:1.0, neutral:0.7, bear:0.3、未知レジームは 1.0 でフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: risk_based / equal / score の割当方式を実装。単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）でのスケールダウン、cost_buffer を考慮した保守的見積り、残差処理ロジックを実装。

- リサーチ・ファクター計算
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を DuckDB SQL で計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。NULL 伝播やカウント条件に注意した実装。
    - calc_value: raw_financials の最新財務データと価格を組合わせて PER / ROE を計算。
  - research.feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターンを一括クエリで取得。パラメータ検証（horizons の範囲）あり。
    - calc_ic / rank / factor_summary: スピアマンランク相関（IC）計算、ランク付け（同順位は平均ランク）、基本統計量サマリを実装。
  - research モジュールは duckdb 接続を受け、外部 API に依存しない設計。

- AI ニュース NLP
  - ai.news_nlp:
    - raw_news を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄別センチメント（-1.0〜1.0）を ai_scores に書き込む処理を実装。
    - タイムウィンドウ計算（JST→UTC 変換）や記事数・文字数上限、チャンク（最大 20 銘柄）によるバッチ化を実装。
    - API 呼び出し失敗（429/ネットワーク/5xx）に対する指数バックオフ・リトライ、レスポンスの厳密なバリデーション、スコアの ±1.0 クリップ、部分失敗時でも他銘柄スコアを保護する DB 更新戦略（DELETE→INSERT の絞り込み）を備える。
    - セキュリティ/設定: API キー未設定時は ValueError。
    - 重要設計: datetime.today()/date.today() を直接参照せずルックアヘッドバイアスを回避（target_date ベース）。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）を読み、稼働率・注文成功率・送信率・P95 レイテンシ等を集計して PASS/FAIL レポートを生成する CLI を追加。
    - デフォルトしきい値（稼働率 99%、成功率 90%、送信率 95%、P95 <= 200ms）を実装。
    - 日付フィルタ（--from / --to）対応、DB 存在チェック、テーブル欠如時のフォールバック動作を用意。

Changed
- 環境変数ロードの振る舞い
  - .env の自動読み込みを実装（プロジェクトルート検出: .git または pyproject.toml）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパースは export プレフィックス、クォート（エスケープ対応）、インラインコメント処理などをサポートし堅牢化。

- DB の利用方針
  - 監視 (run_monitoring) は環境に関係なく production 相当の sqlite_path を使用する旨を明示（意図的な設計/安全策）。
  - run_execution は paper_trading モード時に専用 paper_sqlite_path を使用して本番 DB と分離。

Fixed (実装上の安全策 / 想定されるバグ回避)
- 環境値の検証強化（不正値はエラー・警告で早期検出）。
- process priority / cpu affinity の設定でアクセス権限不足や未対応 OS の場合は例外を握り潰して警告し、プロセスが停止しないようにした。
- DuckDB に対する executemany の注意（空 params を渡さないことでエラー回避）等、実行時障害を想定した処理が散見される。

Removed
- 初版リリースにつき該当なし。

Security
- OpenAI API キーは明示的に引数または OPENAI_API_KEY 環境変数で渡す設計。未設定時はエラーにして漏洩リスクを抑止。

Notes / Breaking changes
- Settings の一部プロパティは必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を参照し、未設定時に ValueError を発生させます。デプロイ時は .env を用意する必要があります。
- PAPER_FILL_MODE の値検証により不正な文字列を許容しません（有効値: instant|partial|never|reject）。
- run_monitoring が常に production sqlite_path を参照するため、開発環境で意図せず実 DB を参照しないよう注意してください。

今後の改善（想定）
- position_sizing の lot_size を銘柄別に持てるよう拡張（stocks マスタ参照）。
- apply_sector_cap における価格欠損時のフォールバックロジック（前日終値や原価の利用）。
- news_nlp のレスポンス検証・バックオフをさらに堅牢化し、部分的な失敗からの自動リカバリを改善。
- ドキュメント（API、運用手順、環境変数サンプル）を整備。

----- 

（注）上記は提供されたコードから推測して記載した CHANGELOG です。実際のコミット履歴やリリースノートと差分がある場合は、該当箇所を差し替えてご利用ください。必要であれば英語版やセマンティックリリース向けの短縮版も作成します。