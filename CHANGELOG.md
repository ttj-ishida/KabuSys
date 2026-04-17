# Changelog

すべての変更は Keep a Changelog の仕様に準拠して記載しています。日付はリリース日を示します。

## [0.1.0] - 2026-04-17

初回リリース。日本株自動売買システム「KabuSys」の基本機能群を実装しました。以下はコードベースから推測できる主な追加点・改善点・既知の注意点です。

### Added
- 全体
  - パッケージ初期化とバージョン管理（kabusys.__version__ = 0.1.0）。
  - Settings クラスによる環境変数ベースの設定管理（自動 .env 読み込み機能を含む）。
  - .env 自動ロードの優先順位: OS 環境変数 > .env.local > .env。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサーの実装（export 形式やクォート・バックスラッシュのエスケープ、インラインコメント処理に対応）。

- 実行／監視
  - run_execution.py — ExecutionEngine 起動スクリプトを実装。
    - 本番と Paper Trading を分離（`KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、`data/paper_trading.db` に記録）。
    - PID ファイル管理、停止フラグ（data/stop_requested.flag）による安全停止対応。
    - 起動時にプロセス優先度を "high" に設定（utils/process_priority.set_process_priority を利用）。
    - ExecutionEngine の組み立て（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler 等）。
    - RiskManager にデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を組み込み。初期ポートフォリオ値はブローカーの利用可能現金を利用。

  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプトを実装。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒、0 以下や無効値は警告のうえデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番用の `sqlite_path` を使用して動作（監視 DB の分離は行わない設計）。
    - 停止フラグ / flag ファイルの検知でループを終了。
    - 監視用 DB 初期化（init_monitoring_db）を起動時に実行して監視テーブルの存在を保証。

- データ・リサーチ
  - research.factor_research モジュール
    - モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（ATR20、相対 ATR、出来高指標）、バリュー（PER、ROE）を DuckDB の prices_daily / raw_financials テーブルから計算する関数を実装。
    - データ不足時の None の取り扱いや行数チェック（例: MA200 のサンプル数チェック）を実装。

  - research.feature_exploration モジュール
    - 将来リターン（複数ホライズン）計算、IC（Spearman の ρ）計算、ファクター統計サマリーの純粋関数を実装。
    - pandas 等外部依存を使わず標準ライブラリと DuckDB で実装。
    - rank メソッドは同順位の平均ランク付けを行い丸め誤差対策あり。

- ポートフォリオ構築
  - portfolio.portfolio_builder
    - 候補選定（スコア降順・タイブレークは signal_rank）、等金額配分、スコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）を実装。
  - portfolio.risk_adjustment
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター別時価から上限を超えるセクターの新規候補を除外。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear のマップ、未知のレジームは 1.0 にフォールバックし警告）。
  - portfolio.position_sizing
    - 株数決定ロジックを実装（risk_based / equal / score）。単位 lot_size（デフォルト 100）で丸め、per-stock 上限・aggregate cap（available_cash）を考慮したスケーリングロジックを実装。
    - cost_buffer による保守的なコスト見積り、端数処理の再配分ロジック（残余キャッシュで lot 単位を追加）を実装。

- AI / ニュース
  - ai.news_nlp モジュール（OpenAI を用いたニュースセンチメントスコアリング）
    - ニュース収集ウィンドウ計算（JST ベースの前日 15:00 ～ 当日 08:30 の UTC 変換）。
    - raw_news / news_symbols を集約して銘柄別テキストを生成、最大記事数・文字数のトリム処理を実装。
    - OpenAI（gpt-4o-mini）へのバッチ送信（1 API コールあたり最大 20 銘柄）、JSON Mode の期待出力、スコアの ±1.0 クリップ、429/ネットワーク/5xx の指数バックオフリトライ実装を含む堅牢化。
    - API キーの明示（引数 or 環境変数 OPENAI_API_KEY）が必須で、未設定時は ValueError を送出。
    - 部分失敗時でも他銘柄の既存スコアを保護するため、更新は対象コードを限定して置換（DELETE→INSERT）する設計。

- ツール
  - tools.paper_verification_report — Paper Trading の検証レポート生成 CLI を追加。
    - デフォルト DB: data/paper_trading.db（環境変数で上書き可能）。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどの指標を集計し、閾値に基づく PASS/FAIL 判定を出力。
    - 日付範囲フィルタ（--from / --to）に対応。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level) によるクロスプラットフォーム（Windows / POSIX）プロセス優先度設定に対応（psutil 利用）。
    - set_cpu_affinity(cpu_count) による CPU affinity 固定機能を追加。
    - アクセス権限や未対応 OS 時は警告を出して安全にスキップする実装。

### Changed
- ログ設定: 実行スクリプト起動時に logging.basicConfig(level=logging.INFO) を設定しているため、デフォルトのログレベルは INFO。
- 起動時にプロセス優先度を "high" に自動設定する挙動（run_execution / run_monitoring）。
- 監視（monitoring）初期化処理で init_monitoring_db を必ず呼び、監視用テーブルの存在を保証する設計（冪等性を意識）。

### Fixed / Hardening
- MONITOR_POLL_INTERVAL の値検証を追加。0 以下や整数化できない値は警告しデフォルト（60 秒）にフォールバックして、time.sleep に渡すことでの例外発生を回避。
- .env パーサーの強化:
  - export 前置の対応、クォート文字列内でのバックスラッシュエスケープ処理、インラインコメントの判定ルールを改善。
  - 誤った行は無視して安全に処理を継続。
- DuckDB / SQLite クエリ部分はデータ不足やテーブル未存在時に sqlite3.OperationalError を捕捉してデフォルト値で継続するよう保護（tools.paper_verification_report など）。
- ポジションサイジングで価格欠損（price が None や <=0）時にスキップするログ出力を追加して誤った計算を防止。

### Deprecated
- なし（初回リリースのため該当なし）。

### Removed
- なし（初回リリースのため該当なし）。

### Security
- OpenAI API キーは明示的に引数または環境変数 `OPENAI_API_KEY` から供給する必要がある旨を明記。API キー未設定時は処理を中止して ValueError を送出。

### Known issues / Notes（実装上の注意）
- ai.news_nlp モジュールは堅牢化を意識した設計となっているが、API 呼び出し周りはレート制限や費用に注意してください。複数銘柄バッチ処理時のプロンプト長・トークン制限は運用で確認してください。
- portfolio.position_sizing は現状 lot_size を全銘柄共通で扱う設計（将来的に銘柄別 lot_map へ拡張予定）。また price のフォールバック（前日終値や取得原価）が未実装のため、price 欠損時はスキップされる点に注意。
- calc_regime_multiplier は未知のレジームで 1.0 にフォールバックして警告を出す実装。未知レジームの扱い方はプロダクション運用方針で要検討。
- run_monitoring は「監視は常に本番 sqlite_path を使用する」設計になっているため、テスト環境での監視動作分離が必要な場合は設定を調整してください。
- 一部ドキュメントや TODO コメントが残っており、将来的な拡張（銘柄別 lot_size、価格フォールバック、AI レスポンス検証強化など）が予定されています。

---

この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のコミット履歴や設計文書がある場合は、それらに基づいて追記・修正してください。