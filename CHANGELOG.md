# CHANGELOG

すべての日付は YYYY-MM-DD 形式。  
この CHANGELOG は Keep a Changelog の形式に準拠しています。コードベースの内容から推測して作成しています。

## [Unreleased]

- なし（次回リリースでの変更を記載してください）。

## [0.1.0] - 2026-04-11

### 追加 (Added)
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。環境に応じて paper_trading 用の専用 SQLite DB を使い、BrokerClientFactory 経由でブローカークライアントを生成して取引セッションを実行する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定可能（デフォルト 60 秒）。監視処理は環境にかかわらず本番 sqlite_path を使用する。
- 設定管理
  - kabusys.config.Settings: 環境変数 / .env ファイルを読み込み・検証する設定クラスを追加。自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に探索し、OS 環境変数の保護や .env.local の上書きサポートを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - .env パーサー: export 構文、クォートのエスケープ、インラインコメントの扱い等に対応した堅牢なパーサを実装。
  - 多数の設定プロパティを提供（J-Quants / kabuAPI / LINE / DB パス / paper trading 設定 / 監視閾値 / ログレベル / 環境判定など）。
  - PAPER_FILL_MODE の入力検証（有効値: instant|partial|never|reject）を実装。
- データベース初期化
  - monitoring 用テーブルが存在することを保証する init_monitoring_db の呼び出しを起動フローに組み込み（冪等）。
- ポートフォリオ構築（純粋関数）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順）で選抜。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分を実装。全スコアが 0 の場合は等分配へフォールバック。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限をチェックして新規候補をフィルタ。sell_codes（当日売却予定）を考慮。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）を実装。未知レジームは警告とともに 1.0 にフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に対応した発注株数計算を実装。単元株丸め、per-position 上限、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積り）対応や残差の lot_size 単位での再配分を実装。
- 実行ユーティリティ
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定する set_process_priority を追加。set_cpu_affinity によりプロセスを最初の N コアに固定する機能も実装。権限不足や未実装機能時は警告でスキップ。
- リサーチ機能（DuckDB ベース）
  - research.factor_research:
    - calc_momentum / calc_volatility / calc_value: DuckDB を使ってモメンタム・ボラティリティ・バリュー系ファクターを SQL ベースで計算。200 日移動平均、ATR、出来高等の集計を実装。
  - research.feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターンを一度のクエリで取得（リード関数利用）。
    - calc_ic / rank / factor_summary: Spearman ランク相関（IC）計算、値のランク化（同順位は平均ランク）、ファクター統計サマリを実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research.__init__ で zscore_normalize（kabusys.data.stats から）などをエクスポート。
- AI 関連
  - ai.news_nlp:
    - ニュース記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）でセンチメント（-1.0〜1.0）を算出し、ai_scores テーブルへ書き込む score_news を実装。
    - バッチ処理（最大 20 銘柄）、1 銘柄あたりの最大記事数 / 文字数制限、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスの厳密なバリデーション、取得スコアのクリッピングを実装。
    - calc_news_window を実装し、タイムウィンドウ（JST 基準）を厳格に扱うことでルックアヘッドバイアスを防止。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は例外を送出。
  - ai.regime_detector:
    - ETF 1321 の MA200 乖離（70% 重み）とマクロニュースの LLM センチメント（30% 重み）を合成して日次の market_regime（'bull'/'neutral'/'bear'）を判定するモジュールを追加。欠損時のデフォルト／フォールバックや idempotent な DB 書き込みを実装。
    - マクロキーワードに基づくニュース抽出、OpenAI 呼び出しのリトライ処理、スコア合成（クリップ）を実装。

### 変更 (Changed)
- 全体の設計方針として「ルックアヘッドバイアス防止」へ配慮。研究・AI モジュールは date/target_date 引数を必須とし、datetime.today()/date.today() を直接参照しない実装を採用。
- DuckDB 互換性対策を各所で実施（ROW_NUMBER の使用、executemany に空リストを渡さないガード等）。
- .env の読み込み順序を OS 環境 > .env.local > .env に明確化し、OS 環境変数を保護する仕組みを導入。
- ログ出力を適切に追加・強化（DEBUG/INFO/WARNING レベルを活用）して状況把握を容易に。

### 修正 (Fixed)
- 環境変数 MONITOR_POLL_INTERVAL の不正値（0 以下や非数）に対してデフォルトにフォールバックするバリデーションを追加し、time.sleep に渡す不正値による例外を回避。
- calc_score_weights: 全スコアが 0 の場合に等金額配分へフォールバックする挙動を追加（警告ログ付き）。
- apply_sector_cap: unknown セクターの扱いを明示（セクター上限の適用対象外）とした。
- 各種外部呼び出し（OpenAI や psutil 操作など）での失敗に対して例外を投げず警告ログで処理を継続するフェイルセーフ設計を採用。

### 破壊的変更 (Breaking Changes)
- なし（このリリースは初期実装をまとめたもののため後方互換性の破壊となる変更履歴はなし）。

### 非推奨 (Deprecated)
- なし。

### 削除 (Removed)
- なし。

### セキュリティ (Security)
- OpenAI API キー取り扱い: score_news / regime_detector は API キーの未設定時に例外を投げる。API キーは環境変数 OPENAI_API_KEY または関数引数で安全に提供すること。

### 既知の問題 (Known issues)
- apply_sector_cap 内の価格欠損時（price == 0.0）にエクスポージャーが過少見積もられる可能性があり、将来的に前日終値や取得原価などのフォールバック価格を導入する余地あり（TODO コメントあり）。
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別 lot_map へ拡張する予定）。
- regime_detector ファイル末尾が切れている/未掲載部分がある（ここに含めた機能はコードから推測した実装内容に基づく）。

---

貢献者: プロジェクトソースコードに基づき自動生成（実際のコントリビュータ情報は該当プロジェクトの履歴を参照してください）。