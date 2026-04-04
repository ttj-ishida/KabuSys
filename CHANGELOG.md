# Changelog

すべての変更は Keep a Changelog の原則に従って記載しています。  
日付はリリース日を示します。

フォーマット: [Unreleased]、[x.y.z] - YYYY-MM-DD

## [Unreleased]

## [0.1.0] - 2026-04-04
初回リリース。日本株自動売買・調査プラットフォームのコア機能群を実装。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"、公開モジュール一覧）。
- 環境変数／設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装。
    - プロジェクトルートを .git または pyproject.toml から検出して探索（CWD非依存）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env パーサは export プレフィックス、クォート、有効なコメント処理、エスケープ対応を実装。
    - 読み込み時に既存 OS 環境変数を保護する仕組み（protected set）。
  - Settings クラスを追加し、主要設定をプロパティ経由で取得可能に。
    - J-Quants / kabuステーション / LINE / DB パス / 監視しきい値 / 環境 / ログレベル 等のプロパティを提供。
    - 必須設定未設定時は ValueError を送出する _require() を実装。
    - KABUSYS_ENV, LOG_LEVEL の値検証（許容値チェック）。
    - パス系設定は Path 型で返却し expanduser を適用。

- ニュース NLP（AI） (kabusys.ai.news_nlp)
  - raw_news と news_symbols を用いて銘柄ごとにニュースを集約・LLM（gpt-4o-mini）でセンチメント評価。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で実装。
  - 1 銘柄あたり記事数・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）を実装しトークン肥大化に対応。
  - 最大 20 銘柄単位でバッチ送信（_BATCH_SIZE）。
  - OpenAI 呼び出しでの再試行（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）を実装。
  - レスポンス検証ロジックで JSON の抽出、"results" リスト、コードの正規化、スコアの数値性／有限性チェックを実装。
  - スコアを ±1.0 にクリップし、ai_scores テーブルへ冪等的に（DELETE→INSERT）保存。
  - APIキー注入（api_key引数または環境変数 OPENAI_API_KEY）、未設定時は ValueError を送出。
  - フェイルセーフ: API失敗時はそのチャンクをスキップして他銘柄処理を継続。

- 市場レジーム判定（AI + 指標） (kabusys.ai.regime_detector)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
  - MA200 比率計算（ルックアヘッド防止のため target_date 未満のみ参照）を _calc_ma200_ratio で実装。データ不足時は中立 1.0 を返す。
  - マクロニュース抽出（_MACRO_KEYWORDS）と最大 N 記事取得ロジックを実装。
  - OpenAI 呼び出し（gpt-4o-mini）・再試行・エラー分類・JSON パース保護を実装。API エラー時は macro_sentiment=0.0 のフォールバック。
  - レジームスコア合成、クリップ、閾値判定（_BULL_THRESHOLD / _BEAR_THRESHOLD）を実装。
  - market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK 実行）。

- データ基盤 (kabusys.data)
  - ETL パイプライン基盤 (pipeline.ETLResult)
    - ETL 実行結果を保持する dataclass ETLResult を実装。品質問題・エラー集約機能と to_dict() を提供。
    - 差分更新 / バックフィル / 品質チェックに関する設計考慮を文書化。
  - calendar_management モジュール
    - market_calendar を使った営業日判定とユーティリティを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB データ優先・未登録日は曜日ベースのフォールバック、最大探索日数制限 (_MAX_SEARCH_DAYS) を実装。
    - calendar_update_job により J-Quants から差分取得・バックフィル・健全性チェックを行い、jquants_client 経由で保存する処理を実装。
  - ETL 周りの内部ユーティリティ（テーブル存在チェック・最大日付取得など）を実装。

- リサーチ機能 (kabusys.research)
  - ファクター計算 (factor_research)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から直近財務データを取得し PER / ROE を計算（EPS が 0 または欠損時は None）。
    - DuckDB 上で SQL による効率的な窓関数実装を採用。
  - 特徴量解析 (feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD によって一括計算。horizons のバリデーションあり。
    - calc_ic: factor と将来リターンのスピアマンランク相関（IC）を実装。サンプル数不足時は None を返す。
    - rank: 同順位を平均ランクで処理するランク化ユーティリティ（丸め誤差対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリーを実装。
  - 研究向けユーティリティ群の公開（__all__ を整備）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数注入または環境変数（OPENAI_API_KEY）で解決し、未設定時は明示的にエラー化して誤用を防止。

### Notes / 設計上の重要ポイント
- ルックアヘッドバイアス防止:
  - 各モジュール（ai/news_nlp, ai/regime_detector, research/*）は datetime.today()/date.today() を直接参照せず、明示的な target_date を受け取って処理する設計。
- DB 書き込みは冪等性に配慮（DELETE→INSERT、ON CONFLICT 指向の保存）し、部分失敗時に既存データを不必要に消さないようにしている。
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスの堅牢なバリデーションとリトライ戦略を実装。
- DuckDB をメインのローカル分析 DB として使用。executemany の空リスト対策（DuckDB 0.10 の制約）をコード上で考慮。

---

今後の予定（例）
- execution / monitoring モジュールの追加実装（発注ロジック、プロセス監視等）
- テストカバレッジの拡充、CI における OpenAI モックの整備
- ドキュメント（StrategyModel.md, DataPlatform.md 等）の公開

もし CHANGELOG に追記したい変更点（公開日や追加の修正）があればお知らせください。