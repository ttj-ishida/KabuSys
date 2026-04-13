KEEP A CHANGELOG形式に準拠した CHANGELOG.md（日本語）を以下に作成しました。コードから推測可能な追加・変更点、既知の挙動や注意事項を項目化しています。リリース日は現在日付（2026-04-13）にしています。必要に応じて日付やバージョンを調整してください。

---
# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

## [0.1.0] - 2026-04-13
初回リリース。

### 追加
- 基本パッケージ
  - kabusys パッケージ初期化。パッケージバージョンを __version__ = "0.1.0" として公開。

- 設定管理
  - kabusys.config: 環境変数／.env ロード・管理モジュールを追加。
    - 自動でプロジェクトルート（.git または pyproject.toml 基準）を探索して .env/.env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント扱い（非クォート時の '#') に対応。
    - Settings クラスを提供。主要設定（DB パス、OpenAI トークン、KABUSYS_ENV、LOG_LEVEL、監視閾値、PID/kill-flag パス等）をプロパティとして取得・検証（不正な値で ValueError を送出）。
    - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等の値検証を実装。

- 実行ユーティリティ
  - kabusys.utils.process_priority:
    - プラットフォーム差を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。Windows と POSIX（Linux/Mac/FreeBSD）に対応。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。
    - 権限不足や未対応環境では警告ログを出して安全にスキップする挙動を実装。

- 起動スクリプト（CLI 実行用）
  - run_execution.py:
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper 専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立て、ExecutionEngine を起動するフローを実装。
    - RiskManager のデフォルト設定（max_position_pct 等）をコード内で設定。
    - 起動時にプロセス優先度を high に設定。

  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視 (monitoring) 用 DB は環境にかかわらず本番 sqlite_path を使用する設計（監視は常に本番データを参照）。

- 監視 DB 初期化
  - kabusys.monitoring.monitoring_db（参照はコードにあり、起動時に init_monitoring_db を呼び出して監視テーブルが存在することを保証）。

- ポートフォリオ構成関連（純粋関数群）
  - kabusys.portfolio.portfolio_builder:
    - シグナル選定 select_candidates（スコア降順、signal_rank によるタイブレーク）。
    - 等重み calc_equal_weights、スコア重み calc_score_weights（スコア全て 0 の場合は等重みにフォールバックして警告）。
  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存保有をセクター別時価で評価し、上限超過セクターの新規候補を除外。unknown セクターは無視）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をマップ、未知レジームは警告して 1.0 にフォールバック）。
  - kabusys.portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数計算。lot_size（単元）丸め、max_position_pct、aggregate cap（利用可能現金を超える場合のスケールダウン）に対応。スケーリング時に端数（lot 単位）を残差順に再配分するアルゴリズムを実装。価格欠損時はスキップ。

- リサーチ機能（DuckDB ベースのファクター計算）
  - kabusys.research.factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。各関数は prices_daily / raw_financials を参照し、所定のウィンドウと条件（例: MA200 行数チェック、ATR のデータ不足処理等）に基づく計算を行う。
    - 定数（MA/ATR 等）の説明と SQL 実装を含む。
  - kabusys.research.feature_exploration:
    - calc_forward_returns（複数ホライズン対応、引数検証あり）。
    - calc_ic（Spearman ランク相関の実装。データ不足時は None を返す）。
    - factor_summary（count/mean/std/min/max/median を計算）。
    - rank（同順位は平均ランク）。
  - kabusys.research.__init__ で主要関数をエクスポート。

- AI ニュース NLP スコアリング
  - kabusys.ai.news_nlp:
    - raw_news と news_symbols から銘柄ごとの記事集約を行い、OpenAI (gpt-4o-mini) を用いてセンチメントスコアを生成・ai_scores テーブルへ書き込む機能を実装。
    - バッチサイズ、文字数上限、記事数上限、スコアの ±1.0 クリップ、最大リトライ回数、エクスポネンシャルバックオフ等の制御を導入。
    - 出力は厳密な JSON を期待し、レスポンス検証を行う設計（部分失敗時の DB 保護のため、書込は対象コードに限定した削除→挿入の方式）。
    - OpenAI API キー未設定時に ValueError を送出。
    - ニュースウィンドウ計算（JST ベースの前日 15:00 ～ 当日 08:30 を UTC に変換）を提供。

- ツール
  - kabusys.tools.paper_verification_report:
    - Paper Trading 検証レポート生成スクリプトを追加。CLI (--from/--to/--db) をサポート。
    - 指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ、リスク却下数 等を集計し PASS/FAIL 判定（閾値はソース内に定義）。
    - レポートは標準出力に整形して出力。DB が存在しない場合はエラーメッセージを出力。

- パッケージエクスポート
  - kabusys.portfolio および kabusys.research の __init__ による主要 API の公開。

### 変更
- （初回リリースのため該当なし）

### 修正 / ロバストネス向上
- 環境変数読み込みの堅牢化:
  - .env パース改善（export 対応、クォート内エスケープ、インラインコメント処理）。
  - 自動ロード時に OS 環境変数を保護（.env.local の override 時にも OS 環境変数は上書きされない）。
- プロセス優先度・CPU 固定の失敗ケースを捕捉して警告ログを出すようにして、起動失敗を避けるようにした。
- DB 初期化処理（init_monitoring_db）は冪等化して、存在チェックや起動時の安全性を向上。
- 各種計算モジュール（factor/volatility 等）でデータ不足時の None ハンドリングを一貫して実装。
- paper_verification_report において、DuckDB/SQLite のテーブルが存在しない場合でも例外をハンドリングして欠損指標を N/A 表示にする処理を追加。

### 破壊的変更
- なし（初回リリース）。

### セキュリティ
- news_nlp は OpenAI API キーが未設定のまま実行すると明示的にエラーとなるため、誤った公開キー運用を防止する設計になっています。
- 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能で、テスト環境や CI で環境汚染を避けることができます。

### 既知の制限・注意事項
- run_monitoring は監視 DB に本番 sqlite_path を使用します。開発／紙トレード環境で監視ループを動かす場合は意図的な設定変更に注意してください。
- position_sizing 等の価格利用箇所で price が欠損（0.0）の場合、エクスポージャーや発注量が過小見積りされる可能性があり、将来的に価格フォールバック（前日終値や取得原価）を導入することを想定しています（TODO コメントあり）。
- news_nlp のレスポンスパースは外部 API に依存するため、モデル出力の想定外フォーマットが来た場合はスキップ・ロギングされ、部分的なスコア更新に留めます（DB 保護のため意図的な設計）。
- calc_forward_returns の horizons は 1〜252 の正の整数である必要があります（検証あり）。
- set_cpu_affinity は指定 core 数が利用可能コア数を超える場合、全コアを使用する旨ログ出力のみ行い動作します。権限不足や未対応環境では例外を吸収して警告でスキップします。

---

今後の予定（例）
- モジュール間のユニットテスト追加（特に position_sizing, risk_adjustment, news_nlp の外部 API ハンドリング）
- 銘柄別単元情報（lot_size）の導入と position_sizing の拡張
- news_nlp のレスポンス検証強化（スキーマバリデータ導入）およびメトリクス計測

---

注: 本 CHANGELOG は提供されたコードベースから推測して作成しました。実際のリリースノートとして使う場合は、実際のコミット／変更履歴に合わせて日付・バージョン・項目を調整してください。