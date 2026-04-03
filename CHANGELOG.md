CHANGELOG
=========

すべての重要な変更点をここに記録します。本ファイルは「Keep a Changelog」準拠の形式で記載しています。

フォーマット:
- 日付は YYYY-MM-DD 形式
- 目立つ変更（機能追加・仕様・バグ修正等）をカテゴリ別に整理しています

Unreleased
----------
（現時点のコードベースに基づく初回リリースを下に記載しています。未リリースの変更はここに追記してください）

0.1.0 - 2026-04-03
------------------

Added
-----
- パッケージ基盤
  - 新規プロジェクト "kabusys" を追加。バージョンは 0.1.0。
  - pakage のトップレベルエクスポート: data, strategy, execution, monitoring。

- 設定 / 環境変数管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルート探索は .git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト等で使用可能）。
  - .env パーサを実装（コメント行、export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等に対応）。
  - 環境変数読み取り用 Settings クラスを提供（J-Quants/OpenAI/kabu/API/DB/監視閾値等の設定をプロパティとして公開）。
  - 環境値のバリデーション（KABUSYS_ENV / LOG_LEVEL の候補値チェック、必須値の取得時に未設定なら例外を投げる _require）。

- データ処理 (kabusys.data)
  - ETL パイプライン基盤（pipeline.ETLResult の公開）。
  - market_calendar を扱うマーケットカレンダー管理（営業日判定、次/前営業日の取得、期間内営業日取得、SQ日判定のユーティリティ群）。
  - calendar_update_job による J-Quants からの差分取得・冪等保存ロジック。
  - ETL の実行結果を格納する ETLResult dataclass（品質検査結果・エラー要約を含むシリアライズ機能あり）。
  - ETL パイプラインのユーティリティ（最終取得日の算出、テーブル存在チェック、差分フェッチ戦略、バックフィル等の設計）。

- ニュース NLP / AI (kabusys.ai)
  - ニュースセンチメントスコアリング（score_news）
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores に書き込む。
    - JSTベースのニュースウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を提供。
    - 1 銘柄あたりの記事・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）でトークン肥大化に対処。
    - 最大 20 銘柄（_BATCH_SIZE）ごとのバッチ送信、JSON Mode を利用して厳密な JSON レスポンスを期待。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフとリトライ実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列チェック、code の正規化、数値・有限性チェック、スコアの ±1.0 クリップ）。
    - 部分成功に備え、取得済み銘柄のみを DELETE→INSERT で置換することで他銘柄の既存スコア保護（DuckDB の executemany 空リスト制約への対応あり）。
    - テスト容易性のため OpenAI 呼び出しのラッパー関数を用意し差し替え可能。

  - 市場レジーム判定（score_regime）
    - ETF 1321（日経225連動）200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を日次判定。
    - prices_daily からの ma200_ratio 計算（対象日はルックアヘッドを防ぐため target_date 未満のデータのみ使用、データ不足時は中立 1.0 にフォールバック）。
    - raw_news からマクロ関連キーワードでフィルタしたタイトルを抽出し、OpenAI で macro_sentiment を算出（記事がない場合は LLM 呼び出しをせず 0.0 を採用）。
    - OpenAI API 失敗時のフェイルセーフ（リトライ・最終的に macro_sentiment=0.0 にフォールバック）と詳細なログ。
    - 計算結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK を試行して例外を伝播）。

- リサーチ / ファクター計算 (kabusys.research)
  - ファクター計算モジュールを提供（prices_daily / raw_financials を利用）。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（cnt_200 チェックでデータ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）。
    - calc_value: raw_financials からの最新 EPS/ROE と当日の株価を用いて PER/ROE を算出（EPS が 0/欠損の場合は None）。
  - 特徴量探索ツール群（kabusys.research.feature_exploration）
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得する効率的なクエリ。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコード数 3 未満は None を返す）。
    - rank: 同順位は平均ランク扱い（丸めで ties 検出漏れを防止）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。

Changed
-------
- （初回リリースのため「Changed」は無し）

Fixed
-----
- （初回リリースのため「Fixed」は無し）

Deprecated
----------
- （現時点では無し）

Removed
-------
- （現時点では無し）

Security
--------
- OpenAI API キーや J-Quants トークン等の必須機密情報は環境変数で管理する設計。必須未設定時は明示的な例外を発生させ安全に失敗する。

Notes / 注意事項
----------------
- OpenAI 関連機能は環境変数 OPENAI_API_KEY（または関数引数での注入）を必要とします。未設定時は ValueError を送出します。
- J-Quants / kabu API のトークンも Settings 経由でアクセスします（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。ドキュメントの .env.example を参考に .env を用意してください。
- DuckDB のバージョン依存（executemany の空リストが不可等）への対処をコード上で行っていますが、運用環境の DuckDB バージョンによりふるまいが異なる可能性があります。
- 時刻処理はルックアヘッドバイアス防止のため、target_date を明示的に受け取り内部で datetime.today()/date.today() を参照しないよう設計されています（再現性・検証に寄与）。
- JSON Mode を期待するが、LLM の出力が厳密な JSON でないケースへのフォールバック処理（文字列中の最外 {} を抽出してパースなど）を実装しています。万一パースに失敗した場合は対象銘柄をスキップし続行する方針です。
- API 呼び出し関数（_call_openai_api 等）はテスト時にパッチできるよう設計されています（unittest.mock.patch により差し替え可能）。

依存関係（主なもの）
-------------------
- duckdb
- openai

貢献・バグ報告
-------------
バグ報告、機能要望、パッチの提出は issue/PR を通じて受け付けてください。変更履歴は本ファイルを更新していきます。

--- End of CHANGELOG ---