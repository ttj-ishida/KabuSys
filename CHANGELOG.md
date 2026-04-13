CHANGELOG
=========

すべての重要な変更点をここに記録します。フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------

- なし（今回のリリースは初回の機能実装を含みます）。

0.1.0 - 2026-04-13
-----------------

Added
- 実行・監視エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用の Paper Trading SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用する仕組みをサポート。起動時にプロセス優先度を "high" に設定する処理を呼び出す。
  - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する挙動を採用。

- 設定管理
  - config.py: Settings クラスを実装。プロジェクトルートの .env / .env.local を自動読み込み（OS 環境変数を保護）、.env パース機能は引用符・エスケープ・export フォーマット・インラインコメント等に対応。KABUSYS_ENV / LOG_LEVEL 等のバリデーション、PAPER_FILL_MODE の検証、paper_sqlite_path / pid_file_path / 各種しきい値等の設定プロパティを提供。

- 監視 DB 初期化
  - init_monitoring_db を起動スクリプトから呼び出して、監視用テーブルが存在することを冪等に保証（run_execution/run_monitoring 双方）。

- ポートフォリオ構築ライブラリ
  - portfolio_builder.py: 候補選定（スコア降順・タイブレーク）、等金額配分およびスコア重み配分（スコア全ゼロ時に等金額へフォールバック）を実装。
  - risk_adjustment.py: セクター集中上限を考慮して候補をフィルタする apply_sector_cap と、市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（未知レジームはログを出してフォールバック）。
  - position_sizing.py: 各銘柄の発注株数算出を実装。risk_based / equal / score の allocation_method をサポート、単元株（lot_size）で丸め、per-position 上限・aggregate cap（available_cash）・cost_buffer を考慮したスケーリングと再配分ロジックを実装。

- リサーチ / ファクター計算
  - research/factor_research.py: DuckDB 接続を用いたモメンタム、ボラティリティ、バリュー（PER/ROE）ファクター計算を実装。200日移動平均やATRなどのウィンドウ関数を用いた集計を含む。
  - research/feature_exploration.py: 将来リターン計算（多ホライズン対応）、IC（Spearman のランク相関）計算、ファクター統計サマリ、ランク付けユーティリティを実装。外部ライブラリに依存しない実装。

- AI ニュース NLP
  - ai/news_nlp.py: raw_news を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む機能を実装。チャンク処理、トークン肥大化対策（記事・文字数トリミング）、JSON 出力検証、スコアクリップ（±1.0）、429/ネットワーク/5xx に対する指数バックオフでのリトライをサポート。API キーが未設定の場合は ValueError を発生させる安全弁あり。

- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成ツールを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を集計し、PASS/FAIL 判定を行う（閾値はソース内定義）。コマンドライン引数で期間指定や DB パス指定が可能。

- プロセス制御ユーティリティ
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定関数 set_process_priority と、CPU affinity を最初 N コアに固定する set_cpu_affinity を実装。psutil を利用し、権限不足や未対応環境では警告を出して安全にスキップ。

Changed
- .env ロードの挙動
  - プロジェクトルート (.git または pyproject.toml を基準) を探索して .env/.env.local を自動ロード。OS 環境変数は保護され、.env.local は .env を上書きする形で読み込み可能。テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。

- DuckDB クエリの最適化/堅牢化
  - factor_research / feature_exploration の SQL はスキャン範囲にバッファ（カレンダー日換算）を与えてパフォーマンスを考慮。データ不足（ウィンドウ未満）の場合は None を返す等、欠損に配慮した実装。

- position_sizing のスケーリング改善
  - aggregate cap 超過時のスケーリングで、lot_size 単位で切り捨て後に「残余キャッシュ」を用いて端数（fractional remainder）の大きい銘柄から追加配分する再配分アルゴリズムを実装し、決定性（再現性）を確保。

- モニタリング周り
  - MONITOR_POLL_INTERVAL のパースを堅牢化。非正の値や不正な値はデフォルト (60 秒) にフォールバックして time.sleep の ValueError を防止するログ出力を追加。
  - 監視起動時にプロセス優先度設定（high）を行うように変更。

Fixed
- .env パーサの不具合対応
  - 引用符付き値に対するバックスラッシュエスケープおよび対応する閉じクォート検索、export プレフィックス対応、非引用符時のインラインコメント判定など、多様な .env フォーマットへの対応を強化。無効行はスキップする。

- ロバストネス改善
  - ai/news_nlp: API キー未設定時に明示的に ValueError を投げるようにして不正な API 呼び出しを未然に防止。
  - tools/paper_verification_report: テーブルが存在しない等の sqlite3.OperationalError を捕捉して、データ欠損時もツールが致命的に落ちないようにフォールバック値を返す処理を追加。
  - utils/process_priority: 未対応 OS や権限不足での失敗をキャッチして警告に留める（例外伝播を防止）。

- 統計・IC 算出の安定化
  - feature_exploration.calc_ic と rank: ties（同値）の扱いを平均ランクで処理し、サンプル数が小さい場合の保護（3 件未満で None を返す）を追加。浮動小数の丸め誤差対策として round を使用。

Misc
- パッケージメタ情報
  - __init__.py にてバージョンを "0.1.0" に設定し、主要サブパッケージを __all__ でエクスポート。

Notes / Known limitations
- ai/news_nlp の処理は外部 OpenAI API に依存するため、API レート制限やネットワーク障害の影響を受けます。部分失敗を考慮し、書き込みは影響範囲を限定する設計（対象コードのみの置換）を採っていますが、運用上の考慮が必要です。
- position_sizing の lot_size は現状グローバル固定で 100 を想定。将来的には銘柄別 lot_map を受け取る拡張を想定。
- .env 自動読み込みはプロジェクトルート検出に依存するため、配布・インストール後の環境では自動検出ができない場合があります（この場合は環境変数で明示的に設定してください）。

開発者メモ
- 初期リリースにあたり、DB スキーマや外部ブローカー周り（BrokerClientFactory / ExecutionEngine の内部実装）、SystemMonitor の詳細実装等は別モジュールで実装されています。本 CHANGELOG はソースコードから推測可能な変更点・機能をまとめたものであり、運用時の細かな仕様は README / ドキュメントを参照してください。