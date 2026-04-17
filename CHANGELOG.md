# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

最新更新日: 2026-04-17

## [Unreleased]
- 小さな改善・ドキュメント整備を継続予定。

---

## [0.1.0] - 2026-04-17
初回リリース。本リポジトリに含まれる主要機能と実装上の注目点をまとめます。

### Added
- 全体
  - パッケージ初期版として各サブモジュールを追加。
  - バージョン情報を `kabusys.__version__ = "0.1.0"` として公開。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御はプロジェクト下の data/stop_requested.flag ファイルで行う。
    - 監視（monitoring）処理は環境にかかわらず本番用 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定する処理を実装。

  - run_execution.py
    - ExecutionEngine（取引エンジン）起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（本番/モック自動選択）。
    - ExecutionEngine をスレッドで起動し、data/stop_requested.flag の検知で安全に停止するループを実装。
    - 実行用 PID ファイルを data/execution.pid に書き出す仕組みを想定（Engine 側で使用）。

- 設定管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を読み込む）。
    - export KEY=val 形式やクォート付き値、インラインコメントの扱いを考慮した独自の .env パーサを実装。
    - 環境変数の読み込み優先度: OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用）。
    - Settings クラスを実装し、各種設定値（DB パス、API トークン、閾値など）をプロパティとして提供。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）や KABUSYS_ENV のバリデーションを実装。
    - 各種監視閾値（CPU/MEMORY/DISK）や PID ファイル・キルフラグのパスを提供。

- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）に対応し、psutil を利用して nice 値や優先度クラスを設定。
    - set_cpu_affinity を追加し、プロセスを最初の N コアに固定する機能を実装（アクセス拒否・未実装環境では警告を出してスキップ）。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - シグナルから候補抽出（select_candidates）と重み計算（等金額: calc_equal_weights、スコア加重: calc_score_weights）を実装。
    - スコア全てが 0 の場合のフォールバック（等金額配分）を WARNING ログで通知。

  - portfolio/risk_adjustment.py
    - セクター集中上限を適用して候補を除外する apply_sector_cap を実装。
    - レジーム（bull/neutral/bear）に基づく投下資金乗数 calc_regime_multiplier を実装（未知レジームはフォールバックで 1.0）。
    - セクターが "unknown" の場合は上限適用対象外とする仕様を採用。
    - price 欠損時の動作に関する TODO コメント（将来的に前日終値等でフォールバックを検討）。

  - portfolio/position_sizing.py
    - 各銘柄の発注株数を算出する calc_position_sizes を実装。
    - allocation_method による "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）で丸め、per-position と aggregate の両方の上限（max_position_pct, max_utilization）を考慮。
    - コストバッファ（cost_buffer）を用いた保守的見積りと、利用可能現金を超える場合のスケーリング・端数配分アルゴリズムを実装。

- リサーチ（因子計算・解析）
  - research/factor_research.py
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、相対ATR）、取引量指標を DuckDB 上で計算する関数を実装（calc_momentum / calc_volatility / calc_value）。
    - データ不足時に None を返す設計（安全性重視）。
    - DuckDB SQL を活用し、営業日ベースの窓を想定したスキャン範囲バッファを導入。

  - research/feature_exploration.py
    - 将来リターン calc_forward_returns、IC（calc_ic）計算、ファクター統計サマリー factor_summary、ランク変換 rank を実装。
    - 外部ライブラリに依存せず、標準ライブラリのみで統計を実装。
    - calc_ic はスピアマン相関（ランクのピアソン相関）を計算し、有効レコードが 3 未満の場合は None を返す。

  - research/__init__.py
    - 主要なリサーチ API をパッケージエクスポート。

- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news テーブルのニュースを OpenAI（gpt-4o-mini）でセンチメントスコア化し、ai_scores テーブルに書き込む機能を設計・実装。
    - 対象時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算するユーティリティ calc_news_window。
    - バッチ処理（1 API 呼び出しで最大 20 銘柄）とトークン肥大化対策（1 銘柄あたり最大記事数・最大文字数）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライする仕組みを用意（最大リトライ回数設定あり）。
    - レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗時のテーブル保護（対象 code のみ置換）などフェイルセーフ設計を採用。
    - ※実装途中（ソース末尾が切れている箇所あり）。API キー未設定時の例外ハンドリングは実装済み。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加（コマンドライン実行可）。
    - PAPER_TRADING_SQLITE_PATH 環境変数 / --db オプションで DB 指定可能（デフォルト: data/paper_trading.db）。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計してレポート出力。
    - 合格基準（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms）を設定し PASS/FAIL 判定を出力。
    - P95 の計算、各種 SQL 集計、存在しないテーブルへの耐性（OperationalError の捕捉）を実装。

### Changed
- （初回公開のため該当なし）

### Fixed
- .env パーサの改善により以下を正しく処理できるようにした:
  - export プレフィックスのサポート
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理
  - クォートなしでのインラインコメントの扱い（スペース直前の # をコメントとみなす）

### Security
- API キー（OpenAI, J-Quants, Kabu API など）は Settings プロパティおよび環境変数で扱い、未設定時は明示的にエラーを出すようにしている（誤設定の早期発見を促進）。

### Known Issues / Notes
- ai/news_nlp.py はファイル末尾で途中切れとなっており、記事取得部分（_fetch_articles）以降の処理が未表示／未確認です。実運用前に残りの実装とテストが必要です。
- portfolio/risk_adjustment.apply_sector_cap は price_map に価格が欠損（0.0）した場合にエクスポージャーが過少見積りされる可能性がある旨の TODO コメントが残されています。将来的に前日終値や取得原価でのフォールバックが推奨されます。
- DuckDB に関する注意: executemany の引数が空だとエラーになる制約をコード内で考慮している箇所あり（ai/news_nlp のトランザクション置換等）。
- 一部関数はデータ不足時に None を返す設計（安全優先）。呼び出し側での None ハンドリングが必要です。

---

改訂履歴の追加依頼や誤記の指摘があれば教えてください。今回の CHANGELOG はコード内コメント・実装から推測して作成しています。