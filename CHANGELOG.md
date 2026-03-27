# Changelog

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを使用します。  
このプロジェクトは安定化フェーズ前の初期バージョンとしてリリースされています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-27

初回リリース。

### Added
- パッケージ初期化
  - kabusys パッケージとバージョン定義を追加（__version__ = "0.1.0"）。
  - 主要サブパッケージを public export に登録: data, strategy, execution, monitoring。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みするロジックを実装。
  - プロジェクトルート検出機能: __file__ の親ディレクトリを走査し .git または pyproject.toml を基準にルートを特定。
  - .env パーサーを実装（コメント行・export 形式・シングル/ダブルクォート・バックスラッシュエスケープ・インラインコメントの扱いに対応）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - Settings クラスを提供し、アプリケーションで必要な設定値（J-Quants / kabu / Slack / DB パス / 環境・ログレベル判定）をプロパティとして取得可能に。
  - env / log_level の値検証（許容値セットによるバリデーション）。
  - 必須環境変数未設定時には ValueError を送出する `_require` を実装。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）に送信しセンチメントスコアを生成。
    - JST/UTC 換算によるニュース収集ウィンドウ定義（前日15:00JST〜当日08:30JST → UTC の前日06:00〜23:30）。
    - バッチサイズ、記事数、文字数上限などのトークン爆発対策（_BATCH_SIZE/_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - JSON Mode を期待し、レスポンス整形・パース（前後に余計なテキストが混入した場合の復元処理を含む）。
    - リトライ / エクスポネンシャルバックオフ（429/ネットワーク断/タイムアウト/5xx を対象）。API 失敗時は該当チャンクをスキップし続行（フォールセーフ）。
    - レスポンス検証（results 配列、各要素の code と score、既知コードのみ採用、数値チェック、±1.0 にクリップ）。
    - DuckDB への書き込みは部分置換（対象コードのみ DELETE → INSERT）を行い、部分失敗時に既存データを保護。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に設計。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算は target_date 未満のデータのみを使用（ルックアヘッドバイアス回避）。
    - マクロ記事はキーワードフィルタリングで抽出し、最大件数制限を適用。
    - OpenAI 呼び出しは独自実装（news_nlp と内部関数を共有しない設計）。
    - API エラーやパース失敗時は macro_sentiment = 0.0 として続行（フェイルセーフ）。
    - DuckDB への書き込みは冪等的（BEGIN / DELETE / INSERT / COMMIT）で処理。失敗時は ROLLBACK を試行し例外伝播。

- データモジュール（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定・操作ユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがない・未登録日は曜日ベースのフォールバック（週末判定）を行い、一貫した挙動を保証。
    - 夜間バッチ calendar_update_job を実装: J-Quants API から差分取得、バックフィル、健全性チェック（未来日異常検知）、冪等保存。
    - 最大探索範囲・ループ防止のための設定（_MAX_SEARCH_DAYS, _CALENDAR_LOOKAHEAD_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS）。

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - 差分抽出・保存・品質チェックを行う ETL のインターフェースを実装。
    - ETLResult dataclass を導入し、取得件数・保存件数・品質問題・エラー一覧などを集約。has_errors / has_quality_errors と to_dict を提供。
    - 差分取得のための最小データ開始日・バックフィル・カレンダー先読みなどの設定を実装。
    - 品質チェック結果は致命的でも ETL を中断せず収集する設計（呼び出し元が意思決定）。

- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算する calc_momentum を実装。データ不足時は None を返す。
    - ボラティリティ/流動性: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算する calc_volatility を実装。NULL 伝搬を考慮した true_range 計算。
    - バリュー: raw_financials から最新報告値を取得して PER / ROE を計算する calc_value を実装。
    - DuckDB を用いた SQL + Python による計算で外部 API にアクセスしない設計。

  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算 calc_forward_returns（任意ホライズン、horizons の検証、効率的な SQL 取得）。
    - IC（Information Coefficient）計算 calc_ic（Spearman ρ、None 処理、最小レコードチェック）。
    - ランク化ユーティリティ rank（同順位は平均ランク、丸めによる ties 対策）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median）。

- 実装上の設計方針（共通）
  - ルックアヘッドバイアス回避のため datetime.today() / date.today() を直接参照しない関数設計を徹底（一部ジョブは実行時に date.today() を利用するが、分析/スコアリング関数は引数で日付を受ける）。
  - 外部 API 呼び出しに対する堅牢性（リトライ・フォールバック・ログ）を重視。
  - DuckDB の既知の制約（executemany に空リスト不可など）を考慮した実装。
  - テスト容易性のため、外部呼び出し部分（例: _call_openai_api）を差し替えられるよう実装。

### Fixed
- （初回リリースにつき該当なし）

### Changed
- （初回リリースにつき該当なし）

### Removed
- （初回リリースにつき該当なし）

### Security
- 環境変数は OS 環境変数を保護する仕組み（.env 読み込み時の protected set）。自動ロードは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

備考:
- OpenAI API を利用する機能は API キー（引数または環境変数 OPENAI_API_KEY）が必須です。未設定時は ValueError を送出します。
- DuckDB に関わる関数群は既存のテーブルスキーマ（prices_daily / raw_news / news_symbols / ai_scores / market_calendar / raw_financials 等）を前提としています。実運用前にスキーマ準備を行ってください。