CHANGELOG
=========

すべての変更は Keep a Changelog の規約に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （なし）

0.1.0 - 2026-04-03
------------------

初回リリース。日本株自動売買プラットフォームのコア機能群を提供します。以下はコードベースから推測される主な追加内容と設計上の注記です。

Added
- パッケージ骨格
  - kabusys パッケージを追加。サブモジュールとして data, research, ai, monitoring, strategy, execution 等を公開する設計（__all__ に "data", "strategy", "execution", "monitoring" を定義）。
  - バージョン: 0.1.0。

- 設定 / 環境変数管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装。プロジェクトルートの検出は __file__ を起点とし .git または pyproject.toml を探索して決定するため、CWD に依存しない。
  - .env パーサ実装: export 形式・クォート・エスケープ・インラインコメント処理に対応。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、J-Quants / kabu ステーション / LINE / DB パス / 監視設定 / システム設定（env, log_level, is_live 等）をプロパティ経由で取得可能。必須キー未設定時は ValueError を送出する _require を実装。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いた銘柄ごとの記事集約ロジックを実装。
    - プロンプト設計と gpt-4o-mini（OpenAI）を用いた JSON Mode 呼び出しで銘柄ごとのセンチメント（-1.0～1.0）を算出し ai_scores テーブルへ書き込み。
    - バッチサイズ・文字数上限・記事数上限等のトークン膨張対策（_BATCH_SIZE, _MAX_CHARS_PER_STOCK, _MAX_ARTICLES_PER_STOCK）。
    - 再試行（429 / ネットワーク / タイムアウト / 5xx）に対する指数バックオフを実装。リトライ非対象エラーはスキップしてフェイルセーフに継続。
    - レスポンスの堅牢なバリデーションと JSON 復元ロジック（余計な前後テキストを含むケースに対応）。
    - テスト容易性のため _call_openai_api を patch で差し替え可能。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等的に書き込む処理を提供。
    - マクロ記事選別はキーワード（日本・米国・グローバル）ベースでタイトルを抽出し、OpenAI（gpt-4o-mini）へ JSON 出力を要求してセンチメントを取得。
    - API 呼び出しのリトライ、5xx の扱い、失敗時のフォールバック（macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス防止のため datetime.today() を直接参照せず、prices_daily クエリは target_date 未満のデータのみ参照する等の安全策を導入。
    - テスト用フック（_call_openai_api の差し替え）を用意。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar を元に営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。DB 未取得時は曜日ベースのフォールバック（週末除外）を採用。
    - JPX カレンダー差分取得の夜間バッチ（calendar_update_job）を実装。バックフィル、健全性チェック（異常に未来の last_date を検出した場合はスキップ）を実装。
    - 最大探索範囲制限（_MAX_SEARCH_DAYS）で無限ループを防止。

  - ETL パイプライン（pipeline, etl）
    - ETLResult データクラスを導入（取得数・保存数・品質問題・エラー一覧・ヘルパープロパティ等）。
    - 差分取得、保存（jquants_client の save_* を利用して冪等保存）、品質チェックの実行を想定した設計。backfill の概念やエラー/品質問題は呼び出し元に伝搬するが ETL 自体は可能な限り継続する方針。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

  - jquants_client（参照のみ）
    - calendar_management や pipeline が jquants_client を利用する設計（fetch/save 関数への依存）。

- 研究モジュール（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M）、200日 MA 乖離、ATR（20 日）、流動性（20 日平均出来高・出来高比率）、バリュー（PER/ROE）等のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を用いた SQL ベースの実装で、対象は prices_daily / raw_financials（外部 API 呼び出しなし）。
    - データ不足時の None ハンドリングやログ出力を実装。

  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（情報係数）計算（calc_ic）、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等の外部依存を避け、標準ライブラリと DuckDB のみで実装。

  - research.__init__ で関連ユーティリティ（zscore_normalize 等）を再エクスポート。

Changed
- 設計方針の明示
  - 全体として「ルックアヘッドバイアスを防ぐ」「DB 書き込みは冪等に」「API エラーはフェイルセーフ（継続）」等の実務的な設計方針を採用。

Fixed
- （今回リリースは初版のため既知のバグ修正履歴なし）

Deprecated
- （なし）

Removed
- （なし）

Security
- OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY で渡す設計。未設定時は明示的にエラーを投げる。環境自動ロードは DISABLE フラグで抑止可能。
- .env 読み込みで既存 OS 環境変数を保護するため protected セットを導入（.env.local は上書き可能だが OS 環境は保護）。

Notes / Known limitations / 今後の作業案
- OpenAI 呼び出しは gpt-4o-mini の JSON Mode を想定。将来的な SDK / API 変更に対する互換性を監視する必要あり。
- DuckDB の executemany の仕様差分（空リスト不可等）に対応した実装を採用しているため、将来 DuckDB のバージョン差による影響があり得る。
- ai モジュールはレスポンスパース失敗時にスコア 0.0 またはスキップするフェイルセーフを採っているが、運用上は API エラーの監視と再実行方針を整備することを推奨。
- テスト容易性のため内部 API 呼び出し箇所は patch 可能な設計になっている（ユニットテスト用のフックを用意）。

作者注: 上記はソースコードからの推測に基づく CHANGELOG です。実際のリリースノート作成時はリリース日・変更差分・既知の互換性問題等を実際の開発履歴に合わせて更新してください。