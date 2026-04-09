# CHANGELOG

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
フォーマット: 主要な変更カテゴリ（Added / Changed / Fixed / Security / その他注記）を用いて整理しています。

注: この CHANGELOG は与えられたソースコードから実装内容を推測して作成したものです。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-09
初期リリース。主にポートフォリオ構築、リサーチ、AI ベースのニューススコアリング・レジーム判定、設定管理、監視永続化周りのコア機能を実装。

### Added
- 全体
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - モジュールのエクスポート定義を整備（portfolio / research / ai / monitoring 等）。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート判定は .git または pyproject.toml を基準に行うため、CWD に依存しない。
    - 読み込みの優先順位: OS 環境変数 > .env.local > .env。
    - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export 文やクォート，インラインコメント，エスケープに対応。
    - OS 環境変数を保護するため「protected keys」扱いで上書きを制御。
  - Settings クラスを実装し、各種設定値（API トークン・API URL・DB パス・Paper Trading 設定・監視閾値・環境/ログレベル判定など）をプロパティで提供。
    - 必須キー未設定時に明確なエラーを出す _require() を導入（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等の値チェック（不正値は ValueError）。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder
    - select_candidates(): BUY シグナルをスコア降順（同点は signal_rank 昇順）で上位 N 件を選択。
    - calc_equal_weights(): 等金額配分の重みを計算。
    - calc_score_weights(): スコア加重配分を計算。全スコアが 0 の場合は等金額配分にフォールバックして WARNING を出力。
  - risk_adjustment
    - apply_sector_cap(): セクター別エクスポージャーに基づき新規候補を除外（セクター集中の上限を適用）。当日売却予定銘柄を除外して計算。unknown セクターは制限対象外。
    - calc_regime_multiplier(): 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す（フォールバック・未知レジームは警告＋1.0）。
  - position_sizing
    - calc_position_sizes(): allocation_method（"risk_based" / "equal" / "score"）に応じて銘柄ごとの発注株数を算出。
      - risk_based: 許容リスク率 (risk_pct) と損切り幅 (stop_loss_pct) に基づく株数算出。
      - equal/score: 重み（weights）に基づく配分を算出。
      - 単元株（lot_size）で丸め、1銘柄上限（max_position_pct）、総投下上限（max_utilization / available_cash）を適用。
      - 手数料・スリッページ見積り用 cost_buffer を考慮した aggregate cap（スケールダウン）ロジック＆端数配分（lot サイズ単位で残差を再配分）。
      - 価格欠損（<=0）の銘柄はスキップし、ログ出力。

- リサーチ（kabusys.research）
  - factor_research
    - calc_momentum(): 1M/3M/6M リターンおよび 200 日移動平均乖離を計算（DuckDB の prices_daily を使用）。データ不足時は None を返す設計。
    - calc_volatility(): 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比（volume_ratio）を計算。true_range の NULL 伝播を考慮。
    - calc_value(): raw_financials と prices_daily を組み合わせて PER（EPS が 0/欠損なら None）と ROE を算出。最新財務レコードの取得は report_date <= target_date の最新を採用。
  - feature_exploration
    - calc_forward_returns(): 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を用いた単一クエリ実装）。horizons 検証（正の整数かつ <=252）。
    - calc_ic(): ファクターと将来リターンのランク相関（Spearman ρ）を計算。十分な有効レコード（>=3）がない場合は None。
    - rank(): 同順位は平均ランクとするランク化ユーティリティ（float を round(...,12) して ties を安定検出）。
    - factor_summary(): count/mean/std/min/max/median を計算する統計サマリー（None を除外）。

  - research パッケージは zscore_normalize（kabusys.data.stats のラッパ）を再エクスポート。

- AI（kabusys.ai）
  - news_nlp
    - calc_news_window(): target_date に対するニュース収集ウィンドウ（JST->UTC 変換）を返す。
    - score_news(): raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込むフローを実装。
      - バッチ処理（最大 20 銘柄 / API 呼び出し）、1 銘柄あたり最大記事数/文字数でトリム。
      - OpenAI 呼び出しは JSON Mode を使用し、429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。
      - レスポンス検証: JSON パース、"results" リスト、各要素が {"code","score"} を持つこと、コードの照合、スコアが有限数値であることをチェック。
      - スコアは ±1.0 にクリップ。部分失敗時に既存の他コードスコアを保護するため DELETE→INSERT をコード絞り込みで実行（DuckDB の executemany の制約に対応）。
      - API キーは引数優先、なければ環境変数 OPENAI_API_KEY を参照。未設定時は ValueError。
      - テスト容易性のため OpenAI 呼び出し関数は差し替え可能（内部関数を patch 可能にしている）。
  - regime_detector
    - score_regime(): ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等的に書き込み。
      - 1321 の ma200_ratio は target_date 未満のデータのみを使用（ルックアヘッド回避）。データ不足時は中立（1.0）として警告ログ。
      - マクロニュースは内部キーワードでフィルタしてタイトルを取得し、存在する場合にのみ LLM 評価を行う。API 失敗時は macro_sentiment=0.0 でフェイルセーフ継続。
      - 合成スコアはクリップされ、閾値によりラベル付け。DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等パターン。
      - OpenAI 呼び出しは news_nlp のものとは別実装（モジュール間のプライベート関数共有を避ける）。

- 監視永続化（kabusys.monitoring.monitoring_db）
  - init_monitoring_db(): SQLite を使った監視用 DB スキーマ作成（冪等）。system_status / trade_logs / positions / risk_logs 等のテーブルとインデックスを作成。

### Changed
- （初回リリースのため変更履歴はなし）

### Fixed
- （初回リリースのため修正履歴はなし）

### Security
- API キーの扱いを明確化：
  - OpenAI API キーは関数引数優先、未指定時は OPENAI_API_KEY 環境変数を参照。未設定時は ValueError を発生させる（明示的なエラーで早期検出）。
  - .env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テストやセキュリティ用途に便利）。
- LLM からの出力は厳密にバリデーションし、未知・不正なデータは無害化（スコア範囲クリップ、無効レスポンスはログ記録してスキップ）。

### Notes / 実装上の補足
- DuckDB / SQLite を想定した設計で、リサーチ系関数は外部 API を叩かない方針（オフラインで安全に解析可能）。
- LLM 呼び出しはテスト容易性を意識して抽象化されており、ユニットテスト時は _call_openai_api の差し替えが可能。
- 各モジュールはログ出力（logging）により異常・フォールバック動作を知らせる設計。
- position_sizing の将来的拡張点として、銘柄別 lot_size（単元株）対応の TODO コメントあり。
- calc_regime_multiplier や calc_score_weights 等は不正値や特殊ケースでフォールバックを行い、プロダクション稼働時の安全性を高めている。

以上。リリースや利用に関する不明点があれば、特定のモジュールや関数についてさらに詳しい要約や使用例を作成します。