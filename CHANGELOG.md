# CHANGELOG

すべての注記は Keep a Changelog の形式に準拠しています。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース。

### Added
- パッケージ基本情報
  - kabusys パッケージの初期バージョンを追加（__version__ = 0.1.0）。
  - パッケージ公開 API に data, strategy, execution, monitoring を含める。

- 環境設定/ローダー (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml）。  
    - 読み込み順: OS 環境変数 > .env.local > .env。  
    - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パース: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いを正確に処理。
  - 保護キー (protected) を用いた上書き制御（OS 環境変数の保護）。
  - 必須環境変数取得用の _require と、主要設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などを必須として取得。
    - KABUSYS_ENV (development|paper_trading|live) と LOG_LEVEL 値検証。
    - デフォルト DuckDB/SQLite パス（data/kabusys.duckdb, data/monitoring.db）。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約し、OpenAI (gpt-4o-mini) を用いて銘柄ごとのセンチメント ai_score を計算する score_news を追加。
  - ニュース収集ウィンドウ計算 calc_news_window を実装（JST の前日 15:00 〜 当日 08:30 を UTC に変換）。
  - バッチサイズ、文字数・記事数の上限、チャンク単位での API コールとレスポンスバリデーションを実装。
  - 再試行（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで処理。
  - レスポンス検証: JSON 抽出、"results" キー・型チェック、コード正規化、スコアの数値検査、±1.0 でクリップ。
  - DB 書き込みは部分失敗時の保護を考慮し、対象コードのみ DELETE → INSERT（トランザクション）で更新。
  - テスト用の置換ポイント: _call_openai_api を unittest.mock で差し替え可能。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%、news_nlp による記事抽出 + OpenAI）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を追加。
  - マクロ判定はマクロキーワード集に基づき raw_news のタイトルを抽出して LLM に投げる設計。
  - OpenAI 呼び出しの再試行/バックオフ、API 失敗時のフェイルセーフ（macro_sentiment = 0.0）を実装。
  - レジーム合成はスコアをクリップし閾値でラベル付け。
  - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
  - 設計上ルックアヘッドバイアス対策: datetime.today() や date.today() を内部で参照しない、SQL クエリで date < target_date を使う等。

- Data モジュール
  - calendar_management:
    - JPX マーケットカレンダーの夜間差分更新ジョブ calendar_update_job を追加（J-Quants クライアント経由で取得し保存）。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day の営業日判定および探索ユーティリティを実装。
    - market_calendar が未取得のときの曜日ベースのフォールバック、DB 値優先の一貫した補完ロジックを提供。
    - 最大探索範囲制限 (_MAX_SEARCH_DAYS)、バックフィル、健全性チェック (_SANITY_MAX_FUTURE_DAYS) を導入。
  - pipeline / etl:
    - ETLResult データクラスを追加し、ETL 実行結果（取得件数・保存件数・品質問題・エラー）を構造化して返却できるように。
    - ETL 設計方針に従った差分更新・バックフィル・品質チェックのためのユーティリティ関数群を実装（内部ユーティリティとして _table_exists, _get_max_date, _adjust_to_trading_day 等）。
    - kabusys.data.etl から ETLResult を再エクスポート。

- Research モジュール（kabusys.research）
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials を用いてモメンタム・ボラティリティ・バリュー系ファクターを算出。
    - 200 日移動平均乖離、1/3/6 ヶ月リターン、20 日 ATR、平均売買代金、出来高比率、PER/ROE 等を計算。
    - データ不足時は None を返し、結果は (date, code) キーの dict リストとして返却。
  - feature_exploration:
    - calc_forward_returns: 任意のホライズン（デフォルト [1,5,21]）に対する将来リターンを一括クエリで取得。
    - calc_ic: ファクターと将来リターン間のスピアマンランク相関（IC）を計算。
    - rank: 同順位の平均ランクを取るランク関数（丸めを行い ties 対応）。
    - factor_summary: count/mean/std/min/max/median を計算する集計ユーティリティ。
  - kabusys.research パッケージの __all__ に主要関数を整備。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数の読み込みにおいて OS 環境変数を保護する仕組み（protected set）を実装し、意図せぬ上書きを防止。

### Notes / 設計上の重要点
- 外部 API（OpenAI / J-Quants）呼び出しは冪等性・フェイルセーフを重視:
  - LLM API の一時失敗はリトライ（指数バックオフ）で回復を試み、最終的には安全側のデフォルト値（例: macro_sentiment=0.0）で継続する。
  - DB 書き込みはトランザクションを使用し、ROLLBACK の失敗時も警告ログを出力。
- ルックアヘッドバイアス防止:
  - 日付処理で datetime.today()/date.today() を直接参照しない実装方針（全関数共通）。
- テストしやすさ:
  - OpenAI 呼び出しの内部関数はテスト用にモック差し替え可能。
  - .env 自動ロードはテスト時に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- DuckDB 互換性考慮:
  - executemany に空リストを渡さない防護や、list バインドの不確実性を避ける実装（個別 DELETE を用いる等）。

---

以上が v0.1.0 のリリースノートです。今後のリリースでは、strategy / execution / monitoring モジュールの実装・テストカバレッジ・運用ドキュメントの追加などを予定しています。