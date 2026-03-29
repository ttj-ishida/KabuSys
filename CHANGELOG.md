Changelog
=========

すべての変更は Keep a Changelog の準拠フォーマットで記載しています。  
安定版リリース以外の変更は Unreleased に記載します。

Unreleased
----------

- なし（初回リリースにて未リリース変更はありません）。

0.1.0 - 2026-03-29
-----------------

Added
- 初期リリース: kabusys パッケージ v0.1.0 を公開。
- パッケージ構成:
  - パブリック API のエントリポイント src/kabusys/__init__.py を提供（data, strategy, execution, monitoring を __all__ に公開）。
- 設定・環境変数管理 (src/kabusys/config.py):
  - .env ファイルまたは環境変数からの設定読み込みを実装。
  - プロジェクトルートの自動検出ロジックを実装（.git または pyproject.toml を基準）。これにより CWD に依存せずパッケージ配布後も正しく動作。
  - .env のパース機能を実装（export プレフィックス、クォート内のバックスラッシュエスケープ、行末コメントの扱い等に対応）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - protected（既存 OS 環境変数の保護）や override の挙動を実装。
  - 必須変数取得関数 _require と Settings クラスを提供。JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等をプロパティで取得。
  - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の値検証を実装。is_live / is_paper / is_dev 等の便宜プロパティを提供。
  - データベースパスのデフォルト（duckdb, sqlite）を設定。

- AI 関連 (src/kabusys/ai):
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news, news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でバッチ解析して銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（JST 前日15:00〜当日08:30）を calc_news_window で計算。
    - チャンク処理（最大 20 銘柄/回）、記事数/文字数上限、JSON mode のレスポンス検証、スコアの ±1.0 クリップ、リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフを実装。
    - レスポンス検証ロジック（JSON 抽出、results 配列/要素検証、未知コードの無視）を実装。
    - テスト容易性のため _call_openai_api を patch できる設計。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせて日次で market_regime テーブルへ保存するロジックを実装。
    - prices_daily からの ma200_ratio 計算、raw_news からマクロキーワードで抽出したタイトルの LLM 評価、合成スコアとラベル（bull/neutral/bear）算出、DB への冪等書き込み実装。
    - LLM 呼び出しのリトライ・フォールバック（失敗時 macro_sentiment=0.0）を実装。
    - テスト用に _call_openai_api を差し替え可能。

- データ基盤 / ETL / カレンダー (src/kabusys/data):
  - ETL パイプライン (src/kabusys/data/pipeline.py / etl.py)
    - ETLResult データクラスを公開（取得数／保存数／品質問題／エラー等を追跡）。
    - 差分取得・バックフィル・品質検査を想定した設計。DuckDB 接続を受け取り、安全に最大日付取得やテーブル存在チェックを行うユーティリティを実装。
    - DuckDB の executemany に関する空リスト制約に配慮した実装（空の場合は実行しない）。
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルの有無に応じた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。DB 登録値優先、未登録は曜日ベースでフォールバック。
    - calendar_update_job により J-Quants API からの差分取得と保存（バックフィル、健全性チェック）を実装。jquants_client 経由で fetch/save を呼び出す設計。
  - jquants_client と quality モジュールとの連携を想定（実際のクライアント実装は別モジュール）。

- リサーチ / ファクター計算 (src/kabusys/research):
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す設計。
    - calc_volatility: 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金、出来高比率を計算。欠損取扱いを厳密に実装。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算（EPS が 0 または欠損時の扱い）。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 複数ホライズンに対する将来リターンをまとめて計算する汎用実装（horizons の検証を含む）。
    - calc_ic: スピアマンランク相関（IC）計算を実装（結合・None 除外・有効レコード閾値）。
    - rank, factor_summary: ランキング・統計サマリーを標準ライブラリのみで提供。
  - kabusys.data.stats の zscore_normalize を再エクスポート。

- DB / オペレーション方針
  - DuckDB を主要な分析 DB として想定し、idempotent な書き込み（BEGIN / DELETE / INSERT / COMMIT）を多用。
  - ルックアヘッドバイアス防止のため、すべてのアルゴリズムは内部で date / target_date を参照し、datetime.now() などの利用を避ける設計。
  - ロギングを適切に配置し、異常時は警告/例外ロギングを行う。

Changed
- —（初回リリースのため変更履歴なし）

Fixed
- —（初回リリースのため修正履歴なし）

Deprecated
- —（初回リリースのため該当なし）

Removed
- —（初回リリースのため該当なし）

Security
- OpenAI API キーや外部 API トークンは環境変数として取り扱う。OpenAI キー未設定時は AI 関連関数は ValueError を投げるよう明確化。
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト用途）。

Notes / Known limitations
- strategy / execution / monitoring の具体実装は本リポジトリ内の該当コードが未掲載（__all__ には含めているが詳細は今後追加予定）。
- OpenAI のレスポンスは必ずしも整形式 JSON とは限らないため、レスポンス復元やフォールバック（スコア 0.0）を多用している。運用時はログ監視を推奨。
- DuckDB のバージョン依存の挙動（executemany の空リスト取り扱い等）に配慮しているが、運用環境の DuckDB バージョンでの動作確認を推奨。
- jquants_client, quality モジュール等の外部依存は別途用意する必要がある（テスト用のモックやスタブが利用可能）。
- 一部関数に外部 API 呼び出しを伴うため（OpenAI, J-Quants）、運用時は API レートやコスト、認証情報管理に注意。

開発者向けメモ
- テスト容易性を考慮し、AI 呼び出し箇所は _call_openai_api を patch して差し替え可能。  
- 自動 .env ロードはプロジェクトルート検出に依存するため、パッケージ配布後のテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して環境をコントロール可能。
- ログレベルや環境切替は Settings クラス経由で行う設計。