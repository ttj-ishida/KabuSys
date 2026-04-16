# Keep a Changelog
すべての重要な変更をここに記録します。  
このファイルは Keep a Changelog の形式に従います。  

## [Unreleased]
### 注意点 / TODO / 既知の問題
- ai/news_nlp.score_news の実装が途中で途切れており（ソースが切れているため）、OpenAI への送信・結果書き込み周りは未完。実運用前に完了とテストが必要。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる旨の TODO コメントあり。前日終値や取得原価でのフォールバック検討が必要。
  - 将来的に銘柄別の lot_size をサポートする拡張予定あり（現状は全銘柄共通 lot_size）。
- apply_sector_cap: "unknown" セクターは現状で上限適用対象外（設計上の意図）。挙動を変更する場合は注意。
- DuckDB に対する executemany の制約（空 params を渡さない等）の扱いに注意が必要（ai/news_nlp の設計注記）。
- クロスプラットフォームのプロセス優先度設定は権限や OS に依存するため、権限不足時は警告を出してスキップする。CI / コンテナ環境での挙動確認推奨。

---

## [0.1.0] - 2026-04-16
初期リリース。自動売買／リサーチ基盤の基礎機能を実装。

### Added
- 全般
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
  - プロジェクト配布後も動作する .env 自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を基準に探索（kabusys.config）。
  - .env パーサを強化:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート中のバックスラッシュエスケープ処理を実装
    - インラインコメントの扱い改善
    - OS 環境変数を保護する protected 機能（.env.local は上書き可能だが OS 環境変数は保護）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能（テスト用途）
  - Settings クラスを提供し、各種設定値（DB パス、API トークン、監視閾値、環境判定など）をプロパティ経由で安全に取得可能。

- 実行・監視
  - run_execution.py:
    - ExecutionEngine 起動用スクリプトを追加。BrokerClientFactory により環境に応じて実ブローカー／MockBrokerClient を切り替え（KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB に記録）。
    - paper_trading 用に専用 SQLite パス（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）検知で安全に停止するロジックを実装。PID ファイル（data/execution.pid）を指定可能。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立て例と既定のリスク設定を追加。
    - duckdb 接続を ExecutionEngine に提供。
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告表示してデフォルトにフォールバック。
    - 監視処理は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する仕様（監視は本番データ参照前提）。
    - 停止フラグの検知・ログ出力・例外ハンドリング（check_once の例外はループ継続）を実装。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順ソート（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分。全スコアが 0.0 の場合は等分にフォールバックし警告を出力。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限検査（max_sector_pct）と新規候補の除外ロジックを実装。売却予定銘柄を除外してエクスポージャー計算可能。
    - calc_regime_multiplier: レジーム（"bull"/"neutral"/"bear"）に応じた投下資金乗数（1.0/0.7/0.3）を実装。未知のレジームは警告して 1.0 を返す。
  - position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に対応した注文株数算出ロジックを実装。単元株丸め、per-position 上限、aggregate cap（available_cash に応じたスケーリング）、cost_buffer（手数料・スリッページ見積り）対応。lot_size 単位での残余配分アルゴリズムを実装。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算（true_range の NULL 伝播に配慮）。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算。
    - 全関数は DuckDB による SQL ベース実装で prices_daily/raw_financials を参照し、結果を (date, code) 辞書リストで返す。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装。データ不足（有効レコード < 3）の場合は None を返す。
    - rank, factor_summary: ランク付け（同順位は平均ランク）と基礎統計量集計を提供。
  - research パッケージ __init__ にて必要なエクスポートを提供（zscore_normalize を data.stats からインポート）。

- AI / ニュース（kabusys.ai）
  - news_nlp:
    - ニュース記事を OpenAI（gpt-4o-mini, JSON Mode）で銘柄別にスコアリングする設計を追加。
    - バッチサイズ、トークン肥大対策（記事数・文字数トリム）、リトライ（429/ネットワーク/5xx）やスコアクリップ（±1.0）などの運用ルールを実装。
    - calc_news_window: 標準化されたニュース収集ウィンドウ（JST→UTC 変換）を実装。
    - score_news（途中実装）: API キー解決やウィンドウ計算、記事集約処理の骨子を実装（ただしソースは途中で切れているため最終処理未完）。
  - 設計上のフェイルセーフ:
    - API 失敗時はスキップして継続する方針（フェイルセーフ）。
    - 書き込み時は対象コードを絞って部分失敗時に既存データを守る実装方針（DELETE→INSERT 部分更新）。

- ツール
  - tools/paper_verification_report:
    - Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを算出して標準出力へ整形して表示する。
    - 検証基準（THRESHOLD_*）を定義し、データ欠損時のフォールバック（N/A 表示）を考慮。
    - DB が存在しない / テーブルがない場合のエラーハンドリングを実装。

- ユーティリティ
  - utils/process_priority:
    - set_process_priority(level) を実装し、Windows と POSIX 系（Linux/Mac/FreeBSD）で適切な優先度（nice / HIGH_PRIORITY_CLASS）を設定。
    - set_cpu_affinity(cpu_count) によりプロセスを先頭 N コアにピン留めするユーティリティを追加。権限不足・非対応環境では警告を出してスキップする。
    - 失敗時は例外を投げず警告に留める堅牢設計。

### Changed
- 既存モジュールの設計面での明確化:
  - 監視テーブルが存在しない場合でも init_monitoring_db() を各起動スクリプト内で呼び出し、冪等的にテーブル存在を保証。
  - DuckDB をリサーチ・AI の分析・集計用に積極的に利用する方向で統一。

### Fixed
- 環境変数の読み込みと値検証の改善:
  - MONITOR_POLL_INTERVAL の値検証を強化し、0 以下や数値でない場合はデフォルトにフォールバックして警告を出すように修正。
  - Settings.env / log_level / PAPER_FILL_MODE 等のプロパティで不正値を検出して明示的に ValueError を投げるようにし、起動時の誤設定を早期発見可能にした。

### Security
- API キー等の必須値は Settings._require を通じて未設定時に ValueError を発生させる仕様にし、暗黙の空文字運用を避ける（例: OpenAI API キーのチェックは score_news でも実施）。

---

変更の背景や注意事項、今後の作業
- news_nlp の残作業（score_news の完成、API レスポンス検証・DB 書き込み処理の実装）が必須。実運用前に追加開発と入念なリトライ/エラーシナリオのテストが必要です。
- position_sizing と apply_sector_cap にある TODO は資金配分の安全性に関わるため優先的対応を推奨します（前日終値や取得原価でのフォールバック、銘柄ごとの lot_size）。
- クロスプラットフォーム（特にプロセス優先度・CPU affinity）は環境（コンテナ / 権限）によって挙動が異なるため、運用環境での確認を推奨します。
- DuckDB のバージョン依存の挙動や executemany の制約について、運用環境での確認を行ってください。

---

（注）本 CHANGELOG は提示されたソースコードから推測して作成しています。実際のリリース履歴や意図した変更内容が異なる場合がありますので、必要に応じてプロジェクト関係者とすり合わせてください。