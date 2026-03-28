CHANGELOG
=========

すべての日付はリリース日を示します。フォーマットは Keep a Changelog に準拠しています。

Unreleased
----------
（なし）

[0.1.0] - 2026-03-28
--------------------

Added
- 初回公開リリース。パッケージ名: kabusys, バージョン: 0.1.0。
- パッケージの公開インターフェースを追加（kabusys/__init__.py）。
- 環境変数／設定管理モジュールを追加（kabusys.config）。
  - .env/.env.local の自動読み込み（プロジェクトルートの検出: .git または pyproject.toml）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env 行パーサ（コメント、export 形式、クォート/エスケープ対応）。
  - 必須環境変数取得用 _require と Settings クラス（J-Quants、kabu、Slack、DB パス、環境判定、ログレベル等）。
  - env / log_level のバリデーション（許容値チェック）。
- AI モジュール群を追加（kabusys.ai）。
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）。
    - target_date に対するニュース収集ウィンドウ計算（JST → UTC 変換）。
    - raw_news / news_symbols を銘柄ごとに集約、テキスト長と記事数のトリム。
    - バッチ（最大20銘柄）で OpenAI（gpt-4o-mini）へ送信、JSON Mode を期待。
    - リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフ、失敗時はスキップ継続。
    - レスポンスバリデーション（JSON 抽出、results 配列、code と score の検証）、スコアを ±1.0 にクリップ。
    - DuckDB への冪等書き込み（DELETE → INSERT、executemany の空リスト回避）。
    - public API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
    - テストしやすさのため _call_openai_api を patch 可能に実装。
  - 市場レジーム判定（kabusys.ai.regime_detector）。
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で判定（'bull'/'neutral'/'bear'）。
    - prices_daily / raw_news を DuckDB から参照し、レジームスコアを market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - LLM 呼び出し失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - API キー注入可能、内部 OpenAI クライアント生成、リトライ・バックオフ処理を含む。
    - テスト用に _call_openai_api を差し替え可能。
- データ関連モジュールを追加（kabusys.data）。
  - マーケットカレンダー管理（kabusys.data.calendar_management）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（土日非営業日）。
    - カレンダー存在有無に依存しつつ一貫した挙動を保証。
    - calendar_update_job により J-Quants から差分取得 → 保存（バックフィル、健全性チェック、ON CONFLICT 置換）を実装。
  - ETL パイプライン（kabusys.data.pipeline）。
    - 差分取得、保存（jquants_client 経由）、品質チェックフレームワークとの連携設計。
    - ETLResult データクラスを導入（target_date, fetched/saved counts, quality_issues, errors 等）。
    - バックフィル、最小データ日付や品質エラー判定ロジックを備える。
  - etl の公開エントリ（kabusys.data.etl → ETLResult の再エクスポート）。
- リサーチ／ファクター分析モジュールを追加（kabusys.research）。
  - ファクター計算（kabusys.research.factor_research）。
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）を DuckDB クエリで計算。
    - 欠損またはデータ不足の取り扱い（None を返す等）。
  - 特徴量探索（kabusys.research.feature_exploration）。
    - 将来リターン（horizons デフォルト [1,5,21]）の計算、rank/IC（Spearman）計算、統計サマリー。
    - pandas 等に依存しない実装。
  - 公開ユーティリティの再エクスポート（zscore_normalize 等）。
- 各モジュールでの共通設計方針（ドキュメント化）
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない設計（target_date に基づく）。
  - DuckDB を主なデータストアとして使用し、SQL と Python の組み合わせで実装。
  - API 呼び出しの失敗は通常フォールバック（スキップ・中立スコア）して処理継続（安全優先）。
  - DB 書き込みは冪等化・トランザクション（BEGIN/COMMIT/ROLLBACK）で実装、ROLLBACK 失敗時のログ出力あり。
  - OpenAI 呼び出しは JSON mode を期待し、応答パースの堅牢性を高めるため前後テキストの補正ロジックを実装。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI の API キーは関数引数経由で注入可能（api_key 引数）。環境変数 OPENAI_API_KEY に依存する挙動もサポート。
- 環境変数の自動ロードは明示的フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト環境配慮）。

Notes / Implementation details
- OpenAI クライアント呼び出しは各モジュールで独立実装（モジュール間でプライベート関数を共有しない設計）。テスト時はこれらの内部関数を patch して API 呼び出しをモック可能。
- DuckDB バインドや executemany の互換性問題（空リスト不可）に対処するため事前チェックを行っている。
- calendar_update_job は jquants_client.fetch_market_calendar / save_market_calendar に依存。API エラーや不具合はログ化して 0 を返す設計。
- 各種定数（バッチサイズ、リトライ回数、バックオフ秒数、ウィンドウ定義等）はモジュール内で明示的に定義されているため、将来的に調整可能。

Developer notes
- 今後の改善候補:
  - ai モジュールの OpenAI モデルやレスポンスフォーマットの抽象化（テストと将来のモデル差替えを容易に）。
  - ETL のジョブスケジューリングや監査ログ出力の拡張。
  - raw_financials の PBR/配当利回りなどバリュー指標の追加。
  - calendar_update_job の並列化や差分フェッチの最適化。

---

このリリースはコードベースの初期機能セット（データ収集 ETL、カレンダー管理、ファクター計算、ニュース／レジームの AI スコアリング、設定管理）を網羅しています。必要であれば、各モジュールの変更点や実装上の注意点をさらに詳細に分割して追記します。