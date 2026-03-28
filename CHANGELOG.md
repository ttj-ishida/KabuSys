CHANGELOG
=========

全般
----
このプロジェクトは Keep a Changelog の形式に準拠して記載しています。
日付はリリース日を表します。

[0.1.0] - 2026-03-28
-------------------

Added
- 初回リリース (0.1.0) — 日本株自動売買 / データ基盤 / 研究用ユーティリティ群を提供。
- パッケージエントリポイント
  - kabusys.__init__ によりバージョン (0.1.0) と主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定値を読み込む自動ローダーを実装。
  - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない）。
  - .env のパースは export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などに対応する柔軟な実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、必須キー取得時は _require() で未設定なら ValueError を送出。
  - 主な環境変数（必須またはデフォルトあり）:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパス）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL の検証

- AI モジュール (kabusys.ai)
  - ニュースセンチメント解析 (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信してセンチメントを算出。
    - チャンク処理（最大 20 銘柄/API 呼び出し）、1 銘柄あたり記事数上限・文字数上限、結果のバリデーションと ±1.0 クリップを実装。
    - リトライ戦略：429・ネットワーク断・タイムアウト・5xx を指数バックオフでリトライ。その他エラーはスキップしてフェイルセーフ。
    - DuckDB への書き込みは部分置換（対象コードのみ DELETE → INSERT）で冪等性と部分失敗耐性を確保。DuckDB の executemany の空リスト制約に対応。
    - calc_news_window: JST ベースのニュースウィンドウ計算を提供（前日 15:00 JST ～ 当日 08:30 JST 相当）。
    - テスト容易性のため _call_openai_api を patch できる設計。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定して market_regime テーブルに冪等書き込み。
    - マクロニュースは raw_news からマクロキーワードで抽出（最大 20 件）して LLM に渡す。記事がなければ LLM を呼ばずマクロセンチメント=0。
    - OpenAI 呼び出しは独立実装でモジュール結合を避ける。API エラー時はフォールバック（macro_sentiment=0.0）。
    - リトライ・バックオフ・エラー分類（5xx は再試行）を実装。

- データプラットフォーム (kabusys.data)
  - ETL パイプライン (kabusys.data.pipeline / ETLResult)
    - 差分取得・保存・品質チェックのための ETLResult データクラスを公開。
    - 最終取得日の取得ユーティリティ、テーブル存在チェック、backfill ロジックなどを実装。
    - 保存後の品質チェック結果を保持し、致命的エラーや品質エラー判定のヘルパーを提供。
  - ETL 入口の再エクスポート (kabusys.data.etl)
    - ETLResult を再エクスポート。
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダーの差分取得・夜間バッチ更新（calendar_update_job）を実装。J-Quants クライアントとの連携で冪等保存を行う。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。DB 登録値を優先し、未登録日は曜日ベースでフォールバック。
    - 安全対策として最大探索日数や健全性チェック（未来日が極端に先の場合はスキップ）を導入。
    - calendar_update_job はバックフィル・ルックアヘッド・例外ハンドリングを備える。

- リサーチ用ユーティリティ (kabusys.research)
  - factor_research
    - モメンタム (calc_momentum): 1M/3M/6M リターン、200 日 MA 乖離を計算。データ不足時は None を返す。
    - ボラティリティ / 流動性 (calc_volatility): 20 日 ATR（true range の扱いに注意）、相対 ATR、20 日平均売買代金、出来高比を計算。
    - バリュー (calc_value): raw_financials から最新の財務を取得し PER / ROE を計算（EPS 0/欠損時は None）。
    - 設計上、本モジュールは prices_daily / raw_financials のみ参照し、発注系や外部 API にはアクセスしない。
  - feature_exploration
    - 将来リターン計算 (calc_forward_returns): 任意ホライズンの将来リターンを一括取得する SQL 実装。horizons の検証あり。
    - IC 計算 (calc_ic): factor と forward return を code で結合し、Spearman のランク相関（ρ）を計算。3 レコード未満は None。
    - ランキングユーティリティ (rank): 同順位は平均ランク、丸め誤差対策として round(v, 12) を採用。
    - 統計サマリー (factor_summary): count/mean/std/min/max/median を計算。None 値を除外。
  - research パッケージの __init__ で主要関数を再エクスポート（zscore_normalize は kabusys.data.stats から）。

- 共通実装・設計上の注意
  - DuckDB を主要な分析 DB として利用。SQL と Python の組合せで計算を行う実装方針。
  - ルックアヘッドバイアス対策: 主要な処理は datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る。
  - OpenAI 連携では JSON Mode（厳密 JSON）を前提としたパースと、レスポンスの堅牢な復元ロジックを実装（前後テキスト除去ロジック等）。
  - API 呼び出しのテスト容易性を考慮し、内部の _call_openai_api 等を patch 可能な実装にしている。
  - DB 書き込みは冪等を重視（DELETE→INSERT、ON CONFLICT 等）し、部分失敗でも既存データを不用意に消さないよう配慮。

Changed
- 該当なし（初回リリースのため）。

Fixed
- 該当なし（初回リリースのため）。

Deprecated
- 該当なし。

Security
- OpenAI API キーや各種トークンは環境変数管理を想定。Settings._require により未設定時は早期に通知。
- .env 自動読み込みは必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD でオフにでき、テストや CI での秘匿管理に配慮。

Notes / 運用メモ
- OpenAI を使う機能（news_nlp.score_news, regime_detector.score_regime）は実行時に OPENAI_API_KEY が必要。api_key 引数で注入可能。
- DuckDB/テーブルスキーマは本リポジトリ外で管理される想定。ETL/カレンダー/AI モジュールは所定のテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など）を前提とする。
- DuckDB の executemany が空リストを受け取れないバージョン（例: 0.10）への互換性が考慮されているため、空チェックを行っている。
- ログレベルや環境は Settings で検証され、不正な値は ValueError を送出するため、運用時は環境整備を推奨。

今後の予定（例）
- strategy / execution / monitoring サブパッケージの具体的な戦略実装・発注ロジック・モニタリング連携の追加。
- ai モデルやプロンプトのチューニング、バッチ処理の性能改善。