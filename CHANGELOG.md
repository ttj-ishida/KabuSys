KEEP A CHANGELOG
すべての注目すべき変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

なお、本CHANGELOGは提示されたコードベースの内容から推測して作成しています。実際のコミット履歴や意図とは差異がある可能性があります。

Unreleased
---------
- （現在のワーキングツリーに対する未リリースの変更はここに記載します）

[0.1.0] - 2026-04-17
-------------------
追加 (Added)
- 基本設定/環境変数管理
  - Settings クラスを追加し、アプリケーション設定（KABUSYS_ENV、各種APIキー、DBパス、監視閾値など）をプロパティ経由で取得可能に。
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートの自動検出: .git または pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env ファイルパーサを強化（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。

- 実行/監視用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。paper_trading 環境時は専用 SQLite（data/paper_trading.db）を使用して本番と完全分離。停止フラグ / PID 管理、スレッドでのエンジン実行をサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定可能。起動時にプロセス優先度を上げ、停止フラグで安全に終了。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 銘柄選定（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）。
  - portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに基づく乗数（calc_regime_multiplier）。
  - portfolio.position_sizing: position size（calc_position_sizes）計算。リスクベース／等配分／スコア加重などの方式、lot_size での丸め、aggregate cap によるスケーリング・残差処理、コストバッファ考慮を実装。

- 研究用モジュール
  - research.factor_research: Momentum / Volatility / Value ファクター計算（calc_momentum, calc_volatility, calc_value）。DuckDB の prices_daily / raw_financials を利用して純粋関数的に計算。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリ（factor_summary）、ランク関数（rank）を追加。
  - research パッケージから必要関数をエクスポート。

- ニュースNLP（AI）モジュール
  - ai.news_nlp: raw_news から銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini) を用いてセンチメントスコアを生成して ai_scores テーブルへ書き込む処理を実装。処理ウィンドウ計算（calc_news_window）、バッチ送信、最大記事/文字数制限、リトライ（指数バックオフ）、レスポンス検証、スコアクリップ等をサポート。

- 解析/検証ツール
  - tools.paper_verification_report: Paper Trading 実行結果（data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計して報告する CLI スクリプトを追加。閾値（稼働率99% 等）に基づく PASS/FAIL 判定を出力。日付フィルタ・DB パス指定をサポートし、テーブル不在時の耐障害性（OperationalError を捕捉）を実装。

- ユーティリティ
  - utils.process_priority: クロスプラットフォームでプロセス優先度（set_process_priority）と CPU affinity（set_cpu_affinity）を設定するユーティリティを追加（psutil 利用）。Windows と POSIX 系（Linux/Darwin/FreeBSD）を吸収し、権限不足等は警告でスキップ。

変更 (Changed)
- 設定の読み込み順序と保護
  - OS 環境変数を保護しつつ、.env（未設定のキーのみ）→ .env.local（上書き可）の順でロードする設計に。
- run_monitoring / run_execution の起動挙動
  - 起動直後にプロセス優先度を High に設定するように統一。監視ループ/エンジン起動前に監視 DB 初期化を行い、監視テーブルの存在を保証（冪等 init）。

修正 (Fixed)
- 入力検証とフォールバック
  - MONITOR_POLL_INTERVAL の値検証を実装し、0以下や非整数の場合はデフォルト（60秒）へフォールバックして警告を出力。
  - Settings.paper_fill_mode の妥当性検査を追加（instant, partial, never, reject のみ許容）。
  - calc_forward_returns で horizons のバリデーションを行い、不正な値を弾く。
- レジリエンス強化
  - tools.paper_verification_report の集計処理でテーブルが存在しない場合に OperationalError を捕捉して無害に扱うようにし、レポート生成を継続。
  - ai.news_nlp: APIキー未設定時に明示的な ValueError を投げることで早めに失敗するようにし、API呼び出しのリトライ（429/5xx/ネットワーク断等）戦略を実装。
- ポジションサイズ計算の厳密化
  - calc_position_sizes にて lot_size 単位の丸め、per-stock 最大上限、および aggregate cap 超過時の補正（スケールと残余配分）を実装。cost_buffer を導入して保守的にコスト推定。

注意 / 既知の制約 (Known issues / Notes)
- ai.news_nlp の処理は外部 API（OpenAI）に依存するため、API のレート制限や料金、利用ポリシーに注意が必要。
- position_sizing の price フォールバックは未実装（price が欠損した場合、現状はスキップ。将来的に前日終値等のフォールバックを検討）。
- calc_regime_multiplier は未知のレジームで 1.0 にフォールバックし警告を出力する設計。
- DuckDB の executemany に関する制約（空パラメータの扱い）に注意。ai/news_nlp 内で書き込み前に対象コード集合が空でないことをチェックしている。

セキュリティ (Security)
- 環境変数（API キー等）は Settings 経由で取得します。自動 .env ロードは有効/無効が切り替え可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

以上。