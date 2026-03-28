CHANGELOG
=========

すべての注目すべき変更点を記録します。これは Keep a Changelog の形式に準拠しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Deprecated: 非推奨
- Removed: 削除
- Fixed: 修正
- Security: セキュリティ関連

0.1.0 - 2026-03-28
------------------

Added
- パッケージ初期リリース:
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"、公開 API（__all__）を定義。
- 環境変数 / 設定管理 (kabusys.config):
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード実装。
  - プロジェクトルート検出ロジック: 現在ファイル位置から .git または pyproject.toml を探索してプロジェクトルートを特定。
  - .env 読み込み器: export KEY=val 形式、クォートやエスケープ処理、行末コメントの扱いをサポートするパーサを追加。
  - .env / .env.local の読み込み優先度（OS 環境変数 > .env.local > .env）と、OS 環境変数を保護する protected 機構を実装。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを停止可能。
  - Settings クラスを追加し、J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等のプロパティを提供。未設定時の必須チェック（_require）を実装。
- AI モジュール (kabusys.ai):
  - ニュース NLP スコアリング (kabusys.ai.news_nlp):
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）の JSON mode で一括評価して ai_scores テーブルへ保存する処理を実装。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、1銘柄あたり記事数制限・文字数トリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 再試行・指数バックオフ（429/ネットワーク断/タイムアウト/5xx に対するリトライ）、レスポンスのバリデーションとスコアの ±1.0 クリップ。
    - レスポンス復元ロジック（JSON パース失敗時に文字列から最外の {} を抽出するフォールバック）。
    - DB 書き込みは部分失敗に備え、スコア取得済みコードのみを DELETE → INSERT で置換（冪等性・既存スコアの保護）。
    - テストフック: _call_openai_api を patch できる設計。
  - 市場レジーム判定 (kabusys.ai.regime_detector):
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する機能を実装。
    - マクロキーワードによる raw_news フィルタ、OpenAI 呼び出し（gpt-4o-mini）による JSON レスポンス取得、リトライ/フェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - レジームスコア合成ロジック（clip, 閾値によるラベリング）と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - テストフック: news_nlp._call_openai_api と分離された独自の _call_openai_api 実装。
- データモジュール (kabusys.data):
  - カレンダー管理 (kabusys.data.calendar_management):
    - JPX カレンダー用ユーティリティ: is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day を実装。
    - market_calendar テーブルが存在しない場合は曜日ベース（土日）でフォールバックする一貫したロジック。
    - 最大探索日数やバックフィル・健全性チェックの定数を導入して無限ループや過剰な未来日付を防止。
    - calendar_update_job: J-Quants API からカレンダーを差分取得し保存する夜間バッチ。バックフィル・健全性チェック・エラー処理を含む。
  - ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl):
    - ETLResult データクラスを定義し、ETL 実行結果の構造化（取得数・保存数・品質チェック結果・エラー等）を提供。to_dict() による品質問題のシリアライズ対応。
    - 差分取得用ユーティリティ（テーブル最大日付取得等）、市場カレンダー連携、バックフィル・品質チェック方針の実装を反映。
    - kabusys.data.etl で ETLResult を再エクスポート。
  - jquants_client 連携のための呼び出しポイントを想定した設計（fetch/save 呼び出しと例外ハンドリング）。
- 研究モジュール (kabusys.research):
  - factor_research:
    - モメンタム (calc_momentum): 1M/3M/6M リターン、200日 MA 乖離を計算。データ不足時の None ハンドリング。
    - ボラティリティ/流動性 (calc_volatility): 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を考慮。
    - バリュー (calc_value): raw_financials から最新財務を取得して PER/ROE を計算（EPS が欠損/0 の場合は None）。
  - feature_exploration:
    - 将来リターン計算 (calc_forward_returns): 任意ホライズン（デフォルト [1,5,21]）のリードを用いた将来リターン計算。ホライズンのバリデーションと一括 SQL 取得。
    - IC（calc_ic）: factor_records と forward_records を code で突合し、スピアマンランク相関（ランクの平均処理・ties 対応）を実装。
    - rank: 同順位は平均ランクで処理（丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - research パッケージの公開 API を整理（__all__）。
- DuckDB を主要ストレージとして想定した SQL 実装を多用。DuckDB のバージョン差異に配慮した実装（executemany の空リスト制約回避や list バインドの互換性考慮等）。
- OpenAI SDK（OpenAI クライアント）を使用した LLM 連携の共通設計（JSON mode / タイムアウト・temperature 0・response_format 指定）。
- ロギング強化: 各モジュールで INFO/DEBUG/WARNING/exception を用いた詳細ログ出力。

Changed
- 初回リリースのため、既存機能の大幅な変更はなし（初期実装）。

Fixed
- 初回リリースのため、既知のバグ修正項目は無し。

Security
- API キーやトークンは Settings 経由で必須チェックを行い、未設定時は明確な ValueError を発生させて安全性を強化。
- .env の取り扱いで OS 環境変数を上書きしない既定値と protected 機構により誤った上書きを防止。

Notes / Migration
- 本リリースは初回公開版です。利用開始時は以下に注意してください:
  - 必須環境変数:
    - OPENAI_API_KEY（AI モジュールを利用する場合）
    - JQUANTS_REFRESH_TOKEN（J-Quants 連携）
    - KABU_API_PASSWORD（kabu API）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（Slack 通知）
  - 自動 .env ロードはプロジェクトルート検出に依存します（.git または pyproject.toml）。パッケージを配布・インストールした場合、KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化することを検討してください。
  - DuckDB スキーマ（prices_daily / raw_news / news_symbols / ai_scores / market_calendar / market_regime / raw_financials 等）を事前に用意しておく必要があります。
  - OpenAI 呼び出し部分はテスト用にモック差し替え可能（内部の _call_openai_api を patch）。

今後の予定（例）
- Web / CLI の運用ツール、モニタリング・通知の拡充、追加のファクター実装、パフォーマンス最適化、より詳細な品質チェックの強化。

---

（この CHANGELOG はソースコードの構造と関数・定数・ドキュメント文字列から推測して作成しています。）