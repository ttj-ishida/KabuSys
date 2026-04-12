# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
この CHANGELOG は、与えられたコードベースの実装内容から推測して作成しています（実際のコミット履歴ではありません）。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-12

初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装しています。主な機能・設計意図・注意点を以下にまとめます。

### Added
- 基本パッケージ情報
  - kabusys パッケージを導入し、バージョンを 0.1.0 に設定。
- 環境設定読み込みと管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）基準で自動読み込み（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パース機能を実装（export 形式対応、クォート・エスケープの取り扱い、インラインコメント処理）。
  - Settings クラスを提供し、アプリケーションで使用する各種設定値（DB パス、API トークン、PID ファイル、閾値、環境種別など）をプロパティ経由で取得。
  - 設定値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。
- 実行エントリスクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを提供。プロセス優先度設定、SQLite（本番/ペーパー分離）および DuckDB 接続、BrokerClientFactory によるブローカークライアント選択、OrderManager / OrderRepository / RiskManager / Reconciler 組み立て、ExecutionEngine の run_session() 呼び出しを実装。
    - paper_trading 環境では専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は常に本番 sqlite_path を使用。
    - KeyboardInterrupt によるグレースフルな終了処理を実装。
- モニタリング DB 初期化（monitoring.monitoring_db を参照）
  - 起動時に監視テーブルの存在を保証するための初期化処理を導入（冪等）。
- プロセス優先度ユーティリティ（kabusys.utils.process_priority）
  - Windows (psutilのpriority class) と POSIX (nice) の差分を吸収する set_process_priority() を実装。利用できない環境では警告を出してスキップ。
  - set_cpu_affinity() を実装（最初の N コアに固定する機能）。アクセス権限等で失敗した場合は警告で安全にスキップ。
- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder: 候補選定（スコア降順・タイブレーク）、等金額配分、スコア加重配分（スコア全0 の場合は等配分にフォールバック）。
  - risk_adjustment: セクター集中上限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。未知セクターの扱い、レジームフォールバック動作を定義。
  - position_sizing: 株数決定ロジック（risk_based / equal / score）、単元株丸め、per-stock 上限・aggregate cap のスケーリング、コストバッファ対応、lot_size（デフォルト 100）などを実装。
- リサーチ / ファクター計算（kabusys.research）
  - factor_research: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20 等）、バリュー（PER/ROE）等の計算ロジックを DuckDB SQL + Python で実装。データ不足時に None を返す安全設計。
  - feature_exploration: 将来リターン計算（任意ホライズン）、Spearman ランク相関（IC）計算、ファクター統計サマリー、ランク変換ユーティリティを実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージの公開 API を整備（zscore_normalize を含む）。
- AI ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI API（gpt-4o-mini）を使ったニュース記事センチメントスコアリング機能を実装。
  - 前日 15:00 JST 〜 当日 08:30 JST を対象ウィンドウとして記事を集約し、銘柄ごとにスコアを生成。
  - バッチ処理（最大 20 銘柄）、トークン肥大化対策（記事数上限・文字数トリム）、API エラー（429/5xx/タイムアウト等）に対する指数バックオフによるリトライ、レスポンス検証、スコアを ±1.0 にクリップして ai_scores テーブルへ部分的に置換する戦略を採用。
  - API キーは引数または環境変数 OPENAI_API_KEY で指定。未設定時は ValueError を送出。
- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成 CLI を実装。SQLite（paper_trading.db）を読み、システム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均・最大・P95）などを集計して標準出力に表示。閾値に基づく PASS/FAIL 判定を行う。
    - --from / --to / --db CLI オプションを提供。DB が存在しない場合のメッセージ出力を実装。
- データベースアクセス
  - DuckDB を分析用に利用（リサーチ／AI の集計）。
  - SQLite を監視・注文ログ・paper_trading 用に利用する構成を採用。
- 安全設計・堅牢性
  - 各所でデータ欠損時に None を返す、例外をキャッチしてログ出力し継続する（監視ループ等）などのフェイルセーフを導入。
  - ログレベル・環境値のバリデーションを実施し、不正値は明示的なエラーやフォールバックで扱う。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーや各種 API トークンは環境変数経由で管理する設計。README/.env.example に従ってローカル環境での取り扱いを推奨。

---

注意・既知の制約（実装内コメントより）
- apply_sector_cap:
  - price_map に欠損（0.0）があるとエクスポージャーが過少評価される可能性があり、将来的にフォールバック価格の採用を検討する旨の TODO が存在。
- position_sizing:
  - 単元株（lot_size）は現状全銘柄共通で 100 を想定。将来的に銘柄別 lot_size を導入する余地あり。
- config 自動読み込み:
  - プロジェクトルートが特定できない場合は .env の自動ロードをスキップする（配布パッケージ環境での安全措置）。
- process_priority / cpu_affinity:
  - 権限不足や未サポート環境では警告を出して処理をスキップする（明示的エラーを避ける）。
- research / feature_exploration:
  - ホライズンは営業日ベース（連続レコード数）を前提にしており、カレンダー日でのバッファを十分に取ってスキャン範囲を限定している。
- AI ニュース NLP:
  - API コール失敗時は部分的な失敗を許容して他銘柄の既存スコアを保護する設計。ただし部分失敗時のリトライ挙動・運用上の注意は README 等で明示することを推奨。

---

開発・運用への提案
- .env.example を整備して必須環境変数を明示する（Settings._require のメッセージにも言及あり）。
- モニタリングと実行エンジンのログやメトリクスを外部（Prometheus / Grafana 等）に送る拡張を検討。
- テストカバレッジ（特にリスク制御・ポジションサイジング・AI レスポンス検証）を充実させることを推奨。

(この CHANGELOG はコードの静的内容から推測して作成しています。実際の変更履歴やコミットログに基づくものではありません。)