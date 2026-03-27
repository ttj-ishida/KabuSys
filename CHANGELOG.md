Keep a Changelog準拠

すべての注目すべき変更はこのファイルに記録します。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-27

Added
- パッケージ初回リリース: kabusys v0.1.0
  - パッケージ情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を定義し、主要サブパッケージを __all__ に列挙。
- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機構（プロジェクトルート検出: .git または pyproject.toml ベース）を追加。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは export KEY=val 形式、クォート（シングル／ダブル）、バックスラッシュエスケープ、インラインコメント処理等に対応。
  - 必須値取得時に未設定なら ValueError を投げる _require を提供。KABUSYS_ENV / LOG_LEVEL の検証ロジック、デフォルト値、DBパス（DUCKDB_PATH, SQLITE_PATH）デフォルトも定義。
- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）の JSON モードでセンチメントを評価。
    - JST の運用ウィンドウ（前日15:00〜当日08:30 JST）を UTC に変換する calc_news_window を提供。
    - バッチ処理（最大 20 銘柄/コール）、1銘柄あたりのトリム（記事数・文字数）によるトークン肥大化対策。
    - レスポンスの堅牢なバリデーションとスコアの ±1.0 クリップ。部分失敗時に既存スコアを保護する idempotent な DB 書き込み（DELETE → INSERT）。
    - API 呼び出しで 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。テストのために _call_openai_api を差し替え可能。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書込銘柄数 を返す。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（Nikkei 225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily からのデータ取得は target_date 未満のデータのみを使用しルックアヘッドバイアスを防止。
    - API 失敗時は macro_sentiment=0.0 としてフェイルセーフ。計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 1（成功）。
- データ処理（src/kabusys/data）
  - 市場カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを使った営業日判定のユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 未取得時は曜日ベース（平日＝営業日）でフォールバックし、一貫性を保つ設計。
    - calendar_update_job により J-Quants から差分取得し冪等的に保存（バックフィル・健全性チェック含む）。
  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult データクラスを公開し、ETL 実行結果（取得数・保存数・品質問題・エラー）を集約。
    - 差分更新、バックフィル、品質チェック統合のための基盤ロジックを実装（jquants_client 経由での保存・品質チェック呼び出しを想定）。
- 研究用モジュール（src/kabusys/research）
  - factor_research.py: calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials 参照）。出力は (date, code) ベースの辞書リスト。
    - Momentum: 約1M/3M/6M リターン、200 日 MA 乖離。
    - Volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率。
    - Value: PER, ROE（raw_financials の最新レコードを使用）。
  - feature_exploration.py: calc_forward_returns（複数ホライズン、LEAD を用いた取得）、calc_ic（Spearman ランク相関）、factor_summary（基本統計）、rank（同順位は平均ランク）を実装。
  - research パッケージは主要関数を __all__ で再エクスポート。
- 共通ユーティリティ
  - DuckDB を前提とした SQL クエリ中心の実装で、外部 API 等のサイドエフェクトを最小化。
  - ロギング、警告、例外ハンドリングを各所で実装し運用での追跡を容易に。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数読み込みで OS 環境変数を保護する仕組み（ロード時に既存キーを protected として扱う）を導入。
- API キー未設定時は明示的な ValueError を送出し、意図しないキー漏洩や無効な呼び出しを防止。

Notes / 設計上の重要事項
- ルックアヘッドバイアス対策: 各モジュール（news_nlp, regime_detector, research など）は内部で datetime.today()/date.today() を参照せず、target_date に依存するためテスト・再現性が高い設計。
- フェイルセーフ: 外部 API（OpenAI / J-Quants 等）が失敗した場合でも例外で即終了させず、可能な範囲でデフォルト値を使って継続する箇所が多く存在（運用での頑健性向上）。
- テストしやすさ: OpenAI 呼び出し箇所は内部関数を patch できるように実装されており、ユニットテストで外部呼び出しを差し替え可能。
- DuckDB executemany に対する互換性配慮（空リストバインド回避）や SQL の互換性を意識した実装。

今後の予定（例）
- PBR / 配当利回りなどバリューファクターの拡張。
- モデル学習 / 戦略実行モジュールの追加（strategy / execution / monitoring パッケージの充実）。
- J-Quants クライアント周りの実装補完と ETL の運用強化。

--- 

（注）本 CHANGELOG はソースコードからの推測に基づき作成しています。実際のリリースノートとして用いる際は必要に応じて補正してください。