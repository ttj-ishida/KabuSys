CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------

（現時点では未リリースの作業はありません）

0.1.0 - 2026-04-17
-----------------

初回リリース。本リリースでは、取引エンジン・監視・ポートフォリオ構築・研究用計算・ニュースNLP 等の主要コンポーネントを実装しています。主要な追加点・改善点は以下のとおりです。

Added
- 全体
  - パッケージのバージョンを追加（kabusys.__version__ = "0.1.0"）。
  - モジュールのエクスポートを整理（kabusys.portfolio, kabusys.research などの __all__ を設定）。

- 起動スクリプト
  - run_monitoring.py を追加（監視ループ起動スクリプト）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ data/stop_requested.flag による安全終了処理。
    - 監視はどの環境でも本番の sqlite_path を使用する仕様に明示。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py を追加（ExecutionEngine 起動スクリプト）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、ExecutionEngine の起動／終了制御（stop flag による制御）。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py に Settings クラスを実装：
    - .env/.env.local の自動読み込み機能（OS 環境変数を保護する override の仕組み）。
    - .env パース強化（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理）。
    - 各種設定プロパティ（PAPER_FILL_MODE の検証、PAPER_TRADING_SQLITE_PATH、DUCKDB_PATH、PID ファイルや閾値等）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック（不正値で ValueError を送出）。

- 監視関連
  - monitoring_db 初期化（init_monitoring_db を起動前に呼び出し、監視テーブルの存在を保証）。

- ツール
  - tools/paper_verification_report.py を追加（Paper Trading の検証レポート生成ツール）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL 判定を行う。
    - コマンドライン引数 --from / --to / --db をサポート。
    - データ不足やテーブル欠如に対するフェールセーフ（OperationalError を捕捉して N/A を出力）。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py を追加：
    - select_candidates（スコア降順の候補選定）、calc_equal_weights、calc_score_weights（スコアが全て 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py を追加：
    - apply_sector_cap（セクター集中の上限検査。既存保有のセクターエクスポージャ計算、unknown セクターは適用除外）。
    - calc_regime_multiplier（市場レジームに応じた投下資金乗数、デフォルトマッピングを実装）。
  - portfolio/position_sizing.py を追加：
    - calc_position_sizes（risk_based / equal / score の割当方式をサポート）。
    - lot_size に基づく単元丸め、aggregate cap による総投下額スケーリング、cost_buffer（手数料・スリッページ見積り）考慮。
    - price 欠損時のスキップ、上限 per-stock 計算、残差処理による追加配分ロジックを実装。

- リサーチ（ファクター計算）
  - research/factor_research.py を追加：
    - calc_momentum（1M/3M/6M リターン、MA200 乖離率）。
    - calc_volatility（ATR20、相対 ATR、20日平均売買代金、出来高比）。
    - calc_value（PER、ROE の算出、raw_financials の最新レコード取得ロジック）。
    - DuckDB を用いた SQL ベース実装（prices_daily / raw_financials を参照）。
  - research/feature_exploration.py を追加：
    - calc_forward_returns（複数ホライズンの将来リターンを一度のクエリで計算）。
    - calc_ic（スピアマンランク相関による IC 算出、データ不足時は None を返す）。
    - rank、factor_summary（基本統計量算出）。
  - research/__init__.py で主要関数と zscore_normalize をエクスポート。

- AI / ニュースNLP
  - ai/news_nlp.py を追加（OpenAI を用いたニュースセンチメントスコアリングの実装）。
    - ニュース取得ウィンドウの計算（JST を基準に UTC に変換、ルックアヘッド防止のため date.today() を使わない方針）。
    - 銘柄ごとの記事集約、記事／文字数のトリム、最大バッチサイズ、スコアクリップ（±1.0）。
    - API 呼び出しのリトライ（429・ネットワーク・5xx に対する指数バックオフ）。
    - 結果の JSON 検証、部分的な DB 更新（該当コードのみ置換）を想定した設計。
    - （注）ファイル末尾が途中で切れているため、実装の一部（記事フェッチ以降）が不完全な箇所あり。

- ユーティリティ
  - utils/process_priority.py を追加：
    - Windows と POSIX（Linux/Mac/FreeBSD）でのプロセス優先度設定を吸収する関数 set_process_priority(level)。
    - CPU affinity 設定用の set_cpu_affinity(cpu_count) を実装。
    - アクセス権限不足や未対応 OS 時の安全なフォールバック／警告ログ。

Changed
- .env 自動読み込み挙動を明確化（OS 環境変数優先、.env → .env.local の順で読み込み、.env.local は override=True）。
- .env パースの堅牢化（export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなど）。
- run_execution/run_monitoring での DB 初期化処理を冪等にして、監視テーブルが存在しない場合でも安全に起動できるように init_monitoring_db を起動時に呼び出すようにした。

Fixed
- calc_score_weights: 全銘柄スコアが 0 のケースでのゼロ除算を回避し、等金額配分へフォールバックするようにした（警告ログあり）。
- ポートフォリオの position sizing における aggregate cap のスケーリングと残余配分ロジックを実装し、利用可能現金を超えるオーダーを避ける処理を追加。
- process_priority：未対応プラットフォームや権限不足で例外が発生する可能性がある箇所で例外捕捉し、安全にスキップする挙動にした。

Notes / Known issues / TODO
- ai/news_nlp.py はファイル末尾が途中で切れているため、記事フェッチ部分や実際の DB 書き込みロジックの一部が未完（現状は draft 状態）。実運用前に残り実装と統合テストが必要。
- position_sizing.calc_position_sizes の price 欠損時の扱いについて補正（前日終値や取得原価によるフォールバック）を将来検討中（コメントに TODO）。
- apply_sector_cap は "unknown" セクターを除外して上限適用しない仕様だが、運用上のポリシー変更が必要な場合は設定で制御する検討が必要。
- .env 自動読み込みはプロジェクトルートの検出 (.git / pyproject.toml) に依存。配布後の環境でこれが見つからない場合は自動ロードをスキップする。

Files of interest
- 起動関連: src/kabusys/run_monitoring.py, src/kabusys/run_execution.py
- 設定: src/kabusys/config.py
- ポートフォリオ: src/kabusys/portfolio/*.py
- 研究/ファクター: src/kabusys/research/*.py
- AI / ニュース: src/kabusys/ai/news_nlp.py
- ツール: src/kabusys/tools/paper_verification_report.py
- ユーティリティ: src/kabusys/utils/process_priority.py

クレジット
- 本リリースは監視・実行・リサーチ・ポートフォリオ構築・NLP 周りの基盤機能を含みます。次リリースでは ai/news_nlp の完成、追加ユニットテスト、運用時の堅牢性向上（ロギング/メトリクス/エラー処理の強化）を予定しています。

もし特定ファイルや変更点についてより詳細な説明（実装意図、使用例、制約、単体テストの要点など）が必要であれば教えてください。