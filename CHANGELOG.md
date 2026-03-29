# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [0.1.0] - 2026-03-29

### Added
- 基本パッケージ構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - パッケージの公開インターフェースを __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定/ロード機能（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルートを .git または pyproject.toml を起点に探索して自動で .env/.env.local を読み込む（CWD 非依存）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用）。
  - 高度な .env パーサを実装（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いを考慮）。
  - OS 環境変数をプロテクトして .env.local による上書き挙動を制御。
  - Settings クラスを提供し、アプリケーション設定をプロパティで取得可能。
    - J-Quants / kabuステーション / Slack / DB パス / 実行環境（development, paper_trading, live）/ログレベル等のプロパティを実装。
    - 必須環境変数の未設定時に明確な ValueError を送出するバリデーションを実装。

- ニュース・NLP（AI）機能（src/kabusys/ai）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を元に、定められた時間ウィンドウ（前日15:00 JST 〜 当日08:30 JST）に基づき銘柄ごとにニュースを集約。
    - OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメントスコアを取得。
    - チャンク処理（最大20銘柄/リクエスト）、トークン肥大対策（記事数・文字数の上限）、レスポンスバリデーション、スコアの ±1.0 クリップを実装。
    - 429/ネットワーク断/タイムアウト/5xx に対するエクスポネンシャルバックオフリトライを実装。致命的な API エラーは該当チャンクをスキップして継続（フェイルセーフ）。
    - スコア書き込みは冪等化（対象コードのみ DELETE → INSERT）して部分失敗時の既存データ保護を実現。
    - テスト用フック: _call_openai_api を unittest.mock.patch で差し替え可能。
    - 公開 API: score_news(conn, target_date, api_key=None) — 書き込んだ銘柄数を返す。
    - ユーティリティ: calc_news_window(target_date)（JST→UTC のウィンドウ計算）。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、news_nlp によるマクロセンチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を判定。
    - マクロニュースはマクロキーワードでフィルタし、LLM（gpt-4o-mini）で -1.0〜1.0 のスコアを取得。API 失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - OpenAI 呼び出しに対するリトライ・バックオフ、JSON パースの堅牢化を実装。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書込失敗時は ROLLBACK を試みて例外を伝播。
    - 公開 API: score_regime(conn, target_date, api_key=None) — 成功時に 1 を返す。

- データプラットフォーム（src/kabusys/data）
  - calendar_management モジュール（src/kabusys/data/calendar_management.py）
    - JPX（市場）カレンダー管理機能を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が存在しない場合は曜日ベース（土日休）でフォールバックする一貫した挙動。
    - 夜間バッチ更新 job (calendar_update_job) を実装し、J-Quants クライアントから差分取得して冪等保存（fetch/save を呼び出す箇所を実装）。
    - バックフィル、先読み、健全性チェック（過度に未来の日付を検出した場合のスキップ）を実装。
  - ETL & Pipeline（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - ETLResult データクラスを実装し、ETL の取得/保存件数、品質問題、エラー概要を集約。to_dict により監査ログ用に変換可能。
    - 差分更新のためのユーティリティ（テーブル存在チェック、最大日付取得、トレーディング日調整等）を実装。
    - ETLResult を data.etl で再エクスポート（__all__ に ETLResult）。
    - 設計方針として、backfill による後出し修正吸収、品質チェックは呼び出し元で判断する形（Fail-Fast 非採用）を採用。

- リサーチ（src/kabusys/research）
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - Momentum / Volatility / Value 等の各種ファクター計算を実装。
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離等を計算。
    - calc_volatility(conn, target_date): 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算。
    - calc_value(conn, target_date): raw_financials から EPS/ROE を取得して PER/ROE を計算（EPS が 0/欠損なら None）。
    - DuckDB を用いた SQL ベースの実装で、結果は (date, code) をキーとする dict のリストで返却。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns(conn, target_date, horizons): 将来リターン（任意ホライズン）を一括クエリで取得。ホライズンは検証あり（1..252）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を実装。有効レコードが 3 未満の場合は None を返す。
    - rank(values): 同順位は平均ランクで処理（丸めによる tie 判定対策あり）。
    - factor_summary(records, columns): count/mean/std/min/max/median を標準ライブラリのみで計算する統計サマリー。
  - research パッケージの __all__ に主要関数を公開（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーは引数で注入可能かつ環境変数 OPENAI_API_KEY を参照する実装。未設定時は ValueError を投げ明示的にエラーを通知。

---

注記:
- 全体的に「ルックアヘッドバイアスを避ける」設計方針が徹底されており、date/datetime の取り扱いや DB クエリの排他条件（target_date 未満等）で未来データ参照を防止しています。
- OpenAI 呼び出し部分はテスト容易性のために差し替え可能な設計（モジュール内の _call_openai_api を patch）となっています。
- DuckDB を主要な永続化層として想定した実装で、executemany の空リスト回避など DuckDB 固有の注意点にも対策が入っています。