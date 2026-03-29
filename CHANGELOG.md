Keep a Changelog準拠 — CHANGELOG.md
==================================

すべての重要な変更はこのファイルに記録します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/ に準拠します。

0.1.0 - 2026-03-29
------------------

Added
- 初回公開: KabuSys v0.1.0 をリリース。
- パッケージ公開情報
  - パッケージトップでのバージョン管理: kabusys.__version__ = "0.1.0"
  - top-level の公開サブパッケージ: data, strategy, execution, monitoring（__all__ 指定）
- 環境設定管理 (kabusys.config)
  - .env ファイル自動読み込みを実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env のパース周りの挙動を細かく実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理（クォートあり/なしで挙動を区別）。
    - ファイル読み込み時のIOエラーは警告を出して安全にスキップ。
    - override / protected の概念を導入し、OS 環境変数を保護して .env.local による上書き制御が可能。
  - Settings クラスを提供（settings インスタンスをエクスポート）。
    - J-Quants / kabuステーション / Slack / DB パスなどのプロパティを定義（必須値は未設定時に ValueError を送出）。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL のバリデーションを実装。
    - duckdb/sqlite の既定パスを提供 (data/kabusys.duckdb / data/monitoring.db)。
- AI モジュール (kabusys.ai)
  - ニュースNLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約して銘柄別にテキストを生成し、OpenAI（gpt-4o-mini、JSON mode）へバッチ送信してセンチメント(ai_score) を算出。
    - タイムウィンドウ計算 (前日15:00JST〜当日08:30JST に対応する UTC naive datetime を返す calc_news_window) を実装。
    - バッチ処理: 最大 _BATCH_SIZE（20）銘柄、1銘柄あたりの記事数/文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - OpenAI 呼び出しのリトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装。API エラーやパース失敗はフェイルセーフでスキップし続行。
    - レスポンスの厳格なバリデーション（JSON 抽出、results リスト、各要素の code/score 検証、数値化と ±1.0 クリップ）。部分成功時のデータ保護のため、ai_scores の更新は取得済みコードのみを DELETE → INSERT。
    - テスト容易性のため _call_openai_api を関数として切り出し、patch による差し替えが可能。
    - score_news(...) API を公開し、書き込み銘柄数を返す。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロニュースは raw_news からキーワードフィルタで抽出（定義済みキーワード群）。
    - OpenAI 呼び出し（gpt-4o-mini、JSON mode）で macro_sentiment を取得。API のリトライ処理とフェイルセーフ（失敗時 macro_sentiment=0.0）を実装。
    - レジームスコア合成ロジック（MA 重み 70%、マクロ重み 30%、スケーリングと clip）を実装し、閾値によりラベル化。
    - market_regime への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。書き込み失敗時は ROLLBACK を試行して例外を上位へ伝播。
    - テスト差替え用に内部 OpenAI 呼び出しを分離（news_nlp と意図的に別実装）。
- データプラットフォーム / ETL (kabusys.data)
  - ETL パイプライン (kabusys.data.pipeline)
    - 差分取得、backfill、保存、品質チェックのための骨組みを実装。
    - ETLResult データクラスを実装し、処理統計（取得数/保存数/品質問題/エラー）を集約。to_dict() で品質問題の要約出力を提供。
    - DuckDB のスキーマ/テーブル存在チェックや最大日付取得ユーティリティを実装。
    - 初回ロード用の最小データ日付、カレンダー先読み日数、バックフィル日数等の定数を設定。
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を用いた営業日判定/探索ロジックを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar が存在しない場合は曜日ベース（土日除外）でフォールバックする設計により、DB がまばらでも一貫性を保持。
    - calendar_update_job 実装: J-Quants クライアント経由で差分取得し保存。バックフィル・健全性チェック（大きく未来にずれた last_date の検出）を実装。API 例外時は安全に 0 を返却して処理継続。
  - ETL の互換性考慮: DuckDB 0.10 の executemany の制約（空リスト不可）を考慮した実装。
  - jquants_client 経由での保存/取得フローを想定（jq.fetch_* / jq.save_* の利用）。
- リサーチ用ユーティリティ (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: mom_1m/mom_3m/mom_6m、200日MA乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金(avg_turnover)、出来高比(volume_ratio) を計算。必要日数が足りない場合は None を返す。
    - calc_value: raw_financials と prices_daily を結合し PER（EPS が 0/欠損時は None）と ROE を算出。target_date 以前の最新財務を取得するクエリを実装。
    - すべて DuckDB クエリベースで実装し、外部 API へはアクセスしない設計。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD により一括計算。horizons の入力検証あり。
    - calc_ic: スピアマンランク相関（ランクは同順位の平均ランク）を実装。有効レコードが 3 件未満のときは None を返す。
    - rank: 値リストを平均ランクに変換（浮動小数点の丸めで ties 検出の安定化）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算。
  - kabusys.research.__init__ で主要関数を再エクスポート。
- テスト/デバッグに配慮した実装上の配慮
  - OpenAI 呼び出し箇所を内部関数化して unittest.mock.patch により差し替えやすくしている（news_nlp._call_openai_api, regime_detector._call_openai_api）。
  - レスポンスの JSON 抽出ロジックは余計な前後テキストを含むケースにも耐えるように最外の {} を抽出して復元を試みる。
  - ルックアヘッドバイアス対策: ほとんどの処理で datetime.today()/date.today() を内部参照せず、target_date を明示的に受け取る設計。

Known issues / Notes
- データ不足や API エラー時はフェイルセーフとして中立（ma200_ratio=1.0、macro_sentiment=0.0、スコア取得失敗はスキップ）する設計のため、外部的には「安全に無視」されるが、呼び出し元は戻り値／ログで失敗を検出する必要があります。
- 一部の機能（strategy, execution, monitoring など）はエントリポイントとして __all__ に含まれているが、このリリースでの詳細実装はコードベースに依存します（本CHANGELOGは提供されたコードから推測して記載）。
- OpenAI の利用には環境変数 OPENAI_API_KEY（または各 API 呼び出しの api_key 引数）が必要です。未設定時は ValueError が発生します。

注記: 上記はコードベースの内容から推測して作成した CHANGELOG です。必要に応じて実際のリリース日・追加情報・未記載の修正点を反映してください。