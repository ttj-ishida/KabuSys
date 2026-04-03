# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

- ドキュメント追記・細かなログ改善（今後のリリースで分割予定）
- テスト用フックの追加検討（OpenAI呼び出しの差し替えなど）

## [0.1.0] - 2026-04-03

初回公開リリース。以下の主要機能および実装を含みます。

### 追加 (Added)

- 基本パッケージ初期構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定管理 (kabusys.config)
  - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動読み込み機能。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード停止可能。
  - .env 行パーサーの実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント対応）。
  - 必須値取得ヘルパー _require() と Settings クラス（J-Quants / kabu / LINE / DB / 監視 / システム設定をプロパティで取得）。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
  - 各種パス（DuckDB / SQLite / PID / kill flag）や監視閾値（CPU/メモリ/ディスク）の取得用プロパティを提供。
  - is_live / is_paper / is_dev の簡易判定プロパティ。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を元に銘柄別にニュースを集約して OpenAI（gpt-4o-mini）へ送信し、銘柄ごとの ai_score（ai_scores テーブル）を書き込む機能。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 比較）。
  - バッチ処理（1回最大 20 銘柄）、1銘柄当たりの記事数・文字数上限 (_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK)。
  - JSON Mode のレスポンス検証（冗長テキストからの JSON 抽出、results の存在/型確認、未知コード除外、スコアの数値検証）。
  - リトライロジック（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ、最大リトライ制御）。
  - フェイルセーフ: API 失敗時は当該チャンクはスキップ、例外を上げず継続。
  - DuckDB 互換性配慮（executemany に空リストを渡さない等）。
  - テスト容易性: _call_openai_api をモック差し替え可能。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で market_regime テーブルに書き込む。
  - マクロキーワードに基づく raw_news タイトル抽出、OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を取得、スコア合成・ラベリング（bull/neutral/bear）。
  - ルックアヘッドバイアス対策: target_date 未満のみを参照、datetime.today()/date.today() を直接参照しない設計。
  - API エラー時のフォールバック（macro_sentiment=0.0）とリトライ処理。
  - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック時の保護処理。

- データプラットフォーム関連 (kabusys.data)
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - ETLResult データクラスを提供（フェッチ/保存件数、品質問題、エラー一覧、便利プロパティ）。
    - 差分取得・バックフィル・品質チェックを意図した設計（J-Quants クライアント連携を想定）。
    - DuckDB テーブル存在チェック、最大日付取得等のユーティリティを実装（パーシャル実装を含む）。
  - カレンダー管理モジュール（kabusys.data.calendar_management）
    - market_calendar テーブルを使った営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB データが無い場合の曜日ベースフォールバック（週末除外）。
    - カレンダー夜間更新ジョブ（calendar_update_job）: J-Quants から差分取得・冪等保存・バックフィル・健全性チェック。
    - 最大探索範囲の上限設定（無限ループ防止）。

- 研究用モジュール (kabusys.research)
  - factor_research: モメンタム / ボラティリティ / バリュー系ファクター計算（momentum, volatility, value）
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
    - calc_value: PER、ROE（raw_financials と prices_daily を組み合わせ）。
    - DuckDB を利用した SQL + Python 実装。結果は (date, code) ベースの dict リストで返却。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク関数（rank）。
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターン算出、範囲チェック。
    - calc_ic: スピアマン（ランク）相関の実装。少数データ時は None を返す。
    - factor_summary: count/mean/std/min/max/median を算出（None 除外）。

- テスト・運用性のための設計上の配慮
  - ルックアヘッドバイアスを防ぐ設計（target_date パラメータ中心、date.today() の非使用）。
  - OpenAI API 呼び出しの差し替え可能性（ユニットテスト用）。
  - ロギングを適切な箇所に追加（info/debug/warning/exception）。
  - DB 書込時のトランザクション保護とロールバック対処。

### 変更 (Changed)

- （初版のため該当なし）

### 修正 (Fixed)

- （初版のため該当なし）

### セキュリティ (Security)

- OpenAI API キーや外部サービスの認証情報は環境変数から取得する設計。未設定時は例外で明示的に通知（ValueError）。
- .env の読み込みでは OS 環境変数を保護する protected ロジックを実装（意図せぬ上書きを防止）。

### 既知の制約 / 注意事項 (Known issues / Notes)

- OpenAI 利用部分は外部 API に依存するため、API レートやレスポンス仕様の変化に対しては影響を受ける（リトライ・フォールバックは実装済み）。
- DuckDB バインドの互換性（executemany の空リスト）は回避策を実装しているが、DuckDB のバージョン差に注意。
- 現時点で PBR・配当利回りなどの一部バリューファクターは未実装。
- calendar_update_job は J-Quants クライアント (kabusys.data.jquants_client) を使用する前提。外部接続失敗時は 0 を返しスキップする設計。
- ai_scores / market_regime などのテーブルスキーマは呼び出し側で整備されている必要がある（マイグレーション等は別途実装想定）。

---

（注）本 CHANGELOG は提供されたソースコードから実装された機能・設計意図を推測して作成しています。実際のリリースノート作成時はテスト・ドキュメント・マイグレーションなどの追加情報を反映してください。