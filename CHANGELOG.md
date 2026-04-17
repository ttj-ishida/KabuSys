# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。  
日時はリリース日として 2026-04-17 を使用しています（コードベースから推定）。

なお、本 CHANGELOG はリポジトリ内のソースコードから実装内容を推測して作成しています。実際のコミット履歴ではありません。

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 全体
  - 初期公開相当の機能群を実装。
  - パッケージメタ情報として `kabusys.__version__ = "0.1.0"` を設定。

- 起動スクリプト
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）検知で安全終了。
  - `run_execution.py`：ExecutionEngine 起動スクリプトを追加。`paper_trading` 環境では MockBroker を使用して paper_trading 用 DB（data/paper_trading.db）へ完全分離して記録。プロセス優先度設定、PID ファイル処理、停止フラグ検知による安全停止を実装。

- 設定・環境変数ロード
  - `config.py`：.env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml から自動検出）。`.env` → `.env.local` の順で読み込み、OS 環境変数を保護（上書き禁止）する仕組みを導入。
  - 環境変数パーサの強化：`export KEY=val` 形式、クォート（シングル/ダブル）とバックスラッシュエスケープ、インラインコメントの取り扱いなどに対応。
  - `Settings` クラスを実装し、各種設定（DB パス、API トークン、監視閾値、環境判定など）をプロパティで提供。

- ポートフォリオ構築（純粋関数群）
  - `portfolio.portfolio_builder`：BUY シグナル選定（スコア降順・タイブレーク）、等金額配分（equal）、スコア加重配分（score）を実装。
  - `portfolio.risk_adjustment`：セクター集中上限の適用（既存保有を考慮した除外）、市場レジームに応じた乗数（bull/neutral/bear）を実装。
  - `portfolio.position_sizing`：株数決定ロジック（risk_based / equal / score）を実装。単元株丸め、per-position 上限、aggregate cap（投下資金スケーリング）、cost_buffer を考慮した保守的見積り、残差処理による追加配分を実装。

- 研究・リサーチ
  - `research.factor_research`：モメンタム（1M/3M/6M / MA200乖離）、ボラティリティ（ATR20・相対ATR・平均売買代金・出来高比率）、バリュー（PER/ROE）を DuckDB 上の prices_daily / raw_financials から計算する関数を追加。
  - `research.feature_exploration`：将来リターン計算（複数ホライズン対応）、Spearman ランク相関による IC 計算、ファクター統計サマリ、ランク変換ユーティリティを追加。標準ライブラリのみで完結する設計。

- ニュース NLP（AI）
  - `ai.news_nlp`：raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む機能を追加。バッチ処理（最大 20 銘柄/回）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコア ±1.0 でクリップなどの安全機構を実装。
  - ニュース対象ウィンドウ計算を実装（target_date の前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して比較）。

- ユーティリティ
  - `utils.process_priority`：Windows・POSIX の差を吸収してプロセス優先度を設定するユーティリティを追加。CPU affinity を固定する set_cpu_affinity も実装（アクセス権限がない場合は警告してスキップ）。

- ツール
  - `tools.paper_verification_report`：Paper Trading の検証レポート生成 CLI を追加。稼働率・注文成功率・送信率・P95 レイテンシ等の指標を集計し、閾値に基づく PASS/FAIL 判定を出力。コマンドライン引数で期間指定可能（--from, --to, --db）。

- DB 初期化 / 監視
  - `monitoring.monitoring_db.init_monitoring_db` を参照するコードが複数の起動スクリプトで呼ばれ、監視テーブルが存在することを保証（冪等処理）。

### 変更 (Changed)
- 環境依存の挙動
  - 監視プロセス（run_monitoring）は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する旨を明示。対して実行エンジン（run_execution）は paper_trading 環境時に専用 DB を使用して本番と完全に分離する動作を確立。

- エラーハンドリング・フォールバック
  - 環境変数数値パースの堅牢化：MONITOR_POLL_INTERVAL の不正値（0 以下や非数値）はデフォルトにフォールバックして警告を出力。time.sleep に渡す不正値による例外回避。
  - 各種ファクター / 集計関数はデータ不足時に None を返す等の安全なフォールバックを実装（例: ma200 が不足、ATR の行不足、created_count==0 時の扱いなど）。
  - calc_score_weights は全銘柄のスコア合計が 0 の場合に警告を吐いて等金額配分へフォールバック。

- ロギング／起動順序
  - run_* スクリプトで起動時にプロセス優先度を最初に設定するよう変更（高優先度を試みる）。PID ファイル / stop flag チェックのタイミングによる安全性向上。

- SQL / DuckDB クエリ
  - Research モジュールの SQL を最適化（1クエリでまとめて取得、ウィンドウサイズを限定してスキャン範囲を縮小する工夫）。

### 修正 (Fixed)
- ポジションサイズ計算の丸め・スケール処理
  - lot_size 単位での丸め処理と aggregate cap 適用時のスケールダウン処理において、残差（fractional_remainder）を考慮して残余キャッシュで追加配分するロジックを導入し、配分の再現性と公平性を向上。
  - 価格が欠損（<=0）の場合にスキップするガードを追加してゼロ除算や不正なサイズ計算を回避。

- ファイル / DB 操作の安全化
  - 起動スクリプトで DB 接続を finally ブロックで確実に閉じるように修正。
  - paper_verification_report で DB ファイルの存在チェックを行い、存在しない場合はユーザ向けに明示的にエラー表示して終了するよう修正。

- process_priority の失敗耐性
  - 権限不足や未実装 API に対しては警告ログを出して処理を継続するよう改善（AccessDenied / NotImplementedError 等をキャッチ）。

### ドキュメント (Documentation)
- 各モジュールに実装意図・設計方針・引数/戻り値の説明を充実させた docstring を追加。特にポートフォリオ構築・リスク調整・研究モジュール・AI スコアリングに詳細な注釈を記載。
- tools.paper_verification_report に使用例と閾値（PASS/FAIL 基準）を明示。

### セキュリティ (Security)
- OpenAI API キーの扱いは引数優先 → 環境変数参照の順で解決。未設定時は ValueError を送出して明示的に処理を中断することで、暗黙のキー漏洩等を避ける設計。

### 既知の制約 / 注意点 (Known issues / Notes)
- `ai.news_nlp` のバッチ収集 / 書き込み部は堅牢化されているが、大量データや部分失敗時のトランザクション分割に関する詳細なテストが推奨される（部分失敗時は既存スコア保護のためコード絞り込みで置換する設計）。
- portfolio.position_sizing の price が欠損（0.0）の場合、現状では exposure が過少見積りされる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO コメントあり。
- .env 自動ロードはプロジェクトルート検出に依存するため、パッケージ化後の特殊な配置では自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を用いることが可能。

---

今後のリリースでは、テストカバレッジの向上、AI スコアリングの部分失敗時の部分的ロールバック処理、銘柄別 lot_size の導入（stocks マスタ連携）、および monitor/execution の運用監視改善（アラート連携等）を想定しています。