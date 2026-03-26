# Changelog

すべての重要な変更点をここに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

現在の安定リリース: 0.1.0 - 2026-03-26

## [Unreleased]
- （現在なし）

## [0.1.0] - 2026-03-26

Added
- 初期リリース。パッケージ名: `kabusys`。
- パッケージ公開インターフェース:
  - src/kabusys/__init__.py にてバージョン `0.1.0` を設定。トップレベルの __all__ に ["data", "strategy", "execution", "monitoring"] を定義（将来的なサブパッケージ公開を意図）。
- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出: `.git` または `pyproject.toml` を起点としてルートを見つける（CWD に依存しない実装）。
  - .env のパース実装: コメント行、`export KEY=val` 形式、シングル/ダブルクォート、エスケープ処理、インラインコメント判定などに対応。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - Settings クラスを提供（プロパティ経由で各種必須値を取得・バリデーション）。
    - J-Quants / kabu API / Slack / DB パス（DuckDB, SQLite）や環境種別（development / paper_trading / live）、ログレベル等を管理。
    - 未設定の必須環境変数は明示的な ValueError を投げる。

- AI 関連（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) にバッチ送信し、銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ保存する `score_news` を実装。
    - タイムウィンドウ定義（JST基準：前日15:00〜当日08:30）を calc_news_window で提供。
    - バッチ処理（1回最大 20 銘柄）、記事数・文字数のトリム、JSON Mode のレスポンス検証、結果のクリップ（±1.0）。
    - API エラー（429 / ネットワーク断 / タイムアウト / 5xx）に対する指数バックオフのリトライ実装。失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - レスポンスバリデーション機能（JSON 抽出、"results" 構造検証、未知コード無視、数値判定）。
    - DuckDB の挙動（executemany に空リストを渡せない）を考慮した DB 書き込み処理（DELETE → INSERT、部分書き換えで既存データ保護）。
    - 単体テスト容易性のため、OpenAI 呼び出し箇所はパッチ可能（_call_openai_api をモックで差し替え可能）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull / neutral / bear）を判定する `score_regime` を実装。
    - prices_daily から MA 乖離を計算（_calc_ma200_ratio）。データ不足時は中立（1.0）を採用して継続。
    - raw_news からマクロキーワードでフィルタしたタイトルを取得し、OpenAI に送信して macro_sentiment を算出（記事が無い場合は LLM 呼び出しを行わず 0.0 を返す）。
    - API リトライやエラー時のフェイルセーフ（macro_sentiment=0.0）を実装。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - テスト容易性のため、OpenAI 呼び出しは patch 可能（内部実装を直接共有しない設計）。
  - ai パッケージ初期公開 API: `score_news`, `score_regime`（news_nlp から score_news をエクスポート）。

- データ系（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー（market_calendar）を使った営業日判定ユーティリティ群を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録がない場合は曜日ベース（平日）でフォールバックする一貫した挙動。
    - 祝日データを J-Quants から差分取得して更新する夜間バッチ job: calendar_update_job（バックフィル、健全性チェックを実装）。
    - 検索上限や日付変換ユーティリティを実装し無限ループを回避。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETL 処理の結果を表すデータクラス ETLResult を実装（取得件数、保存件数、品質問題、エラー一覧などを保持）。
    - 差分取得 → 保存 → 品質チェック の設計方針を反映したユーティリティを実装（jquants_client, quality モジュールを利用する想定）。
    - デフォルトのバックフィル日数や最小データ日などの定数を定義。
  - data パッケージは ETLResult を公開。

- リサーチ（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum, Value, Volatility, Liquidity などの定量ファクター計算関数を実装:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
      - calc_volatility: 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金、出来高比率。
      - calc_value: PER（株価/EPS）、ROE（raw_financialsより）。
    - DuckDB 内で SQL を用いて効率的に計算する設計。データ不足時は None を返す。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定日からの将来リターン（任意ホライズン）を計算。入力ホライズンのバリデーションを実施。
    - calc_ic: スピアマンのランク相関による IC 計算（欠損や同値の扱いに配慮）。
    - rank: 同順位は平均ランクとする実装（丸めで ties 判定の安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
  - research パッケージの __init__ で主要関数をエクスポート（zscore_normalize を data.stats から利用）。

- 一般設計上の注意点（全体）
  - ルックアヘッドバイアス回避: 各種スコア計算やウィンドウ計算で datetime.today()/date.today() を直接参照しない設計（target_date を明示引数として扱う）。
  - DuckDB を主要なデータストアとして使用。DuckDB の特性（executemany の空リスト不可など）を考慮した実装。
  - OpenAI API は JSON Mode（response_format {"type": "json_object"}）を利用。レスポンスパースやエラー耐性を強化。
  - ロギング・ワーニングを多用しフェイルセーフを取る（API 失敗時は処理継続、DB 書き込み失敗時は ROLLBACK を試行）。

Security
- OpenAI API キーなどの機密情報は環境変数経由で参照する設計。必須環境変数未設定時は明示的にエラーを発生させる。
- .env 自動読み込みを無効にするためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。

Compatibility
- Python typing（| を使用）と Pathlib を使用しているため、Python 3.10 以上を想定。
- duckdb と openai パッケージが依存ライブラリとして必要。

Notes / マイグレーション
- 初回リリースのため、将来の変更でテーブル名やカラム名・API の出力形式が変わる可能性があります。DB スキーマ変更時は ETL / research / ai モジュールの対象クエリを確認してください。
- OpenAI SDK の将来の仕様変更（例: 例外クラスや status_code の扱い）に対して保守コードを入れてありますが、メジャーな SDK 更新時は動作確認を推奨します。

---

以上がコードベース（初期リリース）から推測できる主な変更点・追加機能の一覧です。必要であれば各機能ごとの使用例や注意点（環境変数一覧、DB スキーマ想定、テストのモック方法など）を追記します。どの情報を優先して追加しますか？