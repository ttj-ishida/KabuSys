# Changelog

すべての注目に値する変更点はここに記載します。  
このファイルは Keep a Changelog の形式に準拠します。  

フォーマットや区分については https://keepachangelog.com/ja/ を参照してください。

## [0.1.0] - 2026-04-01

初回リリース。以下の主要機能・実装を含みます。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージの基本設定を追加。バージョン情報を `__version__ = "0.1.0"` として公開。

- 環境変数 / 設定管理 (`src/kabusys/config.py`)
  - .env ファイル（`.env` / `.env.local`）または OS 環境変数から設定を自動読み込みする仕組みを導入。
  - 自動ロードの優先度: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用フラグ）。
  - .env パーサーは次の構文をサポート:
    - 空行・コメント行（#）を無視
    - `export KEY=val` 形式に対応
    - シングル / ダブルクォートされた値のバックスラッシュエスケープ処理
    - クォートなし値での行内コメント処理（`#` の直前が空白/タブの場合）
  - 環境変数の取得アクセサ（Settings クラス）を提供:
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 実行環境（development/paper_trading/live）/ログレベル等
    - 必須キー未設定時に明確なエラーを出す `_require` を実装
    - env / log_level の値検証（有効な値集合を厳格にチェック）
    - パスプロパティは Path 型で返す（expanduser 対応）

- AI (自然言語処理) モジュール
  - ニュース NLP スコアリング (`src/kabusys/ai/news_nlp.py`)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）にバッチ送信してセンチメントを算出。
    - 時間ウィンドウ：前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive datetime で処理する calc_news_window を提供）。
    - チャンク処理：1 API コール最大 20 銘柄（_BATCH_SIZE）。
    - 1 銘柄あたりの最大記事数/文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。
    - レスポンス検証: JSON 抽出、"results" リスト形式、code と score の検証、未知コードは無視、スコアは ±1.0 にクリップ。
    - 書き込み: 成功した銘柄のみ ai_scores テーブルへ（DELETE → INSERT の冪等処理）。DuckDB executemany の空配列制約を考慮。
    - テスト向けフック: OpenAI 呼び出し内部関数を patch して差替え可能。
    - API キー注入可能（引数 or 環境変数 OPENAI_API_KEY）。未設定時は ValueError。

  - 市場レジーム判定 (`src/kabusys/ai/regime_detector.py`)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成してレジーム判定（'bull' / 'neutral' / 'bear'）を日次で算出。
    - マクロ記事フィルタリング用キーワード群を定義（日本/米国・グローバル含む）。
    - LLM 呼び出しは gpt-4o-mini の JSON mode を利用、リトライ/バックオフの実装あり。
    - API 失敗時は安全なフォールバック（macro_sentiment = 0.0）で処理継続。
    - データベース書き込みは冪等（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）、失敗時は ROLLBACK を試行し上位へ例外伝播。
    - lookahead バイアス対策の設計（内部で datetime.today() を参照しない、prices_daily クエリは date < target_date の排他条件を遵守）。

- リサーチ機能 (`src/kabusys/research/`)
  - ファクター計算 (`factor_research.py`)
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（データ不足時は None を返す）
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比率（volume_ratio）
    - calc_value: PER（EPS が 0 または欠損時は None）、ROE（raw_financials から最新レコードを結合して算出）
    - すべて DuckDB の prices_daily / raw_financials を参照し外部副作用なし
  - 特徴量探索 (`feature_exploration.py`)
    - calc_forward_returns: target_date 基準で指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons のバリデーションあり。
    - calc_ic: Spearman のランク相関（IC）計算、十分なレコード数がない場合は None を返す
    - rank: 同順位処理は平均ランクで扱う。浮動小数の丸めで ties 検出を安定化
    - factor_summary: count/mean/std/min/max/median を算出

- データ基盤関連 (`src/kabusys/data/`)
  - マーケットカレンダー管理 (`calendar_management.py`)
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末を非営業日扱い）
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存。バックフィル・健全性チェックを実装。
  - ETL / パイプライン (`pipeline.py`, `etl.py`)
    - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラー一覧などを保持）
    - 差分取得・バックフィル・品質チェック（quality モジュール呼び出し）などの方針を実装するための基礎を追加
    - etl モジュールは pipeline.ETLResult を再エクスポート

### 変更 (Changed)
- 設計方針（全体）
  - ルックアヘッドバイアス防止のため、主要 AI / スコアリング / ETL / リサーチ処理は内部で datetime.today()/date.today() を直接参照しない設計とした（呼び出し元が target_date を明示的に渡す）。
  - DuckDB を主要な分析ストレージとして採用し、SQL + Python で計算を完結させる方針（pandas 等に依存しない実装）。
  - OpenAI 呼び出しはテスト容易性のためモジュール内部で差し替え可能な関数を用意し、news_nlp と regime_detector で別実装とした（モジュール間でプライベート関数を共有しない設計）。

### 修正 (Fixed)
- 安全な DB 書き込みパターンを採用
  - ai_scores / market_regime などの更新で部分失敗時に他コードの既存データを保護するため、対象コードのみ DELETE → INSERT する実装に変更（DuckDB の executemany 空リスト制約を考慮）。
  - 例外発生時に ROLLBACK を試行し、ロールバック失敗の警告ログを出す処理を追加。

- OpenAI API エラー処理の強化
  - 429/ネットワーク断/タイムアウト/5xx に対するリトライ（指数バックオフ）を共通的に適用。
  - 非 5xx の APIError や JSON パース失敗は安全にフォールバック（警告ログ）し処理継続するよう修正。

### 注意点 / 既知の設計上の挙動
- OpenAI 依存部分は API キーを必要とする（引数で注入可能）。テストでは内部の _call_openai_api をモックすることを想定。
- DuckDB のバインド動作や executemany の挙動に対して互換性対策を行っている（空配列は送らないなど）。
- calendar_update_job は J-Quants クライアント（jquants_client）に依存しており、API 側のエラーや空レスポンス時は 0 を返して安全に終了する。
- news_nlp / regime_detector の LLM 応答は JSON mode を想定しているが、稀に前後に余分なテキストが含まれる場合の復元ロジックも実装している。

### セキュリティ (Security)
- 特に新規に報告されたセキュリティ修正はありません。環境変数の取扱いは保護（OS 環境変数優先・protected set）を考慮して実装しています。

---

今後のリリースでは以下を想定しています（未実装・計画事項）:
- strategy / execution / monitoring パッケージの実装（現在は __all__ に名前があるが個別モジュールは未掲示）
- 追加の品質チェックルール、より詳細な監視・アラート実装
- ドキュメント（使用例 / データスキーマ / ETL 操作手順）の拡充

（以上）