CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/（日本語訳に準拠）

Unreleased
----------
（現在変更なし）

0.1.0 - 2026-04-01
------------------

Added
- 初回公開: KabuSys パッケージ v0.1.0 を追加。
  - パッケージエントリポイント:
    - src/kabusys/__init__.py にてバージョンと公開サブパッケージを定義。

- 環境設定 / 設定管理（src/kabusys/config.py）を追加。
  - .env/.env.local を自動読込（プロジェクトルートの検出は .git または pyproject.toml を基準）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサ:
    - export プレフィックス対応、クォート文字内のバックスラッシュエスケープ対応、インラインコメント処理等を実装。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス /監視閾値 / システム設定（KABUSYS_ENV, LOG_LEVEL）等をプロパティで取得。
  - 必須環境変数未設定時は _require() が ValueError を投げるよう設計。

- AI モジュール（src/kabusys/ai/*）を追加。
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - score_news(conn, target_date, api_key=None): raw_news + news_symbols から銘柄毎に記事を集約し、OpenAI（gpt-4o-mini、JSON mode）へバッチ送信してセンチメント（-1.0〜1.0）を算出し ai_scores テーブルへ冪等書き込み。
    - calc_news_window(target_date): JST ベースのニュース収集ウィンドウ計算（前日15:00〜当日08:30 JST を UTC に変換）。
    - バッチ処理: 1 API-call あたり最大 20 銘柄、1 銘柄あたり最大 10 記事・3000 文字にトリム。
    - エラー耐性: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、API 失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - レスポンス検証: JSON 抽出、"results" 構造検証、未知コードの無視、スコアを ±1.0 にクリップ。
    - DuckDB の executemany 周りの互換性考慮（空リストバインドの回避）を実装。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース（重み 30%）の LLM センチメントを合成して market_regime テーブルへ冪等書き込み。
    - ma200_ratio 計算は target_date 未満のデータのみを使用（ルックアヘッドバイアス防止）。データ不足時は中立（1.0）にフォールバック。
    - マクロニュースは raw_news からマクロキーワードでフィルタして LLM（gpt-4o-mini）に送信し JSON レスポンスをパース。API 失敗やパース失敗時は macro_sentiment=0.0 にフォールバック。
    - OpenAI 呼び出しは専用の内部関数でラップし、リトライ戦略を実装。

- リサーチモジュール（src/kabusys/research/*）を追加。
  - factor_research.py:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離(ma200_dev) を計算。
    - calc_volatility(conn, target_date): 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date): raw_financials と prices_daily を組み合わせて PER, ROE を算出（EPS が不正な場合は None）。
    - DuckDB SQL を用いた実装、営業日ベースの horizon とスキャンバッファを考慮。
  - feature_exploration.py:
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（デフォルト [1,5,21]）を計算。ホライズンの検証（1〜252）を実装。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を計算（有効レコードが 3 未満なら None）。
    - rank(values): 同順位は平均ランクで扱うランク化ユーティリティ。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算。
  - 研究用ユーティリティ zscore_normalize を data.stats から再エクスポート。

- データプラットフォームモジュール（src/kabusys/data/*）を追加。
  - calendar_management.py:
    - JPX 市場カレンダー管理、is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - calendar_update_job(conn, lookahead_days=90): J-Quants から差分取得して market_calendar を冪等保存。バックフィル（直近数日再フェッチ）と健全性チェックを実装。
    - DB にデータがない場合は曜日ベース（土日を非営業日）でフォールバックするロジック。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）を用いて無限ループを防止。
  - pipeline.py / etl.py:
    - ETLResult dataclass を定義（ETL 実行結果・品質問題・エラーの集約、to_dict メソッド）。
    - ETL の設計方針（差分更新、backfill、品質チェック、id_token 注入可能など）を実装指針として反映。
    - data/etl.py では pipeline.ETLResult を再エクスポート。

Security / External deps
- OpenAI SDK（OpenAI クライアント）および DuckDB を利用。モデルは gpt-4o-mini を想定。
- API キーは api_key 引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。

Design decisions / 重要な設計方針（ドキュメント化）
- ルックアヘッドバイアス回避: datetime.today() / date.today() に依存する処理を避け、すべての関数は target_date を明示的に受け取る設計。
- DB 書き込みは冪等（DELETE → INSERT / ON CONFLICT 相当）で、部分失敗時に既存データを不必要に消さない方針。
- API 呼び出しはフェイルセーフ設計（重大な例外を上位に伝播させず、可能な限り継続）とする方針。
- DuckDB のバージョン差異（executemany と空リストなど）に配慮した互換実装。

Known issues / 注意事項
- src/kabusys/data/pipeline.py の末尾に不完全な記述（typo のような "return date.fro"）が存在します。実装が途中で切れている可能性があり、該当箇所は修正が必要です。  
  （元コードの提供状況に依存して推測しています）

Notes
- 本リリースはコードベースから推測して作成した初期バージョンの CHANGELOG です。実際のリリースノートとして公開する場合は、テスト結果・既知のバグ修正・セキュリティ考慮（API キー管理等）を反映して更新してください。