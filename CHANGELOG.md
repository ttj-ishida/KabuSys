# Changelog

すべての重要な変更点をここに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  
継続的なリリース履歴の作成や運用時の参照にご利用ください。

※ 以下はリポジトリ内のソースコードから推測して作成した初期リリースの変更履歴です。

---

## [0.1.0] - 2026-04-16

### 追加
- 基本パッケージの初期実装を追加（KabuSys v0.1.0）。
  - パッケージ名: kabusys
  - バージョン: __version__ = "0.1.0"

- 実行 / 監視起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の SQLite（data/paper_trading.db のデフォルト）に完全分離して記録。
    - 実行中の停止フラグ（data/stop_requested.flag）検出時に安全に停止する仕組みをサポート。
    - 実行 PID を data/execution.pid に記録する想定の pid_file をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告の上デフォルトにフォールバック。
    - 監視処理は環境変数 KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）でループ終了。

- 設定管理モジュールを追加
  - config.py
    - .env / .env.local を自動読み込み（プロジェクトルート検出ロジック: .git または pyproject.toml を基準）。
    - export 形式、コメント、シングル/ダブルクォート、エスケープを考慮した .env パーサーを実装。
    - OS 環境変数を保護する protected 機能や自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）をサポート。
    - 各種環境変数プロパティ（JQUANTS, KABU API, DB パス, Paper Trading 関連設定、監視用しきい値等）を提供。
    - 環境名検証（development / paper_trading / live）や LOG_LEVEL 検証を実装。
    - PAPER_FILL_MODE の入力検証（instant/partial/never/reject）。

- ポートフォリオ構築・リスク調整・枚数計算モジュールを追加
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア正規化配分（全スコアが 0 の場合は等配分へフォールバックし警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有のエクスポージャー計算、売却予定銘柄の除外、"unknown" セクターは無視）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に基づく投下資金乗数（デフォルトフォールバックと警告あり）。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の配分メソッドを実装。単元株（lot_size）で丸め、per-position 上限・aggregate cap・コストバッファを考慮したスケーリング機構を実装。
    - aggregate cap でスケールダウンした際の残差配分ロジック（ランク付けして lot 単位で追加配分）を実装。

- 研究（Research）用モジュールを追加
  - research/factor_research.py
    - モメンタム・ボラティリティ・バリュー計算（DuckDB 接続を受け取り prices_daily / raw_financials を参照）。
    - 200日移動平均、ATR20、各種ホライズンのリターン等の計算を実装。
  - research/feature_exploration.py
    - 将来リターン計算（任意ホライズン）、Spearman ランク相関（IC）計算、ファクター統計サマリー、ランク化ユーティリティを提供。
    - pandas など外部重い依存を使わず標準ライブラリと DuckDB で完結する設計。

- AI ニュース NLP スコアリング機能を追加
  - ai/news_nlp.py
    - raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）にバッチ送信して銘柄別センチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む機能。
    - API キー解決、タイムウィンドウ計算（JST→UTC の固定ウィンドウ）、記事数/文字数トリム、20銘柄バッチ、JSON バリデーション、スコアクリップ、部分失敗を防ぐ DB 更新方法（対象コードを限定した置換）などを実装。
    - 429/ネットワーク/5xx に対する指数バックオフのリトライ実装（上限あり）。

- ユーティリティを追加
  - utils/process_priority.py
    - Windows / POSIX を吸収したプロセス優先度設定(set_process_priority)と CPU affinity 設定(set_cpu_affinity)を実装。
    - 権限不足や非対応 OS での安全なフォールバック（警告）を実装。

- ツールを追加
  - tools/paper_verification_report.py
    - Paper Trading の SQLite DB からシステム稼働率・注文成功率・送信率・P95 レイテンシ等を集計してレポート出力する CLI スクリプト。
    - 合否判定（閾値）と簡易レポートの印字機能を提供。--from/--to/--db オプションをサポート。

- パッケージ構造・エクスポート
  - portfolio モジュールの主要関数を __init__ で公開。
  - research パッケージで主要関数と zscore_normalize（data.stats）をエクスポート。

### 変更
- DB 初期化補助
  - monitoring.monitoring_db.init_monitoring_db を run_execution/run_monitoring 起動時に呼び出すことで、監視テーブルの存在を保証（冪等）。これにより監視テーブルが存在しない環境でも安全に起動可能。

- run_execution のデフォルト動作
  - paper_trading 環境では paper 専用の SQLite を使用し、本番 DB と分離する挙動を明示。

- .env 自動読み込みの挙動
  - プロジェクトルートが見つからない場合は自動読み込みをスキップ。自動読み込みを無効にする環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。

### 修正（バグフィックス・堅牢性向上）
- .env パーサーを強化
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメント処理などを適切に扱うように改善。
  - 不正な行は無視する安全設計。

- MONITOR_POLL_INTERVAL の不正値ハンドリング
  - run_monitoring._get_poll_interval で環境変数のパースに失敗した場合に警告をログに出し、デフォルト 60 秒へフォールバックするように修正（time.sleep に負の値を渡して ValueError を発生させないため）。

- OpenAI 呼び出しまわりの堅牢化（news_nlp）
  - API エラーや接続障害に対してリトライ/スキップのフェイルセーフを実装。API キー未設定時は ValueError を送出して早期に検出。

- プロセス優先度/CPU affinity の権限例外対策
  - psutil による設定で AccessDenied 等が発生した場合は警告ログを出力して処理を継続するようになり、権限の低い環境でも起動を阻害しない。

- position sizing の aggregate cap スケールダウン時の丸めロジック改善
  - スケーリング後の端数分を lot_size 単位で残余キャッシュを利用して追加配分するアルゴリズムを実装。再現性のため同値ソートはコードを二次キーとして安定化。

### 既知の制約 / 注意点
- 一部関数は DuckDB 接続や特定の DB テーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, system_status, trade_logs, risk_logs 等）に依存しており、適切なスキーマ/データが無い場合は OperationalError を投げる可能性があります。ツール側では OperationalError を受けてフォールバック処理を行う箇所があります（paper_verification_report 等）。
- run_monitoring は監視専用に本番 sqlite_path を使用する設計（環境に依存せず本番 DB へ書き込む）。テスト環境での実行時は注意が必要。
- calc_regime_multiplier の未知のレジームは警告を出し 1.0 でフォールバックする（安全側のデフォルト）。
- position_sizing は現在単元株（lot_size）を全銘柄共通で扱う設計。将来的に銘柄別 lot_size を導入する余地があることをコメントで示しています。

---

今後の予定（想定）
- テストカバレッジとユニットテストの追加。
- 銘柄別 lot_size や価格フォールバック（前日終値など）の導入。
- news_nlp の結果キャッシュやレート制御の強化。
- DuckDB を使ったバッチ処理のパフォーマンス改善や SQL 最適化。

--- 

（この CHANGELOG はソースコードの実装内容に基づく推測を含みます。実際の変更履歴・リリースノート作成時は開発履歴やコミットログを参照して精査してください。）