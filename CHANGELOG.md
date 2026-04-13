# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-04-13
初回リリース — 基本機能一式を追加。

### 追加 (Added)
- 全体
  - パッケージ初期リリース。バージョンは `0.1.0`。
  - モジュール設計方針として「外部 API へ不用意にアクセスしない」「DuckDB / SQLite を中心としたローカルデータ処理」「純粋関数の採用（副作用を限定）」を明示。
- 実行・監視
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite を使用し、本番 DB と分離して動作。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - DuckDB 接続を受け取りデータ参照を可能に。
    - 起動時にプロセス優先度を設定する（utils.process_priority）。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用。
    - プロセス優先度を最初に High に設定。
- 設定管理
  - config.Settings クラスを導入。
    - .env / .env.local の自動ロード（OS 環境変数優先、`.git` または `pyproject.toml` を基準にプロジェクトルートを探索）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - 環境変数のパース機能（export 形式、クォート、エスケープ、インラインコメントの取り扱い）を実装。
    - 各種プロパティを提供（J-Quants / kabu / LINE / DB パス / 監視閾値 / PID・kill flag パス / 環境名・ログレベル・フラグ判定など）。
    - `PAPER_FILL_MODE` の妥当性チェック（instant/partial/never/reject）。
    - `KABUSYS_ENV` と `LOG_LEVEL` の妥当性チェック。
- ポートフォリオ構築（portfolio）
  - portfolio_builder: シグナル選定と重み付け関数を追加。
    - select_candidates: スコア降順 + タイブレークで上位 N 件を選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。スコア全て 0 の場合は等金額にフォールバックして警告を出力。
  - risk_adjustment: セクター上限とレジーム乗数を実装。
    - apply_sector_cap: 既存保有・価格マップに基づくセクター露出を計算し、上限を超えるセクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバック（警告）。
  - position_sizing: 発注株数計算ロジックを実装。
    - risk_based / equal / score の割当方式をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケールダウン）、cost_buffer を考慮した保守的見積り、残差分を lot 単位で再配分するロジック等を実装。
- 研究モジュール（research）
  - factor_research: モメンタム / ボラティリティ / バリュー系ファクター計算を追加。
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率を計算（必要行数不足時は None）。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比を計算（欠損制御あり）。
    - calc_value: raw_financials から最新財務を取り、PER/ROE を算出（EPS が 0/欠損時は None）。
    - 全関数 DuckDB 接続を受け取り prices_daily / raw_financials を参照。
  - feature_exploration: 将来リターン・IC・統計サマリー等のユーティリティを追加。
    - calc_forward_returns: 指定ホライズン（デフォルト 1/5/21 営業日）の将来リターンを計算。
    - calc_ic / rank / factor_summary: スピアマン IC、ランク付け（同順位の平均ランク処理）、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - 外部ライブラリに依存しない純 Python 実装。
- ニュース NLP（ai）
  - news_nlp: raw_news を OpenAI API でスコアリングして ai_scores テーブルへ書き込む処理を追加（gpt-4o-mini を想定）。
    - 記事集約（タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST、UTC に変換して比較）。
    - 1 銘柄あたり記事最大数 / 文字数制限（トリム）を実装してトークン膨張対策。
    - 最大 20 銘柄ずつのバッチ送信、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリップ、部分成功時の DB 保護（対象コードのみ DELETE→INSERT）などフェイルセーフを考慮。
    - OpenAI API キーは引数または環境変数 `OPENAI_API_KEY` から取得（未設定時は ValueError）。
    - 実行に関する定数（バッチサイズ、モデル名、リトライ回数、ウィンドウ定義等）を明示。
    - ルックアヘッドバイアスを避けるため datetime.today() / date.today() を参照しない方針を明記。
- ユーティリティ
  - utils.process_priority: プロセス優先度 / CPU affinity 設定ユーティリティを追加。
    - Windows（psutil の priority constants）と POSIX（nice 値）を吸収する実装。
    - set_process_priority(level) / set_cpu_affinity(cpu_count) を提供。権限不足や未対応 OS は警告でスキップ。
  - __init__.py にパッケージ情報（__version__ = "0.1.0"）を追加。
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成ツールを追加。
    - SQLite（デフォルト data/paper_trading.db）からシステム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）等を集計して標準出力に表示。
    - 判定基準（稼働率 >= 99%, 成功率 >= 90%, 送信率 >= 95%, P95 レイテンシ <= 200 ms）を定義し PASS/FAIL 判定を出力。
    - 日付フィルタ（--from / --to）および --db オプションをサポート。DB が存在しない場合のエラーメッセージを実装。
    - P95 計算ユーティリティを実装（空リストは None を返す）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- OpenAI API キーの取り扱いは環境変数または明示引数に限定（未設定時はエラー）。ただし、キーのログ出力は行わない実装方針。

注記:
- 多くの関数は「DB 参照なしの純粋関数」や「DuckDB 接続を受ける設計」など、テスト・再現性を考慮した構成になっています。
- 実行時の権限不足（プロセス優先度設定や CPU affinity）は警告でスキップされるため、非特権環境でも動作可能です。
- 将来的な拡張点（例: lot_size の銘柄別対応、apply_sector_cap の価格フォールバックなど）はコード内に TODO コメントとして記載されています。