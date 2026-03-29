CHANGELOG
=========

すべての変更は「Keep a Changelog」フォーマットに従って記載します。  
このファイルは、コードベースから推測できる機能追加・実装方針・重要な挙動をまとめたものです。

フォーマット:
- Added: 新機能、追加されたモジュールや公開 API
- Changed: 実装詳細・設計方針・既存挙動の明確化
- Fixed: 明示的な修正（コードから推測される不具合対策等）
- Security: セキュリティ関連（該当なしの場合は記載しない）

Unreleased
----------
（現在の変更は v0.1.0 に相当する初期実装を表します。将来の変更はここに追加してください。）

[0.1.0] - 2026-03-29
--------------------

Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - src/kabusys/__init__.py によりパッケージ公開。サブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ に記載のうち一部実装あり）。
- 環境設定管理モジュール（kabusys.config）
  - .env および .env.local ファイル、OS 環境変数からの設定読み込み自動化を実装。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パーサを実装: コメント行、export KEY=val 形式、シングル/ダブルクォート中のエスケープ、およびコメントの扱いを適切に処理。
  - 環境変数の必須チェック（_require）と Settings クラスを提供。J-Quants, kabu API, Slack, DB パス、実行環境（development/paper_trading/live）、ログレベルの検証を実装。
- AI 関連
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を元にニュースを銘柄別に集約し、OpenAI（gpt-4o-mini、JSON mode）で銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込み。
    - バッチ処理（最大 20 銘柄/リクエスト）、トークン肥大化対策（記事数・文字数によるトリミング）、JSON レスポンスのバリデーション、スコアのクリップ、リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）を実装。
    - テスト用フック: _call_openai_api をモックで差し替え可能。
    - ニュース収集ウィンドウ計算 calc_news_window を提供（JST ベース → UTC naive datetime を返す）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し、market_regime テーブルへ冪等書き込み。
    - マクロキーワードでニュースを絞り込み、OpenAI を用いてマクロセンチメントを JSON スコアとして取得。API 失敗時は macro_sentiment=0.0 でフォールバックするフェイルセーフを採用。
    - レジーム合成ロジック、閾値、リトライ制御、DB トランザクション（BEGIN/DELETE/INSERT/COMMIT + ROLLBACK の安全処理）を実装。
- Data / ETL / Calendar（kabusys.data）
  - calendar_management: JPX カレンダーの管理ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定 API を提供。
    - market_calendar の有無に応じた DB 優先ロジックと曜日ベースのフォールバック、最大探索日数制限、サニティチェックを実装。
    - calendar_update_job を実装: J-Quants API（jquants_client）から差分取得し market_calendar テーブルへ冪等保存。バックフィル日数や将来日数の健全性チェックを実装。
  - pipeline: ETLResult データクラスと ETL パイプラインユーティリティ
    - ETL 実行結果を表す ETLResult を追加（品質チェック結果・エラーの集約・辞書化ユーティリティを含む）。
    - ETL の差分取得方針、バックフィル、品質チェック方針を実装方針として文書化。
  - etl: pipeline.ETLResult を再エクスポートする薄いラッパーを提供。
- Research（kabusys.research）
  - factor_research: ファクター計算群を実装
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を DuckDB SQL で計算。データ不足時は None を返す設計。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播制御や cnt ベースの有効性チェックを実装。
    - calc_value: raw_financials から直近財務データを取得し PER/ROE を計算（EPS が 0 または NULL の場合は None）。
  - feature_exploration: 将来リターン・IC・統計サマリー
    - calc_forward_returns: 指定 horizon（デフォルト [1,5,21]）に対する将来リターンを一括で取得する SQL 実装。horizons の検証とスキャンレンジバッファを実装。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 未満の場合は None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を計算するユーティリティを提供。
- テスト支援
  - AI モジュール内の OpenAI 呼び出しを差し替え可能（unittest.mock.patch を想定）とすることで、外部 API をモックした単体テストを容易にしている。

Changed
- 実装方針・設計上の注意を全面的に明記
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す）。
  - DB 操作は冪等性を重視（DELETE→INSERT、ON CONFLICT 相当の保存を想定）し、部分失敗時の既存データ保護策を採用。
  - OpenAI 呼び出しでのエラー処理は冗長な例外伝播を避け、フェイルセーフ（スコア 0 やスキップ）で継続する方針。
  - DuckDB のバージョン差異（executemany の空リスト問題等）への互換性対策を実装。
- ロギング・警告の追加
  - データ不足、API パース失敗、ROLLBACK 失敗等のケースで適切な logger.warning / logger.info / logger.exception を出力するよう明記。

Fixed
- （初期実装のため明確な「修正履歴」は無し。ただし以下の設計上のフォールバック/安全策を実装）
  - 外部 API 失敗時のフェイルセーフ（macro_sentiment=0.0、スコア取得失敗時はスキップして他銘柄を保護）。
  - DuckDB 書き込み時のトランザクション/ROLLBACK 保護（ROLLBACK 失敗時の警告ログ出力）。

Notes / Known limitations
- jquants_client（jquants_client.fetch_market_calendar / save_market_calendar 等）はモジュール参照はされているが、この変更ログ記載時点のスニペットには実装コードが含まれていないため、外部実装に依存する。
- OpenAI SDK（OpenAI クライアント）への依存がある（gpt-4o-mini を利用する設計）。実行には OPENAI_API_KEY が必要。
- 一部 API（kabu API、Slack 等）に必要な環境変数は Settings クラスで必須扱い（未設定時は ValueError を送出）。運用時は .env/.env.local または環境変数の設定が必須。
- 日時取り扱いは UTC naive datetime を用いる箇所があるため、DB の保存形式・比較ロジックと時刻基準（JST→UTC 変換）に注意が必要。

作者注
- 本 CHANGELOG は提示されたソースコードから機能・挙動を推測して作成しています。実際のコミット履歴やリリースノートが別途存在する場合、本ファイルは公式履歴の補助的説明として扱ってください。