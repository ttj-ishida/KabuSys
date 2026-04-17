# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

## [0.1.0] - 2026-04-17

### 追加
- 基本パッケージ初期リリース（バージョンを __init__.py にて 0.1.0 に設定）。
- 環境・設定関連
  - Settings クラスによる環境変数駆動の設定読み取りを実装（kabusys/config.py）。
    - 自動 .env ロード機能: プロジェクトルート（.git もしくは pyproject.toml）を探索して `.env` / `.env.local` を読み込む（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応）。
    - .env のパースは引用符・エスケープ・export 形式・行内コメント等に対応。
    - 各種設定用プロパティ（DB パス、PID/kill フラグパス、paper_trading 用 DB パス・fill モード、閾値など）を提供。
  - 対話式環境セットアップ CLI（kabusys/config_setup.py）を追加。
    - `.env` の初期作成・更新ウィザード。機密項目は表示をマスクして入力。ファイル書き出しテンプレートを提供。
  - 設定検証 CLI（kabusys/validate_config.py）を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ確認、config/*.yaml の存在確認（PyYAML があればパース検証）、
      本番環境向けのガード（LINE 設定・Kill フラグ挙動）など。
    - --strict オプションで警告を FAIL 扱いにできる。
- 実行/監視ランナー
  - 実行エンジン起動スクリプト（kabusys/run_execution.py）
    - プロセス優先度を高に設定して起動。
    - KABUSYS_ENV が paper_trading の場合は専用の paper DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - BrokerClientFactory を使ってブローカークライアントを生成（paper_trading 時は MockBroker を使う想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）による安全停止、pid ファイル管理。
    - RiskManager の初期設定値（max_position_pct 等）をコード上で定義。
  - 監視ループ起動スクリプト（kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番の sqlite_path を参照して監視 DB を初期化。
    - stop フラグでループ終了、例外発生時はログ出力して次ポーリングまで待機。
- モニタリング DB 初期化（監視関連の初期化呼び出しを各ランナーから実行）および DuckDB 統合
  - DuckDB 接続を分析用に使用する設計（duckdb_path 設定）。
- portfolio モジュール（銘柄選定・重み付け・株数決定・リスク調整）
  - portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights
    - スコア降順で候補選定、スコアが全て 0 の場合は等金額配分へフォールバック（警告ログ）。
  - risk_adjustment: apply_sector_cap, calc_regime_multiplier
    - セクター集中制限（既存エクスポージャーから上限超過セクターの新規候補除外）。unknown セクターは除外対象外。
    - レジームに応じた投下資金乗数（bull/neutral/bear）を提供。不明レジームは 1.0 でフォールバック（警告）。
  - position_sizing: calc_position_sizes
    - risk_based / equal / score の配分方式をサポート。
    - 単元株（lot_size）丸め、1銘柄上限・全体投下上限（max_utilization）適用、cost_buffer による保守的見積り。
    - aggregate cap を超えた場合のスケーリングと端数処理（lot 単位で残余キャッシュ配分）。
    - 入力データ欠損（価格なし等）時のログ出力とスキップ処理。
- utils: プロセス優先度・CPU affinity ユーティリティ（kabusys/utils/process_priority.py）
  - Windows / POSIX 系 OS を抽象化して nice/priority を設定。利用権限エラーや未サポート環境では警告を出してスキップ。
  - CPU affinity を最初の N コアに固定する機能を追加（権限不足や未サポート時はスキップ）。
- リサーチ / ファクター計算基盤（kabusys/research/factor_research.py）
  - DuckDB を用いたファクター計算関数（モメンタム、ボラティリティ等）を実装。prices_daily/raw_financials テーブルのみ参照する純粋関数群。
  - MA200、mom_1m/3m/6m、ATR、20 日平均売買代金等を計算。データ不足時は None を返す設計。
- ツール
  - Paper Trading 検証レポート出力スクリプト（kabusys/tools/paper_verification_report.py）
    - SQLite の paper_trading DB から稼働率、注文成功率・送信率、リスク却下数、レイテンシ（avg/max/P95）を集計してレポート表示。
    - PASS/FAIL 基準を定義（稼働率、成功率、送信率、P95 レイテンシ等）。CLI 引数で期間指定・DB パス指定可能。
- ドキュメント/注意
  - config_setup による .env の生成は .env を絶対に Git にコミットしない旨を明記（テンプレートヘッダー）。
  - validate_config により起動前に設定不備や危険な本番設定を検出できる。

### 変更（実装/安全性向上）
- .env ローダーの挙動
  - OS 環境変数を保護するため protected set を導入し、.env.local の上書き等で OS 環境変数を誤って上書かないよう実装。
- .env パーサーの堅牢化
  - シングル/ダブルクォート内のバックスラッシュエスケープ、export KEY=val 形式、行内コメントの扱いなどに対応。
- 実行スクリプトの安全停止
  - 停止フラグ（data/stop_requested.flag）や PID ファイル経由の管理を標準化。監視スクリプト・実行エンジンともに同様の停止ロジックを採用。
- cross-platform のプロセス優先度設定
  - psutil の OS 固有定数に対する安全なフォールバックを実装し、モジュールロードの障害を回避。

### 修正（バグ修正 / 回避策）
- 環境変数の不正値回避
  - MONITOR_POLL_INTERVAL が無効（整数でない / 0 以下）の場合にデフォルト（60 秒）へフォールバックし、ログで警告を出すようにした。
- DB 集計処理の堅牢化
  - paper_verification_report の各クエリを sqlite3.OperationalError で囲み、テーブルが存在しないケースでもレポート生成が致命的にならないようにした。

### 既知の制約 / TODO（今後の改善案）
- position_sizing の lot_size は現状全銘柄共通の仮定（将来的に銘柄別 lot_map へ拡張予定）。
- apply_sector_cap の価格欠損（price が 0.0 の場合）によりエクスポージャが過少評価される可能性があるため、前日終値や取得原価でのフォールバックを検討中。
- research/factor_research の一部処理は大データ向けの最適化／インデックス化が必要な場合がある。
- ExecutionEngine 周り（BrokerClient 実装、Engine の細かい挙動、order_manager/reconciler の詳細）は今後のリリースでテスト強化・拡張予定。

### セキュリティ
- 機密情報（J-Quants トークン、kabu API パスワード、LINE トークン等）は .env に保存する仕様。config_setup のヘッダーで .env を Git にコミットしないよう明記。
- validate_config に本番（KABUSYS_ENV=live）向けの警告チェックを導入。Kill Switch 設定の危険性も警告。

---

今後のリリースでは、テストカバレッジの拡充、ExecutionEngine / Broker の統合テスト、より詳細なドキュメント追加を予定しています。