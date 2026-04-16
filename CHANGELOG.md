Keep a Changelog
=================

すべての変更は https://keepachangelog.com/ja/ に準拠して記載しています。
日付はコミット相当日（推測）です。

Unreleased
---------

- なし

[0.1.0] - 2026-04-16
--------------------

Added
- 基本パッケージ情報を追加
  - kabusys パッケージのバージョンを __version__ = "0.1.0" に設定。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成。
    - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag による安全停止、PID ファイル出力をサポート。
    - RiskManager, OrderManager, Reconciler 等の依存コンポーネントを組み立て、デフォルトの RiskConfig を設定（レート制限やサーキットブレーカー等を含む）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検出による安全終了、例外発生時のログ継続処理を実装。
- 設定管理
  - config.py: 環境変数 / .env 自動読み込み機能を追加。  
    - プロジェクトルート検出（.git または pyproject.toml を探索）により CWD 非依存で .env を読み込む。
    - .env/.env.local の読み込み順序を実装（OS 環境変数は保護される）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env のパーサを強化（export プレフィックス対応、引用符内エスケープ、インラインコメント処理）。
    - Settings クラスを導入し、各種設定プロパティ（DB パス、PID/kill フラグパス、しきい値、PAPER_FILL_MODE の検証など）を提供。
    - KABUSYS_ENV / LOG_LEVEL の有効値検証を実装。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定、等金額／スコア加重の重み計算を追加（スコア全0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）を追加。unknown セクターは制限対象外とする挙動を明記。
  - portfolio.position_sizing: 発注株数算出ロジックを追加。  
    - allocation_method に "risk_based" / "equal" / "score" をサポート。単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超えた場合のスケーリング）を実装。
    - cost_buffer による手数料・スリッページ保守見積りを考慮。
- ユーティリティ
  - utils.process_priority: プロセス優先度（Windows の HIGH_PRIORITY_CLASS / POSIX の nice 値）と CPU affinity 固定機能を追加。プラットフォーム差分を吸収し、権限不足や未対応環境では警告で安全にスキップ。
- リサーチ / ファクター計算
  - research.factor_research: DuckDB を用いたモメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR, avg turnover, volume ratio）およびバリュー（PER/ROE）ファクター計算関数を追加。SQL ベースで効率的に集計。
  - research.feature_exploration: 将来リターン（複数ホライズン）の一括計算、IC（Spearman ランク相関）計算、ファクター統計サマリ関数を追加。外部依存を持たず標準ライブラリのみで実装。
  - research パッケージは zscore_normalize を data.stats から取り込むエクスポートも行う。
- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成コマンドラインツールを追加。  
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標を算出し、閾値に基づく PASS/FAIL 判定を出力。
    - DB 存在チェック・期間フィルタリング・P95 計算ロジックを実装。DB のテーブル欠如に対しては例外を捕捉してデフォルト値で継続。
- AI ニュース NLP（部分実装）
  - ai.news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）へ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む設計を追加。  
    - ニュース収集ウィンドウ計算（JST→UTC 変換）、記事トリム、バッチ送信、リトライポリシー（429/ネットワーク/5xx の指数バックオフ）、レスポンス検証、スコアクリッピング等を仕様化。  
    - ファイル末尾が途中で切れているため処理の一部は未完（_fetch_articles 呼び出し以降が未収録）。※部分実装として扱う。
- DB 初期化補助
  - monitoring.monitoring_db の init_monitoring_db が run_* スクリプトから呼ばれることで監視テーブルの冪等な初期化を保証。

Changed
- ロギング / フォールトトレランス
  - 起動スクリプトや各ユーティリティで logging を用いた情報/警告/例外ログを細かく出力するようにした（起動時の環境出力、ポーリング開始ログ、例外ハンドリング）。
- 設定読み込みの挙動
  - .env の自動ロードは既存 OS 環境変数を保護するよう保護集合を導入し、.env.local を override=True で上書き可能に変更。
- ポートフォリオ / 発注ロジックの堅牢化
  - lot_size に合わせた丸めと aggregate cap のスケールダウンアルゴリズムを導入（端数配分は残差順で lot 単位で追加配分）。
  - price 欠損時のスキップやログ出力を明示化。

Fixed
- .env パーサのバグ修正/改善（推定）
  - export キーワード、引用符つき値内のエスケープ、インラインコメントの取り扱いなどを改善し、従来の単純実装での誤解析を防止。
- run_execution/run_monitoring のリソースリーク防止
  - finally で sqlite/duckdb コネクションを確実に close するようにしている。

Security
- OpenAI API キー取り扱い
  - ai.news_nlp の score_news は api_key 引数もしくは環境変数 OPENAI_API_KEY を使用し、未設定時は ValueError を送出してキー漏洩/未設定運用を明示。

Deprecated
- なし

Removed
- なし

Breaking Changes
- なし（ただし run_monitoring は常に本番 sqlite_path を使用する挙動や run_execution の paper_trading DB 分離など、既存運用に合わせた環境変数設定の確認が必要です）

Notes / 今後の TODO（コード内コメントからの推測）
- ai.news_nlp の記事取得・OpenAI 呼び出し以降の実装が途中で終わっているため、完全動作には残りの実装が必要。
- position_sizing の price 欠損時のフォールバック（前日終値や取得原価を使う等）や lot_size の銘柄別拡張は将来の改善候補。
- apply_sector_cap の price が 0 の場合の扱い改善（現状は過少見積りのリスクがある）を検討。
- テストカバレッジや CLI の利用例ドキュメント（README）整備が望ましい。

Acknowledgments
- 本 CHANGELOG は提供されたソースコードの内容から機能追加・振る舞いを推測して作成しています。実際の変更履歴（コミットメッセージ等）が得られる場合はそちらに合わせて更新してください。