# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

現在の日付: 2026-04-12

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-12
初回リリース。以下はコードベースから推測される主な機能・修正・設計上の方針です。

### 追加 (Added)
- 実行・監視ランナー
  - run_execution: ExecutionEngine 起動スクリプトを追加。Broker クライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の run_session 呼び出しを行う。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite DB (data/paper_trading.db) を使用し、本番 DB と分離する挙動をサポート。
    - プロセス優先度を起動時に設定（高優先度）。
    - DuckDB 接続を利用。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を組み込む。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用する点を明記。
    - プロセス優先度を起動時に設定（高優先度）。
    - SQLite / DuckDB の接続初期化と監視 DB テーブルの初期化処理を実行。

- 設定管理
  - config.Settings: 環境変数読み込み・検証を行う Settings クラスを追加。
    - .env 自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env / .env.local の読み込み順序・上書きルールの実装。
    - 複数の設定プロパティ（J-Quants、kabu API、LINE、DB パス、監視閾値、環境種別判定等）を提供。
    - 各種値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
    - settings シングルトンをエクスポート。

- ポートフォリオ構築ライブラリ
  - portfolio.portfolio_builder: シグナル選定(select_candidates)、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights) を追加。
  - portfolio.position_sizing: position sizing ロジックを追加（risk_based / equal / score の配分方式、単元株丸め、aggregate cap スケールダウン、cost_buffer を考慮）。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap、レジームに応じた乗数 calc_regime_multiplier を追加。
  - portfolio パッケージのエクスポートを整備。

- 研究（Research）モジュール
  - research.factor_research:
    - モメンタム (mom_1m/3m/6m/ma200_dev)、ボラティリティ（ATR, 相対 ATR, avg turnover, volume_ratio）、バリュー（PER, ROE）を DuckDB を用いて計算する関数を追加。
    - DuckDB SQL を活用し、ウィンドウ関数や欠損対策を考慮した実装。
  - research.feature_exploration:
    - 将来リターン計算 calc_forward_returns（任意ホライズン、入力検証含む）。
    - IC（Spearman の ρ）計算 calc_ic、rank、factor_summary（count/mean/std/min/max/median）を追加。
  - research パッケージのエクスポートを整備（zscore_normalize を含む）。

- ニュース NLP / AI スコアリング
  - ai.news_nlp:
    - raw_news から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いてセンチメントスコア（-1.0～1.0）を計算して ai_scores テーブルへ書き込む処理を追加。
    - バッチ処理（最大 20 銘柄 / コール）、トークン肥大化対策（記事数/文字数のトリミング）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンスバリデーション、スコアのクリップを実装。
    - ニュース取得ウィンドウの計算ユーティリティ calc_news_window を追加。
    - API キー未設定時は ValueError を投げる明示的なチェックあり。

- ユーティリティ
  - utils.process_priority:
    - プロセス優先度（set_process_priority）と CPU affinity（set_cpu_affinity）設定ユーティリティを追加。
    - Windows / POSIX 系（Linux, Darwin, FreeBSD）差分吸収（psutil を利用）、失敗時は警告でスキップするフェイルセーフを実装。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 検証レポート生成スクリプトを追加（期間指定可能）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計し閾値と比較して PASS/FAIL 判定を出力。
    - DB 存在チェック、SQL 実行時の OperationalError を考慮した堅牢な取得処理を実装。

### 変更 (Changed)
- パッケージ化 / エクスポート:
  - 各機能（portfolio, research, utils, tools）で __init__ を整理し公開 API を明確化。
- 設計方針の明確化:
  - portfolio / research モジュールは副作用なしの純粋関数群を目指し、データベース参照や外部 API 呼び出しを限定している旨を注記。
  - 実行・監視プロセスで起動時にプロセス優先度を早期に設定する運用方針を採用。

### 修正 (Fixed)
- 環境読み込みの堅牢化:
  - .env パース処理でクォート内のエスケープやインラインコメントを正しく処理するロジックを実装。export 形式にも対応。
  - 環境変数上書きルール（protected）を導入し OS 環境を不意に上書きしないように変更。

- データ不足時の扱い:
  - ファクター／指標計算でデータ不足時は None を返す等の統一的な振る舞いを実装し、上位呼び出しでの判定・ログ出力を容易にした。

### ドキュメント・注記 (Notes)
- 多くのモジュールにおいて内部に設計ノート（PortfolioConstruction.md, StrategyModel.md などへの参照）や TODO コメントがあり、将来的な拡張ポイント（銘柄別 lot_size 対応、価格フォールバック等）が示されている。
- OpenAI を利用する ai.news_nlp は API キー管理・レート制御・エラーハンドリングに重点を置いた実装になっているが、実運用では API コストやレート制限に留意する必要がある。

### セキュリティ (Security)
- 現時点で明示的なセキュリティ修正は記載なし。環境変数や API キーの管理（.env ファイル取り扱い）には注意が必要。

---

注: 上記は提示されたソースコードの内容から推測してまとめた変更履歴です。実際のコミット履歴やリリースノートと差異がある可能性があります。必要であれば、各ファイルや機能ごとにより細かい変更点（関数シグネチャ、引数のデフォルト等）を抽出して反映します。