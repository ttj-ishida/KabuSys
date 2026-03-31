Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

（なし）

0.1.0 - 2026-03-31
------------------

初回公開リリース。

Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョン 0.1.0（src/kabusys/__init__.py）。
  - 公開サブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ に含めているが一部モジュールは実装済み/参照あり）。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイルと環境変数から設定を自動読み込みする機能を実装。
    - 読み込み優先順位: OS 環境 > .env.local > .env
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD 非依存）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを独自実装（コメント／export プレフィックス／クォート、エスケープ処理対応）。
  - 必須設定取得用の Settings クラスを提供（プロパティで各種環境変数を取得し未設定時はエラー）。
    - 必須項目（例）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB デフォルトパス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - 環境モード検証: KABUSYS_ENV は development / paper_trading / live のいずれか、LOG_LEVEL は標準ログレベルのみ許容。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（score_news）
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む。
    - 日次ウィンドウ定義（JST 前日15:00〜当日08:30 相当）と UTC 変換ユーティリティ（calc_news_window）。
    - バッチ送信（最大 20 銘柄／回）、1 銘柄あたり記事数/文字数上限、レスポンス検証、スコア ±1.0 クリップ。
    - API の一時エラー（429・ネットワーク・タイムアウト・5xx）に対する指数バックオフのリトライ処理を実装。
    - 部分成功に備え、書き込みは該当コードのみ DELETE → INSERT を行い既存データ保護。
  - 市場レジーム判定（score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出はキーワードベース（複数キーワード定義）でタイトルを取得し、OpenAI（gpt-4o-mini）で JSON レスポンスを要求して macro_sentiment を算出。
    - API エラーやパース失敗時は macro_sentiment=0.0 としてフェイルセーフ継続。
    - レトライ・ログ出力機構を備える。

  - OpenAI 呼び出しは各モジュールで独立したラッパー関数を実装（テスト時に差し替え可能な設計）。

- データモジュール（src/kabusys/data）
  - カレンダー管理（calendar_management）
    - market_calendar テーブルを前提に営業日判定、前後営業日検索、期間内営業日リスト取得、SQ 判定を提供。
    - DB にデータがない場合は土日ベースのフォールバックを使用。
    - JPX カレンダーを J-Quants から差分取得して market_calendar を更新する夜間バッチ calendar_update_job を実装（バックフィルと健全性チェックあり）。
  - ETL パイプライン（pipeline, etl）
    - ETLResult データクラスを提供し、ETL 実行結果（取得数・保存数・品質問題・エラー）を集約。
    - 差分取得、バックフィル、品質チェックを行う設計方針を反映。
    - DuckDB 上のテーブル存在確認や最大日付取得ユーティリティを実装。
  - jquants_client との連携を前提（fetch/save 機能を利用する想定）。

- Research モジュール（src/kabusys/research）
  - factor_research: Momentum, Volatility, Value ファクター計算を実装
    - calc_momentum：1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算
    - calc_volatility：20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算
    - calc_value：最新の raw_financials を使って PER, ROE を計算
    - すべて DuckDB の prices_daily/raw_financials を参照し副作用なし
  - feature_exploration: 将来リターン・IC 計算・統計サマリーを実装
    - calc_forward_returns：指定ホライズンの将来リターンを一括取得（horizons の検証あり）
    - calc_ic：Spearman（ランク）ベースの IC 計算（十分なデータがない場合は None）
    - rank：同順位の平均ランク付け（丸めによる ties 対策あり）
    - factor_summary：count/mean/std/min/max/median を標準ライブラリのみで計算

Other notable implementation details
- DuckDB を利用した SQL ベースのデータ処理を中心に実装。多くの処理は SQL ウィンドウ関数や LEAD/LAG を併用して効率的に実装。
- ルックアヘッドバイアス回避設計
  - 日付計算や DB クエリで target_date 未満／<= 等の条件を厳密に扱う。
  - datetime.today()/date.today() を解析ロジックの基準に直接使わない設計（テスト可能性とフェアネス確保）。
- ロバストネス / フェイルセーフ
  - OpenAI API 呼び出しのエラー時フォールバック（0.0 等）やログ出力、リトライ等を適用して処理継続を優先。
  - DB 書き込みは冪等（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK を利用）を意識。
- テストしやすい設計
  - OpenAI 呼び出しや内部ヘルパーは差し替え可能（unittest.mock.patch でモックしやすい）。
- 外部依存
  - OpenAI Python SDK（OpenAI クライアント）を利用。AI 機能を使うには OPENAI_API_KEY が必要。
  - J-Quants クライアントは別モジュール（kabusys.data.jquants_client）で扱う想定。

Known limitations / Notes
- OpenAI の利用を伴う機能（score_news / score_regime）は API キー未設定時に ValueError を送出するため、実行前に OPENAI_API_KEY を用意してください。テストでは api_key 引数で注入可能。
- jquants_client の実装はこの変更履歴の範囲外のため、ETL や calendar_update_job の実行には別途 jquants_client の実装が必要。
- 一部テーブル名（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）に依存するので、スキーマ整備が必要です。
- pandas 等の外部データ処理ライブラリに依存しない実装になっているため、既存の DataFrame ベースのツールチェーンとはインターフェースが異なります。
- 現バージョンでは PBR・配当利回りなど一部ファクターは未実装。

Security
- （なし）

Deprecated
- （なし）

Removed
- （なし）

Fixed
- （なし）