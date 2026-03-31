# Changelog

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
リリースの意味合いはセマンティックバージョニングに従います。

## [Unreleased]

なし

## [0.1.0] - 2026-03-31

初回公開リリース。以下の主要機能と実装方針を含みます。

### Added
- パッケージ初期化
  - kabusys パッケージのエントリポイントを追加。__version__ を "0.1.0" に設定し、公開サブパッケージとして data, strategy, execution, monitoring を列挙。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機構を実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - OS 環境変数を保護するための protected 上書き制御（.env.local は .env より優先して上書き）。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得（J-Quants, kabu ステーション, Slack, DB パス, 監視閾値, 環境/ログレベル判定など）。
  - 環境変数の必須チェックを行う _require 関数を実装。KABUSYS_ENV / LOG_LEVEL のバリデーションを導入。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を元に銘柄単位でニュースを集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを取得して ai_scores テーブルへ書き込む処理を実装。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive datetime で扱う）。
  - バッチ処理: 1回最大 20 銘柄（_BATCH_SIZE）、銘柄ごとに最新最大 10 記事・最大 3000 文字にトリム。
  - 再試行（リトライ）ロジック: 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフ。その他例外は失敗としてスキップ。
  - レスポンス検証: JSON パース・results リスト・各要素の code/score 検証・未知コード無視・スコアを ±1.0 にクリップ。
  - DB 書き込みは部分的冪等（DELETE for codes → INSERT）を実施し、部分失敗で他銘柄の既存スコアを保護。
  - テスト容易性: OpenAI 呼び出し箇所は _call_openai_api を通すことでモック差し替えを想定。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を日次で判定する機能を実装。
  - マクロニュースにはマクロ系キーワードリストを使用し、最大 20 記事を LLM に投げて macro_sentiment を算出（gpt-4o-mini, JSON mode）。
  - スコア合成は clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1) として閾値で label を決定。
  - API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
  - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の流れで冪等性を確保。失敗時は ROLLBACK を試みる。

- データ関連モジュール（kabusys.data）
  - calendar_management:
    - JPX カレンダーを管理する market_calendar テーブル操作関数を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB の calendar データがない場合は曜日（平日/土日）ベースのフォールバックを採用。
    - next/prev/get_trading_days は DB 登録値優先で未登録日は曜日フォールバックし、一貫性を保つロジックを採用。
    - calendar_update_job を実装し、J-Quants API から差分取得 → 保存（fetch / save を jquants_client に委譲）。バックフィルや健全性チェックを実装（直近再フェッチ・極端な未来日付の検出）。
  - pipeline / etl:
    - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラーリスト等を格納）。
    - ETL パイプライン設計に関するユーティリティ、差分更新・バックフィル・品質チェックの設計方針を実装（jquants_client / quality モジュールとの連携を想定）。
    - data.etl は pipeline.ETLResult を再エクスポート。

- リサーチモジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を算出。ウィンドウ不足時は None を返す。
    - calc_value: raw_financials から最新財務データを取得して PER, ROE を計算（EPS が 0/欠損の場合は None）。
    - 計算は DuckDB 上の SQL を併用して実行。外部 API にアクセスしない安全設計。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで計算。horizons の入力検証あり。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。有効レコードが 3 件未満なら None を返す。
    - rank: 値のランク化（同順位は平均ランク）を実装（round による丸めで ties の検出安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - research パッケージは上述関数群と zscore_normalize（kabusys.data.stats から）を公開。

### Behavior / Design decisions (重要な挙動とセーフガード)
- ルックアヘッドバイアス防止:
  - AI スコアリング・レジーム判定等の各関数は datetime.today()/date.today() を直接参照せず、target_date を引数として明示的に与える設計。
  - DB クエリでは date < target_date / date = target_date 等の排他条件やリード/ラグウィンドウを利用し、将来データ参照を防止。

- OpenAI API 呼び出し:
  - gpt-4o-mini を想定し JSON Mode を利用。response_format に JSON を要求。
  - 失敗時はリトライ（指数バックオフ）を実施し、それでも失敗した場合は安全にフォールバック（macro_sentiment=0.0、または該当チャンクをスキップ）して処理継続。
  - テスト時にモック差し替え可能なレイヤ（_call_openai_api）を用意。

- DuckDB 互換性考慮:
  - executemany に空リストを渡せない制約（DuckDB 0.10）を考慮して、埋め込み前に params の空チェックを行う。
  - SQL 内で ROW_NUMBER / window functions を多用し、最新レコード取得や移動平均等を効率的に算出。

- DB 書き込みの冪等性:
  - market_regime や ai_scores など、同日付/銘柄ごとに DELETE → INSERT の順で置換して冪等性を担保。
  - トランザクション（BEGIN / COMMIT / ROLLBACK）を明示的に使用し、部分失敗時のロールバックやその失敗時ログ出力を実装。

### Notes / Limitations
- OpenAI API キーは api_key 引数か環境変数 OPENAI_API_KEY に依存。未設定時は ValueError を発生させる（明示的なエラー）。
- news_nlp / regime_detector の LLM 出力は JSON パースに依存するため、稀に余分なテキスト混入がある場合は簡易抽出ロジックで復元を試みるが、必ず成功する保証はない（失敗時はフォールバック動作）。
- 一部の財務指標（PBR・配当利回り等）は現バージョンでは未実装。
- jquants_client / quality / data.stats 等は外部モジュールとして依存し、環境に合わせた実装が必要。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの詳細実装とテストカバレッジ拡充
- ai モデルのプロンプト改善・多言語対応・より厳密なレスポンス検証
- ETL のスケジューリング・監視ダッシュボード統合

<!--
バージョン履歴のテンプレート（Keep a Changelog）に従っています。
必要に応じて日付や項目の粒度を調整してください。
-->