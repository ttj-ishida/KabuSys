# Changelog

すべての重要な変更は Keep a Changelog のガイドラインに従って記録しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-03-26
初回公開リリース。以下の主要機能と実装上の注意点を含みます。

### 追加
- パッケージ基盤
  - kabusys パッケージの基本設定（__version__ = 0.1.0）。
  - パブリック API として data, strategy, execution, monitoring をエクスポート（将来的な拡張ポイント）。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイル（.env, .env.local）および環境変数から設定を自動読み込み。
  - プロジェクトルート検出: .git または pyproject.toml を基準に __file__ から探索するため CWD 非依存で動作。
  - .env パーサ実装:
    - コメント行/空行のスキップ、`export KEY=val` 形式対応。
    - シングル／ダブルクォート文字列のバックスラッシュエスケープ処理を考慮したパース。
    - クォート無しの値では '#' の直前が空白/tab の場合にコメントとみなす。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを抑止可能。
  - Settings クラスを提供（J-Quants / kabu / Slack / DB パス / 環境モード / ログレベル等）。
    - 必須キー未設定時は ValueError を送出する _require を実装。
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値のチェック）。
    - デフォルトの DB パス（DuckDB/SQLite）を提供。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を元に銘柄別ニュースを集約し OpenAI（gpt-4o-mini）でセンチメント評価。
  - バッチ処理（1 API 呼び出しで最大 20 銘柄）とトークン肥大対策（記事数・文字数制限）。
  - リトライ戦略: RateLimit / ネットワーク / タイムアウト / 5xx に対して指数バックオフでリトライ。
  - レスポンスバリデーション: JSON パースの復元処理、results の型チェック、未知コード無視、スコアを ±1.0 にクリップ。
  - 書き込みは部分失敗耐性あり（該当コードのみ DELETE → INSERT）。
  - テスト容易性: _call_openai_api をモック差替え可能。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
  - prices_daily / raw_news / market_regime を参照し、計算結果を冪等的に market_regime テーブルへ保存（BEGIN / DELETE / INSERT / COMMIT）。
  - LLM 呼び出しのリトライ制御、API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
  - ルックアヘッドバイアス防止の設計（date < target_date 等の排他条件）。
  - テスト容易性: _call_openai_api をモック差替え可能。

- データ関連（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得、保存（jquants_client の save_* を想定した冪等保存）、品質チェックの基本フロー。
    - ETLResult データクラスによる詳細な実行結果（取得数 / 保存数 / 品質問題 / エラー）報告。
    - backfill の考慮、calendar の先読み等の実運用設定。
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を使った営業日判定、next/prev_trading_day、get_trading_days、is_sq_day の提供。
    - DB 未取得時の曜日ベースフォールバック（週末を非営業日扱い）。
    - calendar_update_job により J-Quants からの差分取得→保存処理を想定（バックフィル・健全性チェック付き）。
    - 最大探索日数制限で無限ループ防止。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）などを DuckDB の SQL を活用して実装。
    - データ不足時の None 処理、結果は (date, code) 単位の dict リストで返す。
  - feature_exploration:
    - 将来リターン calc_forward_returns（任意ホライズン対応、ホライズン検証あり）。
    - IC（Spearman のランク相関）calc_ic とランク関数 rank。
    - ファクター統計の要約 factor_summary（count/mean/std/min/max/median）。
    - 外部ライブラリ非依存（標準ライブラリ + DuckDB）を設計方針に沿って実装。

### 改善（設計上の配慮）
- ルックアヘッドバイアス対策を徹底:
  - date.today() / datetime.today() をスコア計算やウィンドウ計算の内部で直接参照しない（target_date を引き回す設計）。
  - DB クエリで date < target_date / 排他ウィンドウを使用。
- フェイルセーフを優先:
  - LLM や外部 API の障害時に例外を無闇に投げず、ログ出力して安全側の既定値（例: macro_sentiment=0.0）で継続する箇所を多数実装。
- テスト容易性:
  - OpenAI 呼び出し部は内部で分離しモック差替え可能（unittest.mock.patch の想定）。

### 修正 / 不具合対応
- 初版リリースのため該当なし（以降のリリースで細かいバグ修正や最適化を適宜追加予定）。

### 既知の制約 / 注意事項
- OpenAI API（gpt-4o-mini）依存箇所は API キー（OPENAI_API_KEY）を環境変数か関数引数で提供する必要あり。未設定時は ValueError を送出する。
- DuckDB を前提とする SQL 実装（DuckDB のバージョン差異による型バインドの違いを回避するため executemany を使った個別 DELETE を採用する等の回避策あり）。
- news_nlp と regime_detector は意図的に内部の _call_openai_api 実装を分離しており、共通 private 関数を共有していない（モジュール結合を低減）。
- calendar_update_job や ETL の J-Quants / jquants_client 依存部分は外部クライアント実装に依存する（モック可能）。

---

今後のリリース予定:
- strategy / execution / monitoring の具体的実装と統合（実運用の発注ロジック、モニタリングとアラート機能）。
- パフォーマンス最適化、テストカバレッジ拡充、ドキュメント整備。