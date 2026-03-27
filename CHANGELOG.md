# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
このパッケージはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-27
初回リリース。

### Added
- パッケージ基本情報
  - パッケージ名 kabusys、バージョン `0.1.0` を追加。
  - パッケージ公開インターフェースとして `data`, `strategy`, `execution`, `monitoring` を __all__ に定義。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート検出は __file__ を起点に `.git` または `pyproject.toml` を探索（CWD に依存しない）。
    - 読み込み順序は OS 環境変数 > .env.local > .env（`.env.local` は上書き）。
    - 自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能（テスト用途）。
  - .env パーサ実装（`export KEY=val`、クォート付き値、エスケープ、インラインコメントを考慮）。
  - 環境設定アクセス用 `Settings` クラスを提供（`settings` インスタンスをエクスポート）。
    - J-Quants / kabuステーション / Slack / DB パス等の設定プロパティを実装。
    - `KABUSYS_ENV` と `LOG_LEVEL` の値チェックと便利なプロパティ (`is_live`, `is_paper`, `is_dev`) を追加。
    - 必須設定未定義時は明示的な ValueError を発生。

- AI モジュール
  - ニュースセンチメントスコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメントを評価する `score_news` を実装。
    - JST 時間ウィンドウ前日15:00〜当日08:30（UTC に変換）を正確に算出する `calc_news_window` を実装。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、1 銘柄あたりの記事数・文字数制限を実装してトークン肥大化を抑制。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - API レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code/score の型検査、既知コードのみ採用）、スコアを ±1.0 にクリップ。
    - DB への書き込みは部分失敗を考慮し、対象コードのみ DELETE → INSERT を行う（冪等性、DuckDB executemany の互換性に配慮）。
  - マクロレジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（"bull"/"neutral"/"bear"）を判定する `score_regime` を実装。
    - マクロニュースは `news_nlp.calc_news_window` を利用してウィンドウを取得し、タイトルをフィルタして LLM に渡す。
    - OpenAI 呼び出しは専用の内部実装を用い、API 失敗時は macro_sentiment=0.0 にフォールバック（例外を上げず継続）。
    - 結果は `market_regime` テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- データ（Data platform）
  - ETL/パイプライン (kabusys.data.pipeline / kabusys.data.etl)
    - ETL 実行結果を表す `ETLResult` データクラスを実装（取得件数、保存件数、品質問題、エラーメッセージなどを保持）。
    - ETL の差分取得・バックフィル方針や品質チェックの設計方針をコード化（デフォルトバックフィル 3 日、calendar lookahead 90 日等）。
    - `kabusys.data.etl` で `ETLResult` を再エクスポート。
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX マーケットカレンダーの夜間バッチ更新ジョブ `calendar_update_job` を実装（J-Quants API 経由で差分取得→保存）。
    - 営業日判定ユーティリティを提供：`is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`。
    - カレンダーデータがない場合の曜日ベースフォールバック（平日を営業日と判断）や DB 優先ルール、最大探索範囲（60 日）等を実装。
    - バックフィル、健全性チェック（将来日付の異常検知）を実装。

- Research（研究用分析）
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）を計算する `calc_momentum`, `calc_volatility`, `calc_value` を実装。
    - DuckDB 上の SQL ウィンドウ関数を活用して効率的に計算。データ不足時は None を返す設計。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターンを計算する `calc_forward_returns`（任意ホライズン、入力検証あり）。
    - スピアマン ICC（ランク相関）を計算する `calc_ic`（結合・フィルタリング・ties 処理を考慮）。
    - ランキングユーティリティ `rank`（平均ランク、丸め処理で ties の判定安定化）。
    - ファクター統計サマリー `factor_summary`（count/mean/std/min/max/median を計算）。
  - 研究用ユーティリティのエクスポートを提供（`zscore_normalize` は kabusys.data.stats から再利用）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数注入または環境変数 `OPENAI_API_KEY` を使用。未設定時に明示的な ValueError を出すことで誤用を防止。

### Notes / Implementation details
- 時刻・日付設計
  - すべての日付は date オブジェクトで扱い、タイムゾーン混入を防止。ニュースウィンドウ等は JST の業務要件に基づき UTC naive datetime に変換して比較に使用する。
  - ルックアヘッドバイアス防止のため、内部実装で datetime.today()/date.today() を直接参照する箇所を最小化し、明示的な target_date を受け取る API を優先。
- API フォールトトレランス
  - OpenAI 呼び出しはリトライ・バックオフ・フォールバック（0.0 スコア）を採用。LLM レスポンスのパース失敗等も警告ログを出して継続する。
- DB 書き込み
  - 各書き込み操作は冪等性を意識（DELETE→INSERT、ON CONFLICT、部分書き込みでの既存データ保護）している。
- テスト容易性
  - OpenAI 呼び出し関数はモジュール毎に内部でラップしており、ユニットテスト時に patch しやすい設計。
  - 環境自動読み込みをオフにするフラグや api_key を引数に渡せる設計で外部依存を注入可能。

---

著者注: 本 CHANGELOG は提供されたソースコードから機能/振る舞いを推測して作成しています。実際のリリースノートでは、コミット履歴や差分ベースの詳細（追加ファイル、修正行数、既知の制限や既知のバグ）を追記することを推奨します。