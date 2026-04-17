# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

※この CHANGELOG は提供されたコードベースの内容から推測して作成しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-17

初回リリース。システム全体の以下主要機能を実装 / 導入しました。

### Added
- 全体
  - パッケージ kubusys を初期実装。バージョンは 0.1.0（src/kabusys/__init__.py）。
  - 環境変数 / .env の読み込みと設定管理を行う Settings クラスを実装（src/kabusys/config.py）。
    - 自動 .env / .env.local ロード機能（プロジェクトルート検出ロジック含む）。
    - .env のパースはクォート・エスケープ・コメントを考慮した柔軟な実装。
    - 必須変数の検出用 _require ユーティリティ、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑止に対応。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定等）。
    - PAPER_FILL_MODE の検証（有効値: instant/partial/never/reject）等。

- 実行基盤
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB（data/paper_trading.db をデフォルト）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を介したブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立てを行い ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）と pid ファイル管理、デーモンスレッドでの実行監視に対応。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。

  - SystemMonitor ポーリング起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバック。
    - Monitoring は環境にかかわらず本番用 sqlite_path を使用して監視データを記録。
    - 停止フラグ検知によるループ終了、例外発生時のログ出力／ループ継続を行う安全設計。
    - 起動時にプロセス優先度を "high" に設定。

  - 監視 DB の初期化ユーティリティ呼び出し（init_monitoring_db を利用して冪等に監視テーブルを保証）。

- ポートフォリオ構成（純粋関数モジュール）
  - 銘柄選定と配分
    - select_candidates: スコア降順＋シグナルランクで候補選定（src/kabusys/portfolio/portfolio_builder.py）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコアが全て 0 の場合は等金額にフォールバック）。
  - リスク調整
    - apply_sector_cap: セクターごとのエクスポージャー計算と候補除外ロジック（売却予定銘柄を除外可能、unknown セクターは上限適用外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）と未知レジームでのフォールバック。
  - ポジションサイズ決定
    - calc_position_sizes: risk_based / equal / score 各方式に対応。単元株（lot_size）で丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap スケーリングを実装。

- リサーチ / 特徴量
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（MA200）を計算。
    - calc_volatility: 20日 ATR、相対ATR、平均売買代金、出来高比率を計算（true_range の NULL 伝播を厳密に扱う）。
    - calc_value: raw_financials と株価から PER / ROE を計算（target_date 以前の最新財務データを取得）。
    - いずれも DuckDB 接続を受け SQL で効率的に処理。データ不足時は None を返す。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズンでの将来リターン（1/5/21 営業日をデフォルト）を計算。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算（同順位の平均ランク処理含む）。
    - factor_summary / rank: 基本統計量とランク付けユーティリティを実装。
  - research パッケージの __all__ エクスポートに zscore_normalize（kabusys.data.stats 経由）などを含めた公開 API を整備。

- AI / ニュース NLP（初期実装）
  - ニュースを OpenAI (gpt-4o-mini) でセンチメント採点し ai_scores テーブルに書き込むモジュールを追加（src/kabusys/ai/news_nlp.py）。
    - ニュース収集ウィンドウ（JST）定義、銘柄ごとの記事集約、トークン肥大化対策（記事数／文字数上限）、バッチ送信（最大 20 銘柄）、JSON Mode 出力厳格化、スコアの ±1.0 クリップ。
    - 429/ネットワーク/5xx に対する指数バックオフ・リトライ、失敗時は部分スキップして継続するフェイルセーフ設計。
    - API キー未設定時は例外を投げる（呼び出し側で明示的にキーを渡すか OPENAI_API_KEY を設定する必要あり）。
    - （注）ファイル末尾が断片的に提供されているため一部処理が未完（提供コードに依存）。

- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収して set_process_priority(level) を提供（high/normal/low）。
    - set_cpu_affinity(cpu_count) で最初の N コアにピン固定。権限不足や未対応環境では警告を出してスキップ。
    - psutil の AccessDenied/NotImplemented を安全にハンドリング。

- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）。
    - コマンドラインで期間指定 (--from/--to) や DB パス指定 (--db) が可能。
    - system_status / trade_logs / risk_logs テーブルを参照して稼働率・注文成功率・送信率・レイテンシ（P95）等を集計。
    - PASS/FAIL 判定基準（稼働率 99% 以上、成立率 90% 以上、送信率 95% 以上、P95レイテンシ <= 200ms）を導入。
    - P95 計算、欠損ハンドリング（テーブルが存在しない場合のフォールバック）を実装。

### Changed
- なし（初回リリースのため該当なし）

### Fixed
- なし（初回リリースのため該当なし）

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キーは明示的に渡すか環境変数 OPENAI_API_KEY を利用する設計。キー未設定時は処理を明示的に失敗させるため、誤って無許可で API キーを使うリスクを低減。

## 注記 / マイグレーション
- 環境変数
  - KABUSYS_ENV の有効値は development / paper_trading / live のいずれか。無効値での起動はエラーになります。
  - .env 自動読み込みはデフォルトで有効。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - Monitoring のポーリング間隔は MONITOR_POLL_INTERVAL 環境変数でオーバーライド可能（正の整数、デフォルト 60 秒）。不正値時は警告を出してデフォルトを使用します。
  - Paper Trading 用 DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）で分離されています。
  - PID / STOP / KILL フラグによるプロセス制御（data/*.flag, data/*.pid）に対応しています。運用スクリプトから停止フラグを作成すると安全に終了します。
  - PAPER_FILL_MODE の値は instant/partial/never/reject のいずれか。誤った値は起動時に ValueError を発生させます。

- DB スキーマ
  - 監視・トレードログ・リスクログ・ai_scores 等のテーブルを前提とした処理を行います。初回起動時に監視テーブルが存在しない場合は init_monitoring_db により作成されます（冪等）。

- 未実装 / 既知の制約
  - news_nlp モジュールはファイル末尾が断片的（提供コード切れ）なため、実行前に完全実装が必要です。
  - position_sizing の lot_size は現状グローバル固定（デフォルト 100）。将来的には銘柄別単位での拡張が予定されています（TODO コメントあり）。
  - calc_regime_multiplier の bear 動作は戦略側で通常 buy シグナルが生成されない設計になっているため補助的な guard として実装されています。

---

作成：自動生成（コードベースの内容から推測）  
注意：上記は提供されたソースコードから推測してまとめた CHANGELOG です。実際のコミット履歴や差分がある場合はそれに合わせて更新してください。