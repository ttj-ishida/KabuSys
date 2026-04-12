# Keep a Changelog
すべての注目すべき変更をこのファイルにまとめます。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-12
初回リリース。本リポジトリに含まれる主要機能と実装上の挙動をまとめます。

### Added
- 全体
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として追加。
  - パッケージエクスポート（kabusys のサブモジュール公開）を定義。

- 実行 / 運用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境 (KABUSYS_ENV) にかかわらず本番の sqlite_path を使用する仕様。
    - プロセス優先度を起動時に "high" に設定。
    - DB 接続（SQLite / DuckDB）および監視ループのエラーハンドリングを実装。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=`paper_trading` の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory により実際のブローカーまたはモックを切替。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine を実行。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - 自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順序と上書きルール（OS 環境変数保護）。
    - 複雑な .env 解析対応（export 行、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い）。
    - 環境変数存在チェック用の _require() と Settings クラスを提供。
    - 多数の設定プロパティを公開（API トークン、DB パス、監視閾値、PID/KILL フラグパス、paper_trading フラグなど）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動読み込みを無効化可能。
    - `PAPER_FILL_MODE` の検証（有効値: instant|partial|never|reject）。

- 監視 / ツール
  - monitoring_db 初期化呼び出しを監視／実行スクリプトから行うことでテーブル存在を保証（冪等）。
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加（コマンドライン実行可能）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を集計して PASS/FAIL 判定を行う。
    - デフォルト閾値を定義（稼働率 99%、成功率 90% 等）。
    - 日付フィルタ、DB パス引数、PAPER_TRADING_SQLITE_PATH 環境変数をサポート。
    - DB がない場合やテーブルが未作成の場合でも安全に動作するよう例外をハンドル。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - BUY シグナル選定（スコア降順・同点タイブレーク）と候補選定機能を追加。
    - 等金額配分およびスコア加重配分（スコア全て 0 の場合は等金額へフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター比率が閾値を超える場合に同セクターの新規候補を除外。
    - レジーム乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" のマッピング）を実装。未知レジームは警告の上 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - position sizing（株数決定）を実装。
    - allocation_method に対応（risk_based / equal / score）。
    - 単元株丸め（lot_size）と per-stock 上限・aggregate cap（available_cash に基づくスケーリング）を実装。
    - cost_buffer による保守的コスト見積り、スケールダウン後の端数配分ロジックを実装。
    - 価格欠損や価格 <= 0 の場合はスキップする安全処理。

- 研究 / ファクター計算
  - research/factor_research.py
    - Momentum, Volatility, Value ファクター計算を DuckDB 上で実装（prices_daily / raw_financials を使用）。
    - 200 日移動平均乖離、ATR、平均売買代金、出来高比率、PER/ROE などを計算。
    - 欠損データに対する安全処理（ウィンドウ不足時は None を返す）。
  - research/feature_exploration.py
    - 将来リターン計算（任意ホライズン）、Spearman ランク相関（IC）計算、ファクター統計サマリ、ランク付けユーティリティ を実装。
    - ties の扱いは平均ランク（同順位は平均ランク）で処理し、丸め誤差を回避するため round を用いる。
    - 最小有効レコード数チェック（IC は有効レコード < 3 の場合 None を返す）。
  - research パッケージは外部ライブラリに依存せず標準ライブラリ + DuckDB で動作する方針。

- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news から銘柄ごとに記事を集約し、OpenAI API (gpt-4o-mini) を用いてセンチメントスコア（-1.0〜1.0）を付与し ai_scores テーブルへ書き込む機能を追加。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を計算し、UTC に変換して抽出。
    - 1 銘柄あたりの記事数・文字数上限を持つ集約（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - バッチ処理（最大 20 銘柄/コール）、429/ネットワーク/5xx 等に対する指数バックオフリトライ（上限あり）、レスポンス検証、スコアクリッピングを実装。
    - 部分失敗時に既存スコアを保護するため、更新対象 code を限定して DELETE → INSERT を行う。

- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定機能（Windows / POSIX 対応）を追加。設定失敗は警告でスキップ。
    - CPU affinity を最初の N コアに固定するユーティリティを追加（引数検証付き）。
    - Windows 用定数と POSIX nice 値を定義。

### Changed
- なし（初回リリースのため変更履歴なし）

### Fixed
- 初期実装として各モジュールにおいて想定される安全策を実装：
  - MONITOR_POLL_INTERVAL が不正（0以下や非数）な場合にデフォルトにフォールバックして警告を出す。
  - .env 読み込み失敗時に warnings.warn を出し、処理を継続。
  - calc_score_weights: 全銘柄スコアが 0 の場合は等金額配分へフォールバックして警告ログを出力。
  - SQL クエリや統計計算でデータ不足時に None を返すなどの堅牢化（研究・レポート系）。
  - OpenAI API キー未設定時には明確な ValueError を送出。
  - DuckDB に対する executemany の注意（空 params 回避）等、実行時障害を回避する注記（ai/news_nlp、その他）。

### Security
- API キーやパスワード等の機密は環境変数経由で読み込む設計（config.Settings の _require を利用）。
- .env 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` により無効化可能（テスト用途）。

### Notes / Known limitations
- research モジュールは DuckDB の prices_daily / raw_financials テーブルに依存する。これらが不足している場合は多くの値が None になる。
- apply_sector_cap は "unknown" セクター（mapper に存在しないコード）に対してはセクター上限を適用せず除外しない。
- position sizing の price 欠損 (0.0) は現状スキップ扱い。将来的にフォールバック価格（前日終値や取得原価）を導入する予定。
- news_nlp の API 呼び出しは gpt-4o-mini を想定。OpenAI 側の変更・レート制限・レスポンスフォーマット変更に対して脆弱性が残る可能性あり。
- monitoring は常に本番 sqlite_path を参照する仕様のため、テスト環境での監視動作には注意が必要（意図的な分離が要される場合は設定を変更すること）。

---

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリース日やバージョン運用ポリシーに合わせて適宜修正してください。）