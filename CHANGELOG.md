CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

リリース日はコードベースから推測した作成日を使用しています。

Unreleased
----------

- （現時点ではなし）

0.1.0 - 2026-03-31
------------------

Added
- 初期リリース: kabusys パッケージを追加。日本株自動売買 / データプラットフォーム / 研究用ユーティリティ群を提供。
- パッケージ公開情報:
  - バージョン: 0.1.0
  - パッケージ名: kabusys
  - エクスポートモジュール: data, strategy, execution, monitoring（__all__ にて公開）
- 環境設定:
  - 環境変数読み込みモジュールを実装（kabusys.config）。
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み（デフォルト）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーは export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント判定をサポート。読み込み時に OS 環境変数を保護する仕組み（protected keys）を用意。
  - Settings クラスを実装し、主要設定値をプロパティ経由で取得（必須項目は _require により未設定時に ValueError を送出）。
  - 対応する環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL。

- データプラットフォーム（kabusys.data）:
  - ETL パイプライン基盤（kabusys.data.pipeline）を実装。
    - ETLResult データクラスを定義（取得/保存件数、品質問題、エラー一覧等を保持）。
    - 差分更新、バックフィル、品質チェック、DuckDB テーブル上の最大日付取得等のユーティリティを実装。
  - calendar_management モジュール:
    - JPX マーケットカレンダー管理（market_calendar テーブルを基に営業日判定）を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の提供。
    - calendar_update_job により J-Quants API から差分取得 → 冪等保存（ON CONFLICT 相当）を行うバッチ処理を実装。バックフィル・健全性チェックを含む。
    - カレンダーデータ未取得時は曜日ベース（土日休）でフォールバックする堅牢設計。

  - etl モジュールは pipeline.ETLResult を再エクスポート。

- 研究・解析ツール（kabusys.research）:
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離等のモメンタムファクター計算。
    - calc_volatility: 20 日 ATR, ATR 割合, 平均売買代金, 出来高比等のボラティリティ・流動性指標算出。
    - calc_value: raw_financials からの EPS/ROE を用いた PER / ROE 計算（target_date 以前の最新財務データを参照）。
    - DuckDB SQL とウィンドウ関数を活用した高効率実装。入力は prices_daily / raw_financials。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（例: 1,5,21 営業日）の将来リターン取得（LEAD を使用）。
    - calc_ic: スピアマンランク相関（IC）計算（欠損・同値処理に注意）。
    - rank: 同順位は平均ランクを返すランク付けユーティリティ（浮動小数丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median の統計サマリー。

  - 研究用ユーティリティをトップレベル __all__ でエクスポート（calc_momentum 等）。

- AI 関連（kabusys.ai）:
  - ニュース NLP（kabusys.ai.news_nlp）:
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へ送信、センチメント（-1.0〜1.0）を ai_scores テーブルへ保存する score_news を提供。
    - JST ベースのニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window に実装。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/コール）、トークン肥大対策（記事数上限・文字数トリム）を備える。
    - API エラー（429, ネットワーク, タイムアウト, 5xx）に対する指数バックオフリトライ実装。非再試行のエラーやレスポンス不正はフェイルセーフによりスキップして継続。
    - レスポンス検証（JSON 抽出、results 配列の妥当性、コード照合、スコア数値＆有限性確認）を実装。テスト用に _call_openai_api をパッチ差し替え可能。
    - DuckDB への書込は冪等に行う（DELETE → INSERT、部分失敗時は他銘柄スコアを保護）。

  - レジーム検出（kabusys.ai.regime_detector）:
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出する score_regime を実装。
    - ニュースは news_nlp.calc_news_window と raw_news から抽出、OpenAI を用いて macro_sentiment を算出（記事なしまたは API 失敗時は 0.0 フォールバック）。
    - レジームスコアはクリップし閾値でラベル化。結果を market_regime テーブルへ冪等書き込み。
    - OpenAI クライアント呼び出し、API エラーとリトライ処理、レスポンスパースエラーハンドリングを備える。news_nlp とは独立した _call_openai_api 実装でモジュール結合を避ける設計。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Notes / 実装上の重要な設計判断
- ルックアヘッドバイアス対策:
  - 日付計算に datetime.today()/date.today() を不用意に使用しない設計（target_date を明示的に渡すことでテスト容易性と再現性を確保）。
  - DB クエリでは target_date 未満／以上の排他条件を適切に用いる。
- フェイルセーフ設計:
  - 外部 API （OpenAI / J-Quants）失敗時はスコアを 0.0 にフォールバックする、または該当銘柄だけスキップするなど局所的に安全に継続する実装。
- DuckDB 互換性:
  - executemany に空リストを渡さない等、DuckDB 実装差分への配慮を行った実装。
- テストフック:
  - OpenAI 呼び出し関数はモジュール内で切り替え可能に設計（unittest.mock.patch による差し替えを想定）。
- ロギング:
  - 重要な分岐・警告・エラーで logger を使用し、運用時のトラブルシュートを想定した情報を記録。

導入上の注意
- OpenAI API を利用する機能（score_news / score_regime）を実行するには OPENAI_API_KEY の指定（引数または環境変数）が必要。
- Settings の必須プロパティに対応する環境変数が不足していると ValueError を発生するため、.env を用いた設定または OS 環境変数の設定を推奨。
- DuckDB/SQLite のデフォルトパスは設定で指定可能（DUCKDB_PATH / SQLITE_PATH）。

今後の予定（想定）
- strategy / execution / monitoring モジュールの詳細実装と実稼働向けの安全対策（発注ガード、取引ログ、モニタリング）を追加予定。
- J-Quants クライアント周り（認証・レート制御）の強化と E2E テスト整備。

----- 
（この CHANGELOG は、提供されたコードの内容と設計コメントから推測して作成しています。実際の開発履歴と差異がある場合があります。）