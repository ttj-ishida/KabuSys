Changelog
=========

すべての注目すべき変更履歴はこのファイルに記載します。  
このプロジェクトは Keep a Changelog の慣習に従います。  

フォーマット:
- 変更はセクション（Added, Changed, Fixed, Removed, Security）ごとに分類しています。
- 各リリースはバージョンと日付で表記します。

Unreleased
----------
（次回リリースのための保留中の変更があればここに記載します）

0.1.0 - 2026-03-28
------------------

Added
- 初回リリース。パッケージ名: kabusys（__version__ = "0.1.0"）。
- パッケージ構成と公開 API:
  - モジュール群を公開: data, strategy, execution, monitoring。
  - research パッケージで主な研究用関数を再エクスポート（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
  - data.etl で ETLResult を公開。

- 環境設定管理 (kabusys.config):
  - .env / .env.local ファイルと OS 環境変数からの設定読み込み機能を実装。
  - プロジェクトルートの自動検出ロジック（.git または pyproject.toml を起点）。
  - .env パーサーの実装（export プレフィックス、クォート内エスケープ、インラインコメント処理に対応）。
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスによりアプリ設定をプロパティで提供（必須項目は _require で ValueError を送出）。
  - 主要環境変数のキー:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - OPENAI_API_KEY を参照する AI 機能（関数呼び出し時に引数で上書き可能）
  - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
  - KABUSYS_ENV のバリデーション（development / paper_trading / live）と LOG_LEVEL バリデーション。

- データプラットフォーム (kabusys.data):
  - calendar_management:
    - JPX カレンダー管理（market_calendar テーブルの活用）。
    - 営業日判定ヘルパー: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - 夜間バッチ更新 job: calendar_update_job（J-Quants から差分取得、バックフィル、健全性チェック）。
    - DB 未取得時は曜日ベースでフォールバックする堅牢な動作。
  - pipeline / ETL:
    - ETLResult データクラス（ETL の取得数・保存数・品質問題・エラーの集約）。
    - 差分取得 / backfill の方針、品質チェック統合（quality モジュールとの連携を想定）。

- 研究・特徴量 (kabusys.research):
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離 (ma200_dev) を計算。
    - calc_volatility: 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials からの EPS/ROE を用いた PER / ROE 計算（未実装項目は明記）。
    - 全関数は DuckDB の prices_daily / raw_financials を参照し、ルックアヘッドバイアスを避ける設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得。
    - calc_ic: スピアマンのランク相関（IC）計算を実装（有効レコードが 3 未満の場合は None）。
    - rank: 同順位は平均ランクを返す実装（数値丸めによる ties を考慮）。
    - factor_summary: count/mean/std/min/max/median の統計サマリ。

- AI／NLP (kabusys.ai):
  - news_nlp:
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini の JSON Mode）へバッチ送信して銘柄ごとの ai_score を ai_scores テーブルへ保存。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive datetime に変換）。
    - バッチ・チャンク処理（最大 20 銘柄 / チャンク）、1 銘柄当たり最大 10 記事・3000 文字にトリム。
    - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ、その他はスキップ。失敗時は部分的に保護して DB 更新（該当コードのみ DELETE→INSERT）。
    - レスポンスバリデーション（JSON パース、results 配列、コード照合、数値検査）、スコアは ±1 にクリップ。
    - テスト容易性: _call_openai_api をパッチ可能。
  - regime_detector:
    - ETF 1321 の 200 日 MA 乖離（重み 70%）と news_nlp 由来のマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書込。
    - マクロニュース取得は calc_news_window を利用（news_nlp と時間同期）。
    - OpenAI 呼び出しは独立実装、最大リトライ・バックオフ、API 失敗時は macro_sentiment=0.0 のフェイルセーフ。
    - レジーム合成ロジック、閾値（BULL_THRESHOLD=0.2, BEAR_THRESHOLD=0.2）を定義。
    - テスト容易性: _call_openai_api をパッチ可能。

Changed
- （初版のため変更履歴なし）

Fixed
- （初版のため修正履歴なし）

Removed
- （初版のため削除履歴なし）

Security
- OpenAI API キーなどの機密情報は環境変数/ .env 経由で取得する設計。自動ローディングを無効化するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を用意。

Notes / 実装上の重要ポイント
- ルックアヘッドバイアス対策: 全ての分析/スコアリング関数は datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を渡す設計。
- DuckDB を主要なローカル分析 DB として使用。SQL と Python の組合せで分析処理を実装。
- OpenAI 呼び出しは gpt-4o-mini を想定し、JSON Mode（response_format={"type":"json_object"}）での利用を前提とした実装。レスポンスパース/バリデーションを慎重に行う。
- テスト容易性を配慮して API 呼び出し実体をモック/patch 可能な設計。
- DB 書き込みは冪等となるよう DELETE→INSERT や ON CONFLICT を意識した実装（ETL や calendar 更新等）。

既知の制約・今後の作業候補
- news_nlp, regime_detector は OpenAI の課金・レート制限の影響を受けるため、実運用時のコスト評価・レート制御の追加検討が必要。
- factor_research の PBR や配当利回りなど一部バリューファクターは未実装（将来的な追加候補）。
- DuckDB への executemany の挙動（空リスト不可）に対するワークアラウンドを実装済みだが、DuckDB バージョン互換性のテストが必要。

---

（注）日付はソースコードを基に推測して設定しています。実際のリリース日やバージョン運用ポリシーに合わせて更新してください。