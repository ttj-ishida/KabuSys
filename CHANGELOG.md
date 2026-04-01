# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
このプロジェクトでは "Keep a Changelog" の形式に従います。  

なお、ここに記載した内容はソースコードから推測して作成した変更履歴です。

## [0.1.0] - 2026-04-01

### Added
- パッケージ初回リリース。
  - パッケージメタ情報:
    - バージョン: 0.1.0
    - パッケージ名: kabusys
    - 公開モジュール群: data, strategy, execution, monitoring（__all__ でエクスポート）

- 環境・設定管理（kabusys.config）を実装
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準に探索）。
  - .env のパース仕様:
    - 空行・コメント行（#）を無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のエスケープ処理を考慮した値抽出。
    - クォートなしの場合、直前がスペース・タブの '#' をインラインコメントとみなす。
  - .env 読み込みの優先順位: OS 環境変数 > .env.local > .env
  - OS 環境変数を保護する protected 機能（既存キーの上書きを防止）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
  - 設定ラッパー Settings を提供（プロパティで取得）:
    - J-Quants / kabuステーション / Slack / DB パス（DuckDB/SQLite）/監視閾値/システム設定（env, log_level, is_live 等）。
  - 設定のバリデーション:
    - KABUSYS_ENV の許容値制約（development/paper_trading/live）
    - LOG_LEVEL の許容値制約

- AI モジュール（kabusys.ai）を実装
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI (gpt-4o-mini) に送信してセンチメント（-1.0〜1.0）を算出。
    - JST 時間ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を calc_news_window で提供（UTC naive datetime を返す）。
    - バッチ処理: 最大 20 銘柄／API コール（_BATCH_SIZE）。
    - 1 銘柄あたりの記事数・文字数のトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - レート制限(429)/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。
    - JSON Mode のレスポンス検証・回復処理（前後の余計なテキストを含む場合は最外の {} を抽出してパース）。
    - レスポンス検証ルール: results リスト、各要素に code と score、未知コードは無視、スコアは数値かつ有限で ±1.0 にクリップ。
    - DuckDB への書き込みは冪等（DELETE → INSERT）で、部分失敗時に既存スコアを保護する実装。空パラメータでの executemany を回避する安全策あり。
    - score_news API を公開（conn, target_date, api_key 引数）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算（target_date 未満のデータのみを使用してルックアヘッドバイアスを排除）。データ不足時は中立（1.0）にフォールバック。
    - マクロニュース抽出は news_nlp.calc_news_window とマクロキーワードによるフィルタ（最大 20 件）。
    - OpenAI 呼び出し（gpt-4o-mini）へのリトライ・エラーハンドリング（RateLimit/接続/タイムアウト/5xx を考慮）。API 失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - スコア合成式と閾値に基づくラベル付け、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - score_regime API を公開（conn, target_date, api_key 引数）。

- データ基盤モジュール（kabusys.data）を実装
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の提供。
    - market_calendar が未取得のときは曜日（平日）ベースのフォールバックを使用。
    - DB 登録値優先、未登録日には曜日フォールバックで一貫性を確保。
    - 夜間バッチ calendar_update_job を実装（J-Quants から差分取得・バックフィル・健全性チェック・保存）。
  - ETL パイプライン（kabusys.data.pipeline および etl 再エクスポート）
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー一覧を格納、to_dict をサポート）。
    - 差分更新・バックフィル・品質チェックの設計に基づく処理を実装。jquants_client を利用して冪等保存（ON CONFLICT DO UPDATE）を想定。
    - テーブル存在チェックや最大日付取得等のユーティリティを実装。
  - jquants_client 連携を想定（fetch/save 関連の呼び出しポイントあり）。
  - data.etl は pipeline.ETLResult を再エクスポート。

- 研究・ファクター分析モジュール（kabusys.research）
  - factor_research: calc_momentum, calc_volatility, calc_value を実装
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None を返す挙動）。
    - Volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率等を計算（真のレンジ計算で NULL 伝播制御）。
    - Value: raw_financials から最新財務を取り出し PER・ROE を計算（EPS が 0 または欠損時は None）。
    - DuckDB SQL を活用した高効率な実装。外部 API にはアクセスしない。
  - feature_exploration: calc_forward_returns, calc_ic, rank, factor_summary を実装
    - 将来リターン計算（horizons パラメータ、入力検証、一度のクエリで複数ホライズン取得）。
    - IC（Spearman の ρ）をランクに基づき算出（同順位は平均ランク処理）。
    - 統計サマリー（count/mean/std/min/max/median）を算出するユーティリティ。
    - pandas 等に依存せず標準ライブラリのみで実装。

- ロギングとフェイルセーフ設計
  - 多くの箇所で詳細な logger 呼び出しを追加し、API 失敗やデータ不足時に警告・情報ログを出力する設計。
  - DB 書き込みで例外発生時は ROLLBACK を試行し、ROLLBACK 失敗時は警告を出す実装。

### Changed
- （初回リリースなので変更履歴は該当なし）

### Fixed
- （初回リリースなので修正履歴は該当なし）

### Security
- OpenAI API キーや各種機密情報は Settings 経由で環境変数から取得する設計。キー未設定時は ValueError を送出して明示的に失敗させる。

---

補足:
- 本CHANGELOGはコードベースを解析して推測した初回リリース内容を記載しています。実際の変更履歴や公開パッケージのリリースノートと差がある場合があります。必要であれば、リリース担当者によるレビューで文言修正・追記を行ってください。