CHANGELOG
=========

すべての重要な変更は「Keep a Changelog」形式で記載しています。  
慣例に従い、セマンティック バージョニングを想定しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-16
--------------------

Added
- 初期リリースとして主要コンポーネントを追加
  - 実行エンジン起動スクリプト
    - src/kabusys/run_execution.py
    - ExecutionEngine をデーモン スレッドで起動するランチャーを提供。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用の専用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用し、本番 DB とデータを分離。
    - ブローカークライアントを BrokerClientFactory 経由で生成し、OrderRepository・OrderManager・RiskManager・Reconciler を組み立ててエンジンを起動。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止、実行 PID ファイルの管理・待機ロジックを実装。
  - 監視プロセス起動スクリプト
    - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整（デフォルト 60 秒）。
    - 監視は環境に関わらず production 用の sqlite_path を使用する設計。
    - 停止フラグ検出・例外ハンドリング・接続クローズを含む安全なループ実装。
  - 設定/環境管理
    - src/kabusys/config.py
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）と .env/.env.local の自動読み込み（環境変数で無効化可）。
    - .env の行パーサ実装（export 形式、クォート内のエスケープ、インラインコメント処理など）。
    - Settings クラスで主要な設定プロパティを提供（DB パス、API トークン、監視閾値、環境判定等）。バリデーション・デフォルト値を定義。
  - ポートフォリオ構築ライブラリ
    - src/kabusys/portfolio/*
    - 銘柄選定（select_candidates）、重み計算（calc_equal_weights / calc_score_weights）。
    - セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）。
    - 株数決定ロジック（calc_position_sizes）：risk_based / equal / score の配分方式、単元株丸め、aggregate cap によるスケールダウン、コストバッファによる保守的見積りを実装。
  - リサーチ / ファクター計算
    - src/kabusys/research/*
    - モメンタム（calc_momentum）、ボラティリティ・流動性（calc_volatility）、バリュー（calc_value）の計算。
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリ（factor_summary）等の解析ユーティリティ。
    - DuckDB 接続を受け取り SQL と Python の組み合わせで効率的に計算する設計。
  - ニュース NLP（OpenAI 統合）
    - src/kabusys/ai/news_nlp.py（主要設計を実装）
    - raw_news / news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントをスコア化。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大化対策（記事数・文字数制限）、429/ネットワーク/5xx に対する指数バックオフ再試行を想定。
    - 結果を ai_scores テーブルへ安全に置換（部分失敗時の保護）。
    - OpenAI API キー未設定時は明確なエラーを返す。
  - ユーティリティ
    - src/kabusys/utils/process_priority.py
    - Windows と POSIX (Linux/Mac/FreeBSD) を吸収するプロセス優先度設定（high/normal/low）実装。CPU affinity 設定ヘルパも提供。
    - 権限不足や未対応環境では警告ログにフォールバックする堅牢な実装。
  - 運用ツール
    - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを提供。稼働率・注文成功率・送信率・レイテンシ（P95）等を集計し PASS/FAIL 判定を行う。
    - デフォルト DB パスは data/paper_trading.db（環境変数または --db で上書き可）。
  - パッケージ情報
    - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を設定。

Changed
- （初期リリースにつき該当なし）

Fixed
- （初期リリースにつき該当なし）

Notes / 行動指針・運用メモ
- DB:
  - デフォルトで DuckDB は data/kabusys.duckdb、監視用 SQLite は data/monitoring.db、Paper Trading SQLite は data/paper_trading.db を使用。環境変数で変更可能。
  - 監視用テーブルの初期化処理を冪等に実行（init_monitoring_db の呼び出し）。
- 環境変数:
  - 自動 .env ロードはプロジェクトルート検出に依存し、テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
  - Settings は未設定の必須環境変数に対して ValueError を送出するため、起動前に .env を整備してください。
- Paper Trading:
  - paper_trading 環境では発注シミュレーション用の DB と MockBrokerClient を用いる設計で、本番環境と明確にデータ分離されます。
- API / 外部依存:
  - news_nlp は OpenAI API を利用するため、利用時は OPENAI_API_KEY を設定してください。失敗時はフェイルセーフで継続するような設計が組み込まれていますが、キー未設定は例外になります。
- ロギング:
  - 起動スクリプトは basicConfig による INFO レベルログ出力を行います。Settings.log_level で運用時のログレベル管理を想定。

今後の方向性（予定）
- ニュース処理: OpenAI API のレスポンス検証・部分更新ロジックの耐障害性強化。
- 価格フォールバック: 価格欠損時のフォールバック（前日終値や取得原価）を position sizing / sector cap に導入。
- 単体テスト: factor / portfolio 周りのユニットテストの拡充と CI 統合。
- 運用: system_monitor と execution エンジンの統合テスト・耐障害性向上（再起動ポリシー等）。

---