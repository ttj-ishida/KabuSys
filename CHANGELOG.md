# CHANGELOG

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」フォーマットに準拠しています。

フォーマットのポリシー: 互換性のない変更は Breaking Change として明示し、機能追加・改善・修正をカテゴリ別に分けて記載します。

## [Unreleased]

（現時点では未リリースの変更はありません）

---

## [0.1.0] - 2026-04-17

最初の公開リリース。自動売買システム KabuSys のコア機能群を追加しました。
以下はコードベースから推測できる主な機能追加・設計上の要点です。

### 追加 (Added)
- 一般
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
  - Settings クラスを実装し、環境変数 / .env(.local) の自動読み込み・検証を提供。
    - .env ファイルのパース（コメント、export 形式、引用符・エスケープ対応）に対応。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - 必須環境変数未設定時に明示的なエラーを投げるユーティリティを提供。

- 実行系
  - run_execution.py：ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV による paper_trading の分離（paper_trading 用専用 SQLite DB を使用）。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）検知による安全な停止処理をサポート。
    - 実行 PID ファイル（data/execution.pid）の管理を考慮。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit 等）を記載。

  - run_monitoring.py：SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト 60 秒、無効値はフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視データは本番DBへ集約）。
    - 停止フラグ検知でループを終了、例外発生時もログ出力して次回ポーリングを継続。
    - 起動時にプロセス優先度を high に設定（set_process_priority 呼び出し）。

- 監視 / DB
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）を実行開始時に呼び出すことで、監視テーブルの存在を保証（冪等）。

- ポートフォリオ構築
  - portfolio.portfolio_builder：シグナル選定（select_candidates）と重み計算（等金額・スコア加重）を実装。
    - スコア同点時のタイブレーク（signal_rank）をサポート。
    - 全スコアが 0 の場合に等配分へフォールバック。

  - portfolio.risk_adjustment：セクター集中上限適用（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。
    - 既存保有・売却予定銘柄を考慮したセクターエクスポージャー算出。
    - 不明セクター ("unknown") はセクター上限の対象外として扱う。

  - portfolio.position_sizing：発注株数決定ロジック（calc_position_sizes）を実装。
    - allocation_method による "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金を超える場合のスケーリング）を実装。
    - cost_buffer による手数料・スリッページの保守的見積りを考慮。
    - スケールダウン時の再配分ロジック（端数の大きい順に lot 単位で追加）を実装。

- ユーティリティ
  - utils.process_priority：クロスプラットフォームのプロセス優先度設定と CPU affinity 設定を実装（Windows / POSIX を吸収）。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。
    - アクセス拒否や未対応環境では警告ログを出して失敗をスキップ。

- リサーチ / ファクター計算
  - research.factor_research：
    - momentum（1M/3M/6M リターン、MA200乖離）、volatility（ATR20、相対ATR、出来高指標）、value（PER, ROE）計算関数を追加。
    - DuckDB による SQL ベースでの計算を採用。欠損データやウィンドウ不足時の扱いを明確化。

  - research.feature_exploration：
    - 将来リターン（calc_forward_returns）、IC（calc_ic / Spearman ランク相関）、ランク変換、ファクター統計サマリーを実装。
    - 外部ライブラリ非依存（標準ライブラリのみで実装）。

  - research パッケージは data.stats の zscore_normalize を re-export。

- ツール
  - tools.paper_verification_report：Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を集計して PASS/FAIL 判定を出力。
    - 日付フィルタ (--from / --to) と DB パス指定 (--db) をサポート。
    - P95 計算、各種閾値（稼働率 99%, 成功率 90% 等）を定義。

- AI ニュース NLP
  - ai.news_nlp：ニュース記事を OpenAI（gpt-4o-mini）でスコアリングして ai_scores テーブルへ書き込むロジックを実装。
    - 時間ウィンドウの算出（JST ベースの前日 15:00 〜 当日 08:30）と DuckDB からの集約。
    - バッチ送信（最大 20 銘柄 / コール）、JSON Mode 指定、リトライ（429/ネットワーク/5xx に対する指数バックオフ）を考慮。
    - レスポンスのバリデーション、スコアの ±1.0 クリップ、部分更新（対象コードのみ DELETE → INSERT）で部分失敗時の既存データ保護。
    - 注意: ファイル末尾が途中で切れている（コードが途中で終端している断片あり）。実行前に未実装箇所の補完が必要。

### 変更 (Changed)
- Settings 側で各種検証ロジックを追加
  - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE に対する許容値チェックを実装（無効値で ValueError）。
  - データベースパスや PID ファイルパス等を Path オブジェクトで取り扱い expanduser 対応。

- run_monitoring / run_execution
  - 起動直後にプロセス優先度を上げる（set_process_priority("high")）ことで実行安定性を向上。
  - DuckDB と SQLite の両方を使用する設計に統一（分析用に DuckDB、状態は SQLite）。

- エラーハンドリング
  - long-running なループやスレッド監視箇所で例外をログに残しつつ処理を継続する方針を採用（フェイルセーフ）。

### 修正 (Fixed)
- .env パーサーの強化により以下を修正・対応
  - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの扱いを改善。
  - override ロジックで OS 環境変数を protected として上書き防止する仕様を導入。

- position_sizing のスケーリングロジックで
  - lot 単位での丸め・残差処理、上限チェック、残余キャッシュを使った追加配分を実装して配分の再現性と安全性を確保。

### 注意 (Notes / Known issues)
- ai/news_nlp.py のソースが途中で切れている（"if not articl" で終端）。このままでは score_news の記事取得部分以降が未完成のため、実行時エラーまたは未完実装になります。運用前に該当箇所を補完してください。
- 一部 TODO コメントあり（例: position_sizing の lot_size を銘柄別にする拡張、apply_sector_cap の price フォールバック等）。将来的な改善候補です。

### セキュリティ (Security)
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を発生させる明示的なチェックを実装（秘匿性の扱いは呼び出し側で管理）。

---

今後のリリースでは、ai/news_nlp の完成、テストカバレッジ追加、エラーハンドリング強化、運用用のドキュメントやデプロイ手順の追加を予定してください。