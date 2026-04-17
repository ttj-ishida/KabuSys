CHANGELOG
=========

フォーマットは "Keep a Changelog" に準拠しています。
この変更履歴は提示されたコードベースの内容から推測して作成したものです。

Unreleased
----------

Added
- 環境・設定管理を強化（src/kabusys/config.py）
  - プロジェクトルート自動検出機能を追加し、.env/.env.local の自動読み込みをサポート（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env のパーサーを拡張：export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメント処理に対応。
  - Settings クラスで各種設定プロパティを提供（DB パス、Paper Trading 関連、監視閾値、ログレベル等）。
  - PAPER_FILL_MODE の値検証を追加（instant/partial/never/reject のみ許容）。

- 実行・監視ランナーの改善
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）
    - KABUSYS_ENV=paper_trading 時に paper_trading 用の SQLite を使用して本番 DB と分離。
    - BrokerClientFactory を利用したブローカー抽象化。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）の取り扱いを実装。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（不正値はデフォルト 60 秒にフォールバック）。
    - 環境に依らず本番 sqlite_path を監視 DB に使用し、SystemMonitor を使った単発チェックをループ実行。

- プロセス制御ユーティリティを追加（src/kabusys/utils/process_priority.py）
  - Windows と POSIX 系（Linux / Darwin / FreeBSD）に対応したプロセス優先度設定（high/normal/low）。
  - CPU affinity を最初の N コアに固定するユーティリティを追加（アクセス権限や未サポート環境では警告を出してスキップ）。

- ポートフォリオ構築関連の純粋関数群を追加（src/kabusys/portfolio/*）
  - 銘柄選定と重み計算（select_candidates / calc_equal_weights / calc_score_weights）。
  - セクター集中制限とレジーム乗数（apply_sector_cap / calc_regime_multiplier）。
  - 株数決定ロジック（calc_position_sizes）
    - risk_based、equal、score の allocation 方法を実装。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（全銘柄合計が利用可能現金を超えた場合のスケーリング）および残差処理を実装。
    - cost_buffer による手数料・スリッページ見積りを考慮。

- リサーチ・ファクター計算（src/kabusys/research/*）
  - DuckDB を利用したファクター計算モジュール（calc_momentum, calc_volatility, calc_value）。
    - Momentum: 1M/3M/6M リターン、MA200 乖離。
    - Volatility: ATR20、相対 ATR、20日平均売買代金、出来高変化率。
    - Value: PER（EPS に依存）、ROE（raw_financials から取得）。
  - 特徴量探索ツール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク関数（rank）。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- Paper Trading 検証レポートツールを追加（src/kabusys/tools/paper_verification_report.py）
  - 指定期間の system_status / trade_logs / risk_logs を集計して稼働率・注文成功率・送信率・レイテンシ（avg/max/P95）を算出し、PASS/FAIL を判定。
  - P95 計算、日付フィルタ、各種閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。

- ニュース NLP スコアリングの基礎を実装（src/kabusys/ai/news_nlp.py）
  - OpenAI API（gpt-4o-mini）を使ったニュースセンチメント集約フローの設計と一部実装。
  - タイムウィンドウ計算（JST 基準 → UTC 変換）、記事集約・トリムルール（記事数・文字数上限）、バッチ送信、レスポンス検証、スコアのクリップ等を設計。
  - ルックアヘッドバイアス防止のため date.today()/datetime.today() を参照しない設計思想を明記。
  - （注）ファイル末尾が切れているため一部処理は未掲載。リトライ・バックオフ・部分コミットの設計は記載あり。

Changed
- パッケージメタ情報/エクスポートを追加（src/kabusys/__init__.py）
  - __version__ を "0.1.0" に設定。
  - __all__ で主要サブパッケージを公開。

Fixed
- 環境変数の厳密な検証を追加
  - MONITOR_POLL_INTERVAL が不正（非数値や 0 以下）の場合に警告してデフォルトにフォールバック（run_monitoring）。
  - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の不正値で早期に明確なエラーを出す (Settings)。

- DB 初期化の冪等性保証
  - init_monitoring_db を呼び出して監視用テーブルの存在を担保（監視/実行ランナーで共通処理）。

- 安全性・耐障害性の向上
  - process_priority の設定で権限不足や未対応 OS の場合は警告を出して処理を継続するように修正。
  - ExecutionEngine・監視ループが例外を拾ってログ出力し続行するように（監視は check_once() の例外を捕捉して次ループへ）。

Known issues / Notes
- ai/news_nlp.py はファイル末尾が切れており、_fetch_articles 等の内部実装が提示されていません。OpenAI 呼び出し周りの実行部分は設計がある一方で、完全実装と統合テストが必要です。
- position_sizing の price のフォールバック（price が欠損時の扱い）は TODO コメントあり。前日終値や取得原価を用いる等の改善が検討中。
- DuckDB を利用する関数群はテーブルスキーマ（prices_daily/raw_financials 等）に依存します。実運用前にスキーマ整合性の確認が必要です。

0.1.0 - 2026-04-17
------------------
Added
- 初期リリース相当の機能群を追加：
  - 環境設定ロード／Settings（.env 自動読み込み、検証）
  - 実行エンジン起動・監視ループスクリプト
  - プロセス優先度 / CPU affinity ユーティリティ
  - ポートフォリオ構築（選定・重み付け・リスク調整・ポジションサイズ）
  - リサーチ用ファクター計算（モメンタム/ボラティリティ/バリュー）および特徴量解析ユーティリティ
  - Paper Trading 検証レポートツール
  - ニュース NLP スコアリング（設計および一部実装）
  - DuckDB / SQLite を用いたローカル分析・監視データ連携

Security
- なし（コードから推測できる直接的なセキュリティ修正は検出されませんでした）。ただし、OpenAI API キーや各種シークレットは環境変数管理を前提としているため、運用時には適切なシークレット管理を推奨します。

---

補足:
- 本 CHANGELOG は提示されたソースコードから推測して作成したものであり、実際のコミット履歴や意図と異なる場合があります。必要であれば、リリースごとのコミットログやチケット情報に基づいた正確な履歴化を支援します。