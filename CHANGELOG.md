# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### 追加
- なし

---

## [0.1.0] - 2026-04-13

初回リリース — KabuSys のコア機能を実装しました。以下はコードベースから推測してまとめた主要な機能・変更点です。

### 追加
- 全体
  - パッケージ初期化およびバージョン情報を追加（kabusys.__init__.__version__ = "0.1.0"）。
  - Settings クラスによる環境変数/.env ベースの設定読み込み機能を実装。自動ロード順は OS 環境変数 > .env.local > .env。プロジェクトルートは .git または pyproject.toml を基準に自動検出。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。

- 実行 / 監視
  - run_execution スクリプトを追加。ExecutionEngine の起動エントリポイントを提供。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（paper_trading に対しては MockBrokerClient を使用する想定）。
    - ExecutionEngine 起動前に OrderRepository、OrderManager、RiskManager（RiskConfig）、Reconciler を組み立てる。
    - 実行開始前にプロセス優先度を "high" に設定するユーティリティ呼び出しを実施。
  - run_monitoring スクリプトを追加。SystemMonitor のポーリングループ起動を提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値（0 以下・非整数）は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。

- データベース / クエリ
  - DuckDB と SQLite を併用する設計を採用（duckdb_path / sqlite_path）。
  - 監視テーブル初期化を行うための init_monitoring_db 呼び出しを両スクリプトで実行（冪等）。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順ソートと上位 N 選定機能。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコアに応じた重み付け。全スコアが 0 の場合は等配分にフォールバックして WARNING を出力。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限(max_sector_pct) を適用して新規候補を除外する機能（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは警告して 1.0 でフォールバック。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に対応した株数（lot 単位）決定ロジックを実装。stop_loss_pct/risk_pct/max_position_pct/max_utilization/lot_size/cost_buffer 等のパラメータを考慮。
    - aggregate cap（全銘柄合計が available_cash を超える場合）のスケーリングと、lot_size 単位での端数処理（残差に基づく追加配分）を実装。
    - price が欠損（<=0）の場合はスキップし、ログを出力。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率の計算を DuckDB SQL で実装。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から直近財務を取得し PER/ROE を計算。
    - いずれも prices_daily / raw_financials に依存。欠損データ時は None を返す設計。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（任意ホライズン、デフォルト [1,5,21]）計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。有効レコードが少ない場合は None を返す。
    - rank / factor_summary: ランク付けと統計サマリを実装。
  - DuckDB 接続を受け取り、外部 API に依存しない点を明記。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news → OpenAI（gpt-4o-mini）でのセンチメントスコアリング機能を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window。
    - 銘柄ごとに記事を集約してトークン肥大化対策（最大記事数・最大文字数）を実施。
    - 最大 20 銘柄/チャンクでバッチ送信。429・ネットワーク断・5xx に対して指数バックオフでリトライ。
    - レスポンス検証、スコアの ±1.0 クリップ、部分失敗に備えた部分的な DB 書き換え手順（DELETE + INSERT）を想定。
    - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError。
    - 設計上、API 失敗時も処理は継続する（フェイルセーフ）。

- ツール（kabusys.tools）
  - paper_verification_report:
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db をデフォルト）から統計を集計し検証レポートを標準出力に表示。
    - 指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ、リスク却下数など。
    - パス/フェイル基準（稼働率 >=99%、fill_rate >=90%、send_rate >=95%、P95 <=200ms）を定義し判定を表示。
    - コマンドライン引数 --from / --to / --db をサポート。

- ユーティリティ（kabusys.utils）
  - process_priority:
    - set_process_priority(level): Windows と POSIX（Linux/ Darwin / FreeBSD）を抽象化して優先度（high/normal/low）を設定。権限不足時は警告してスキップ。
    - set_cpu_affinity(cpu_count): 指定したコア数に固定する機能。cpu_count が None の場合は変更しない。権限不足等は警告してスキップ。

### 変更（設計上の注意点 / 実装上の取り決め）
- Settings._load_env_file:
  - export KEY=val 形式・クォート・インラインコメントに対応する独自パーサーを実装。既存の OS 環境変数を保護するため protected 引数を導入。
- run_monitoring:
  - 監視は常に本番用 sqlite_path を使う設計（環境設定に依存せず監視 DB を共通で扱う方針）。
- position_sizing:
  - lot_size は現状全銘柄共通で 100 を想定。将来的な拡張（銘柄別 lot_map）を TODO として明記。
- calc_score_weights / calc_regime_multiplier:
  - 異常値や未知値に対してフォールバック（等配分 / multiplier=1.0）を行い、ログ出力で通知。

### 修正（既知の注意点）
- apply_sector_cap:
  - price_map に 0.0 が来るとセクターエクスポージャーが過少評価される可能性がある旨の TODO コメントを追加。将来的に価格のフォールバックロジックが必要。
- utils.process_priority:
  - サポート外 OS の場合は設定をスキップし警告する実装。権限不足や未実装 API のケースも警告して安全に継続する。

### 既知の制約 / 未実装・留意点
- 一部モジュール（例: SystemMonitor の実装、BrokerClient の詳細、ExecutionEngine 内部挙動など）は本コード断片では省略されているが、呼び出しインタフェースは起動スクリプト側で確立済み。
- news_nlp の処理は OpenAI API を前提としており、API キーの管理とコストに注意が必要。
- DuckDB に対する executemany の制約を考慮した記述（空 params のチェック）が残されている点に注意。
- 日付/時刻処理は UTC naive を使用する箇所があり、運用時のタイムゾーン取り扱いに注意。

---

今後のリリースで想定される改善点（参考）
- 銘柄別 lot_size のサポート（stocks マスタからの取得）。
- apply_sector_cap の価格フォールバック（前日終値・取得原価など）。
- SystemMonitor / ExecutionEngine の堅牢化（詳細な例外ハンドリング・メトリクス拡充）。
- AI スコアリング結果の部分リトライ・ロールバック戦略の強化。

もし CHANGELOG に追記してほしい点（特定のコミットや issue、日付の調整など）があれば教えてください。コード履歴の断片からの推測に基づくため、必要なら実際のコミットログを参照してより正確な changelog を作成します。