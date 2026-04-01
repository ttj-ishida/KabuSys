# Changelog

すべての非破壊的変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトの初期リリースの内容をコードベースから推測してまとめています。

フォーマット:
- 重大な変更は Breaking Changes として明示します（本初版では該当なし）。
- 日付はリリース日（本ドキュメント作成日: 2026-04-01）です。

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-04-01

初回リリース。以下の主要コンポーネントと機能を実装／公開しました。

### Added
- パッケージ基盤
  - kabusys パッケージの公開（__version__ = 0.1.0）。主要モジュール (data, strategy, execution, monitoring) を __all__ でエクスポート。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを導入。
  - プロジェクトルート自動検出（.git または pyproject.toml を起点）。
  - .env/.env.local の自動読み込み（OS 環境変数を保護、.env.local は上書き）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 複雑な .env フォーマット対応:
    - export KEY=val 形式対応
    - シングル／ダブルクォート内でのバックスラッシュエスケープ処理
    - 行内コメントルール（クォート外で直前が空白／タブの '#' をコメントとみなす）
  - 必須値チェック用 _require と各種プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - DB ファイルのデフォルトパス（DUCKDB_PATH, SQLITE_PATH）、監視設定（PID_FILE_PATH 等）、しきい値（CPU/MEM/DISK）、実行環境（KABUSYS_ENV）とログレベル検証を実装。
  - is_live / is_paper / is_dev ヘルパー。

- AI モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約し、銘柄ごとのニューステキストを OpenAI（gpt-4o-mini）でバッチ評価。
    - JST 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を明示的に計算する calc_news_window。
    - 1 銘柄あたりの最大記事数および文字数のトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - バッチ処理（デフォルト _BATCH_SIZE=20）、JSON Mode を使った厳格なレスポンス検証。
    - 429 / ネットワーク断 / タイムアウト / 5xx の際の指数バックオフリトライ。致命的でない失敗はスキップして継続するフェイルセーフ設計。
    - レスポンスの堅牢なパース/バリデーション（JSON 抽出、results 配列検査、コード照合、数値検証、スコアの ±1.0 クリップ）。
    - DuckDB への冪等書き込み（DELETE → INSERT、executemany 前に空チェック）で部分失敗時の既存データ保護。
    - テスト用に OpenAI 呼び出しを差し替え可能（_call_openai_api を patch 可能）。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して日次で 'bull' / 'neutral' / 'bear' を判定。
    - ma200_ratio の計算は target_date 未満のデータのみ使用しルックアヘッドを防止。
    - マクロキーワードによる raw_news フィルタリング（日本・米国・グローバルの主要語句リスト）。
    - OpenAI 呼び出しは JSON mode（gpt-4o-mini）で厳密 JSON を期待。API 障害時は macro_sentiment=0.0 で継続。
    - リトライ・バックオフ、5xx とそれ以外の扱いの違いに基づくフォールバック。
    - 計算結果は market_regime テーブルにトランザクション (BEGIN/DELETE/INSERT/COMMIT) で冪等的に保存。例外発生時は ROLLBACK を試行。

- データプラットフォーム (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar を用いた営業日／SQ判定、next/prev_trading_day、get_trading_days の実装。
    - market_calendar が未取得の場合は曜日ベース（土日除外）でフォールバック。
    - カレンダー夜間バッチ更新 calendar_update_job: J-Quants から差分取得・バックフィル・健全性チェックを実装。
    - 最大探索日数、先読み／バックフィル日数、健全性検査の閾値を設定し無限ループや異常データを防止。

  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを導入（取得・保存件数、品質問題リスト、エラーリスト等を保持）。
    - 差分更新・バックフィル・品質チェック（quality モジュール連携）を想定した設計。
    - jquants_client の save_* 関数を用いた冪等保存を前提。

  - データ操作ユーティリティ（_table_exists, _get_max_date 等の内部ユーティリティ）。

- リサーチモジュール (kabusys.research)
  - factor_research
    - モメンタム (calc_momentum): 1M/3M/6M リターンと 200 日 MA 乖離を算出（必要行数不足時は None を返す）。
    - ボラティリティ／流動性 (calc_volatility): 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を算出。
    - バリュー (calc_value): raw_financials と prices_daily を組合せて PER（EPS が 0/NULL の場合は None）、ROE を算出。
    - DuckDB 上で SQL を駆使した効率的実装（外部 API に依存しない、安全な read-only 分析）。
  - feature_exploration
    - 将来リターン計算 (calc_forward_returns): 複数ホライズンの将来終値リードを用いたリターン算出。horizons のバリデーションあり。
    - IC 計算 (calc_ic): スピアマンのランク相関（ランクは平均ランク処理、必要レコード数チェック）。
    - ランク変換ユーティリティ (rank) とファクター統計サマリ (factor_summary) を提供。
    - pandas 等に依存しない純標準ライブラリ実装。

- その他
  - モジュール間の結合を低く保つ設計（例: news_nlp と regime_detector で OpenAI 呼び出し実装を共有しない）。
  - ロギングを各モジュールで使用（情報／警告／例外ログを適切に記録）。

### Changed
- （初版につき該当なし）

### Fixed
- （初版につき該当なし）

### Removed
- （初版につき該当なし）

### Security
- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を使用。キーの管理は環境変数／シークレット管理を推奨。
- .env 自動ロードは OS 環境の上書きを防ぐ設計（protected set）で導入。

### Notes / Known limitations
- OpenAI への呼び出しは gpt-4o-mini を前提とした実装（レスポンス JSON mode を期待）。将来的なモデル変更時には _MODEL 定数の更新が必要。
- DuckDB 依存: 実行環境に DuckDB と適切なスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）が必要。
- 一部の ETL / jquants_client / quality モジュール本体はここに含まれていない（参照のみ）。実運用には外部モジュールの実装が必要。
- 日付処理は意図的に date/datetime を直接参照する実装を避け、target_date を明示的引数として与えることでルックアヘッドバイアスを防止する設計になっています。ユニットテストしやすい設計です。

---

今後の予定（例）
- strategy / execution / monitoring の実装充足、注文ロジック・実行レイヤーの追加。
- 品質チェック（quality）の詳細実装・ETL の自動ジョブ化。
- 単体テストと CI の整備、OpenAI 呼び出しのモックテスト追加。

もしこの CHANGELOG の内容について追記や修正したい点があれば教えてください。