Keep a Changelog
================
すべての重要なリリースノートはこのファイルで管理します。
フォーマットは「Keep a Changelog」に準拠します。
リリースはセマンティックバージョニングに従います。

[Unreleased]
-------------

- 現時点の未リリースの変更点はありません。

[0.1.0] - 2026-03-29
-------------------

Added
- 基本パッケージ構成を追加（kabusys v0.1.0）。
  - パッケージ公開用メタ情報: src/kabusys/__init__.py に __version__="0.1.0" と __all__ を定義。
- 環境変数・設定管理モジュールを追加（kabusys.config）。
  - .env / .env.local 自動読み込み実装（プロジェクトルート判定：.git または pyproject.toml）。
  - export KEY=val 形式やクォート・エスケープ、コメントの扱いに対応したパーサーを実装。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須環境変数取得ヘルパー _require と Settings クラスを提供（J-Quants / kabu / Slack / DB パス / 環境・ログレベルなど）。
  - 環境値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。
  - デフォルトの DB パス（DuckDB / SQLite）や kabu API のデフォルト URL を定義。
- AI 関連モジュールを追加（kabusys.ai）。
  - news_nlp モジュール（kabusys.ai.news_nlp）:
    - raw_news / news_symbols を用いたニュースの銘柄別集約、OpenAI（gpt-4o-mini）へのバッチ投げ（最大20銘柄/チャンク）によるセンチメントスコア算出。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST を UTC に変換）を実装。
    - レスポンスのバリデーション、JSON 抽出フォールバック、スコアの ±1.0 クリップ。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフのリトライ処理とフェイルセーフ（失敗時はスキップして継続）。
    - DuckDB への冪等書き込み（DELETE → INSERT）、部分失敗時に既存データを保護する実装。
  - regime_detector モジュール（kabusys.ai.regime_detector）:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロ記事抽出（キーワードベース）、OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を算出、score 合成とクリップ処理。
    - API 呼び出しのリトライとフォールバック（失敗時 macro_sentiment=0.0）、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）およびロールバック処理。
    - ルックアヘッドバイアスを防ぐ設計（datetime.today() を使用しない、prices_daily の date < target_date 条件）。
- データプラットフォーム関連（kabusys.data）を追加。
  - calendar_management:
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを提供。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - DB が空のときは曜日ベースのフォールバック（土日を非営業日扱い）。
    - calendar_update_job: J-Quants からの差分取得、バックフィル再取得、健全性チェック（将来日付の異常検出）と冪等保存の処理を実装。
  - pipeline / etl:
    - ETLResult データクラス（kabusys.data.pipeline.ETLResult）を実装し、etl モジュールから再エクスポート（kabusys.data.etl）。
    - 差分更新・バックフィル・品質チェックを想定した ETL の設計方針を反映。
    - DuckDB 上のテーブル存在チェックや最大日付取得ユーティリティを実装。
- リサーチ系モジュール（kabusys.research）を追加。
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を DuckDB の SQL ウィンドウ関数で計算。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播制御を考慮。
    - calc_value: raw_financials から最新財務を取得して PER/ROE を計算（EPS=0 や欠損時は None）。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を利用）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を実装。サンプル数が少ない場合は None を返す。
    - rank, factor_summary: ランク付け（同順位は平均ランク）と基本統計量の集計処理を実装。
- テストしやすさ・安全性のための実装上の配慮を多数導入。
  - OpenAI 呼び出し部分はモジュール内でラップしてあり、ユニットテストで差し替え可能（unittest.mock.patch を想定）。
  - 外部 API エラー時のフォールバック（マクロスコア=0 やチャンクスキップ）により全体処理の停止を防止。
  - DuckDB の executemany における空リスト問題への対処（空時は呼ばない）。
  - 例外発生時のトランザクションロールバックとロールバック失敗時の警告ログ出力。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは呼び出し時に引数注入または環境変数 OPENAI_API_KEY を使用する設計。キー解決に失敗した場合は ValueError を送出して明示的に扱うようにしている。

Notes / Implementation details
- 全モジュールで「ルックアヘッドバイアス防止」の設計方針が明示されており、日時の参照は外部から与えられる target_date に依存している（datetime.today()/date.today() を直接参照しない）。
- OpenAI 呼び出しは gpt-4o-mini を想定し JSON mode による厳密な JSON 出力を期待するが、実運用を考慮してレスポンスの余分な文字列を切り出して復元する処理を実装。
- DuckDB を主要な分析用ローカル DB として想定。デフォルトパスは data/kabusys.duckdb。
- kabu API、Slack など運用周りの設定は Settings 経由で集中管理。

今後
- モジュールごとの単体テストの追加（OpenAI モック含む）、CI 連携、パフォーマンス最適化、さらなる品質チェックルールの拡充を想定しています。