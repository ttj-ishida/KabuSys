Keep a Changelog 準拠の CHANGELOG.md（日本語）

全ての変更はセマンティックバージョニングに従います。  
このファイルはコードベースから推測して作成した初期リリースの変更履歴です。

Unreleased
---------
（空）

[0.1.0] - 2026-03-31
-------------------
Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - パッケージ化エントリポイントを追加（src/kabusys/__init__.py）。
  - __all__ に data, strategy, execution, monitoring を公開。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env および .env.local ファイルの自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
  - export KEY=val 形式やクォート、インラインコメント等を考慮した .env パーサー実装。
  - 既存の OS 環境変数を保護する protected 値の概念を導入。
  - 必須環境変数取得ユーティリティ _require と Settings クラスを提供。
  - 設定項目: J-Quants, kabuステーション, Slack, DuckDB/SQLite パス, 環境種別（development/paper_trading/live）, ログレベル等。
  - 環境値の妥当性検証（KABUSYS_ENV、LOG_LEVEL の許容値チェック）。

- AI 関連モジュール（src/kabusys/ai/）
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いたセンチメント評価を行い ai_scores テーブルへ書き込むパイプラインを実装。
    - 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で計算（UTC naive datetime を返す）。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたりの記事数・文字数上限、429/ネットワーク/タイムアウト/5xx に対する指数バックオフとリトライを実装。
    - レスポンスの堅牢なバリデーション（JSON パース回復処理、"results" 構造確認、コード正規化、スコア数値変換、クリッピング）。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - regime_detector（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュースベースの LLM マクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルに冪等書き込みを実行。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - マクロニュースはキーワードベースで raw_news から抽出し、OpenAI を呼んで JSON をパースしてスコア化。
    - API 障害時は macro_sentiment=0.0 のフェイルセーフ、リトライ/バックオフを実装。
    - OpenAI クライアント生成箇所は明示的に分離（news_nlp と内部関数を共有しない設計）。

- データプラットフォーム（src/kabusys/data/）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理ユーティリティ（market_calendar テーブル）を提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の営業日判定ロジックを実装。
    - DB データがない場合は曜日ベースのフォールバック（週末除外）を採用。
    - 夜間バッチ calendar_update_job を実装（J-Quants クライアント経由で差分取得、バックフィル、健全性チェック、保存）。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult データクラスを実装して ETL 処理の取得数・保存数・品質問題・エラーを集約。
    - 差分更新、バックフィル、品質チェックの設計方針に基づいたユーティリティを提供（J-Quants クライアントと quality モジュールとの連携を想定）。
    - 内部ユーティリティで DuckDB 上のテーブル存在確認や日付最大値取得を実装。
  - etl モジュール（src/kabusys/data/etl.py）で ETLResult を再エクスポート。

- Research（src/kabusys/research/）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）, Volatility（20 日 ATR 等）, Value（PER, ROE）等のファクター計算を実装。
    - DuckDB の SQL ウィンドウ関数を利用した高速な集計。
    - データ不足時は None を返すなど堅牢性を考慮。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（任意ホライズン）、IC（Spearman の ρ）計算、rank、factor_summary（count/mean/std/min/max/median）など研究用ユーティリティを実装。
    - pandas 等に依存せず標準ライブラリ + DuckDB のみで実装。
  - research パッケージの __all__ で主要関数を公開。

- 汎用 / 実装方針（全体）
  - DuckDB を主要な組み込み分析 DB として採用（各モジュールは DuckDB 接続を受け取る設計）。
  - ルックアヘッドバイアス防止：datetime.today()/date.today() を直接参照しない設計思想を各 AI / 研究モジュールで徹底。
  - DB 書き込みは冪等性を重視（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK を使用）。
  - API 呼び出しに関しては 429/ネットワーク断/タイムアウト/5xx をリトライ対象にし、非 5xx の APIError は即時フェイルセーフで処理継続。
  - テスト容易性を考え、外部 API 呼び出し箇所（_call_openai_api 等）をモック差し替え可能に設計。
  - ロギングメッセージを各関数に充実させ、失敗時のフォールバック動作や警告出力を明示。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で供給。環境変数がない場合は ValueError を送出して明示的に失敗する設計。

Notes / 備考
- DB スキーマ（テーブル名: prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）がコード内で参照されます。実行には想定のテーブル定義・データが必要です。
- OpenAI モデルはデフォルトで gpt-4o-mini を使用。JSON Mode を前提としたレスポンス処理を行います。
- .env パーシングは POSIX 系 .env の一般例にかなり忠実に実装されていますが、極端なフォーマットは未検証です。
- 実際の本番売買（execution）に関わるモジュールは __all__ に含まれるものの、この差分からは発注ロジックは見えていません（本リリースはデータ収集・研究・スコアリング基盤に注力）。

もしこの CHANGELOG に補足してほしい箇所（例: モジュール別の API 使い方、既知の制限、テストのポイントなど）があれば指示してください。