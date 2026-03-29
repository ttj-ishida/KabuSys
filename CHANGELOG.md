# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに従います。  

現在のバージョン: 0.1.0

---

## [0.1.0] - 2026-03-29

### 追加 (Added)
- 基本パッケージ
  - kabusys パッケージの初期公開（src/kabusys/__init__.py）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ でエクスポート。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルと環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索し、自動読み込みは CWD に依存しない実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能（テスト用）。
  - .env パーサの強化:
    - コメント行・空行無視、`export KEY=val` 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理（クォート有無に応じた扱い）などをサポート。
    - ファイル読み込み失敗時は警告を出して継続。
    - 既存 OS 環境変数を保護する protected オプションを採用し、上書き制御を実現。
  - Settings クラスによるプロパティベースの設定取得を提供（J-Quants / kabuステーション / Slack / DB パス / 環境種別・ログレベル等）。
    - 必須変数未設定時に ValueError を送出する _require 実装。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値以外はエラー）。
    - DB パスプロパティが Path 型で返る（expanduser 対応）。

- AI モジュール
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信してセンチメントスコアを算出。
    - 特徴:
      - JST 基準のニュース収集ウィンドウ計算（calc_news_window）。
      - 1 銘柄あたりの記事数・文字数に上限を設けてトークン肥大化対策（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
      - 最大 _BATCH_SIZE（20） 銘柄ずつのチャンク処理。
      - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。
      - レスポンス検証（JSON 抽出、results リスト、code/score の検証、未知コード無視、数値チェック）。
      - スコアは ±1.0 にクリップ。
      - 書込みは部分成功に耐える設計（該当コードのみ DELETE → INSERT、DuckDB executemany の空リスト制約を配慮）。
      - テスト容易性のため OpenAI 呼び出し関数は差し替え可能（unittest.mock.patch 用に _call_openai_api を内部実装）。
  - レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - 特徴:
      - MA200 比率計算は target_date 未満データのみを使用しルックアヘッドバイアスを防止。
      - マクロニュースはキーワードフィルタで抽出（_MACRO_KEYWORDS）し、最大件数で LLM 評価を実行。
      - OpenAI 呼び出しはリトライとエラーハンドリングを備え、失敗時は macro_sentiment=0.0 としてフェイルセーフ継続。
      - 推定結果を market_regime テーブルに冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
      - テスト容易化のため _call_openai_api は差し替え可能。

- Research モジュール (src/kabusys/research/)
  - factor_research.py
    - モメンタム、ボラティリティ、バリュー（PER・ROE）の定量ファクター計算を実装。
    - calc_momentum: 1M/3M/6M リターン、ma200_dev（200 日 MA 乖離率）。データ不足時の None 処理。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。NULL 伝播を制御して正確な ATR を算出。
    - calc_value: raw_financials から最新財務（report_date <= target_date）を取り出して PER/ROE を算出。
    - 全関数は DuckDB と prices_daily / raw_financials のみ参照（実際の発注等に影響しない）。
  - feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）に対する将来リターンを一度のクエリで取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（有効レコードが 3 未満は None）。
    - rank / factor_summary: ランク付け（同順位は平均ランク）、及び各カラムの count/mean/std/min/max/median 計算（外部ライブラリ非依存、標準ライブラリのみ）。

- Data モジュール (src/kabusys/data/)
  - calendar_management.py
    - JPX カレンダー管理と営業日判定ロジックを実装。
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - DB に market_calendar があればそれを優先、未登録日は曜日ベースのフォールバック（土日休）を採用して一貫性を確保。
    - next/prev_trading_day は最大探索日数を設定して無限ループを防止。
    - calendar_update_job により J-Quants から差分取得 → market_calendar へ冪等保存（バックフィルと健全性チェックを実装）。
  - pipeline.py / etl.py
    - ETL のための ETLResult データクラスを導入（pipeline.ETLResult を data.etl で再エクスポート）。
    - ETLResult は取得件数/保存件数/品質問題/エラー要約を保持し、has_errors / has_quality_errors / to_dict を提供。
    - 差分更新、バックフィル、品質チェック（quality モジュールと連携）の設計方針を実装（実装の詳細は pipeline 内に記載）。
    - DuckDB テーブル存在確認や最大日付取得ユーティリティを提供。

- テスト性・安全性
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を直接参照しない設計（target_date パラメータ基準）。
  - OpenAI API 呼び出しはモジュール内でラップされ、テスト時に簡単に差し替え可能。
  - 外部 API エラー時は例外抑止やフォールバック（ゼロスコアやスキップ）により全体処理の停止を防止するフェイルセーフ設計。
  - DuckDB の仕様（executemany の空リスト不可等）への互換性配慮がなされている。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### 非推奨 (Deprecated)
- 初期リリースのため該当なし。

### 削除 (Removed)
- 初期リリースのため該当なし。

### セキュリティ (Security)
- OpenAI API キーは引数 injection を許容しつつ、環境変数 OPENAI_API_KEY を既定で参照する設計。必須未設定時は明示的な ValueError を発生させる。

---

注:
- 上記はコードベースの実装内容と docstring から推測してまとめた CHANGELOG です。実際のリリースノート作成時は用途に応じて対象の変更点・既知の制約・互換性情報を追記してください。