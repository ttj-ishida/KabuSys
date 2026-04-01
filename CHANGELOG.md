CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
リリース日付はソースコードからの推測に基づき付与しています。

[0.1.0] - 2026-04-01
--------------------

Added
- 初期リリース: KabuSys 日本株自動売買・データ基盤用ライブラリを追加。
- パッケージのバージョンを src/kabusys/__init__.py にて 0.1.0 に設定。
- 環境設定管理モジュール（kabusys.config）を追加:
  - .env / .env.local の自動読み込み（プロジェクトルートは .git / pyproject.toml で検出）。
  - export KEY=val 形式、シングル/ダブルクォート内のエスケープ、行末コメント等に対応した .env パーサ実装。
  - OS 環境変数の保護（既存値を保護する protected セット）や、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
  - 必須環境変数取得用 _require と Settings クラスを提供。主な環境変数:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（省略時デフォルトあり）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH 等のデフォルトパスを持つ設定
    - KABUSYS_ENV / LOG_LEVEL のバリデーション（development / paper_trading / live 等）

- AI モジュール（kabusys.ai）を実装:
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）:
    - OpenAI（gpt-4o-mini）の JSON Mode を用いたバッチセンチメント解析機能。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）の算出（calc_news_window）。
    - 銘柄毎に記事を集約し（最大記事数・文字数トリム）、最大 20 銘柄／チャンクで API 送信。
    - 再試行（429 / ネットワーク切断 / タイムアウト / 5xx）に対する指数バックオフ処理。
    - レスポンスの厳密なバリデーションとスコアの ±1.0 クリップ。
    - 書き込みは部分失敗を考慮して「影響を受けたコードのみ」DELETE → INSERT の冪等保存。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
  - 市場レジーム判定（kabusys.ai.regime_detector）:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news / market_regime を参照し、計算結果を冪等に DB へ保存（BEGIN/DELETE/INSERT/COMMIT）。ロールバック処理あり。
    - OpenAI 呼び出しは独立実装でモジュール結合を抑制。API エラー時は macro_sentiment=0.0 のフェイルセーフ。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- Research モジュール（kabusys.research）を追加:
  - ファクター計算（kabusys.research.factor_research）:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を算出。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等を算出。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（EPS が 0 / NULL の場合は None）。
    - DuckDB 上で SQL を中心に計算し、(date, code) をキーとする dict のリストを返す設計。
  - 特徴量解析（kabusys.research.feature_exploration）:
    - calc_forward_returns: 翌日/翌週/翌月（デフォルト: [1,5,21]）の将来リターンを計算（LEAD を利用）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。
    - rank: 同順位は平均ランクにするランク関数（round(...,12) による丸めで ties を処理）。
    - factor_summary: カウント／平均／標準偏差／最小／最大／中央値を算出。

- Data モジュール（kabusys.data）を追加:
  - マーケットカレンダー管理（kabusys.data.calendar_management）:
    - market_calendar を参照した is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の判定ロジック。
    - DB にデータがない場合は土日ベースのフォールバック。最大探索日数制限（_MAX_SEARCH_DAYS）やバックフィル戦略を実装。
    - calendar_update_job により J-Quants から差分取得して冪等保存（バックフィル日数・健全性チェックあり）。
  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）:
    - ETLResult データクラスを公開（取得数・保存数・品質チェック結果・エラーを保持）。
    - 差分更新・バックフィル・品質チェックの設計方針に基づく処理を実装するための基盤を用意。
    - DuckDB テーブル存在チェック・最大日付取得などのユーティリティを実装。
  - jquants_client と連携する設計（fetch/save 関数を想定）。

- 研究 / データ処理に関する設計方針を明文化:
  - ルックアヘッドバイアスを避ける（datetime.today()/date.today() を参照しない関数設計）。
  - OpenAI 呼び出しはフェイルセーフで失敗時も処理継続（ゼロ値やスキップで保護）。
  - DuckDB 互換性のための注意（executemany 空リスト回避など）。

Changed
- （初出のため該当なし）

Fixed
- （初出のため該当なし）

Deprecated
- （初出のため該当なし）

Removed
- （初出のため該当なし）

Security
- OpenAI API キー・J-Quants トークン等の機密情報は環境変数で管理することを明示（Settings により必須チェックを行う）。

Notes / 制約・既知の挙動
- OpenAI 連携:
  - score_news / score_regime などの AI 関連 API は OPENAI_API_KEY（もしくは引数での api_key 注入）が必須。未設定時は ValueError を送出する。
  - JSON Mode の性質上、LLM が返すレスポンスのパースに対して耐性（前後余計なテキスト除去の試み）や厳格なバリデーションを実装しているが、LLM の予期せぬ出力によるスキップが発生する可能性がある。
- データベース:
  - DuckDB を前提とする SQL / window 関数が多用されているため、実行環境の DuckDB バージョン互換性に注意（executemany の空リスト等の回避実装あり）。
- .env 自動読み込み:
  - プロジェクトルート検出に .git または pyproject.toml を使用するため、配布形態やインストール後の挙動はプロジェクト構成に依存する。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動読み込みを無効化できる。
- ロギング:
  - 各モジュールで logger を利用し、重要な失敗やフォールバックは WARN/INFO/EXCEPTION で記録される。

今後導入が想定される項目（示唆）
- AI モデルやバッチサイズの設定を外部から調整可能にする設定機能の拡充。
- jquants_client の具体実装・テストヘルパーの整備。
- monitoring / execution 等のランタイム管理モジュールの公開 API とドキュメント整備。

作者注
- 本 CHANGELOG は提示されたソースコードからの実装内容・設計意図を推測して作成しています。実際のコミット履歴や変更履歴が存在する場合は、それに合わせて修正してください。