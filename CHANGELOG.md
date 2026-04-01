CHANGELOG
=========

このプロジェクトは Keep a Changelog の形式に従い、セマンティック バージョニングを採用します。
リリースノートは人間と自動化されたリリースプロセスの両方で参照されることを想定しています。

フォーマット:
- Unreleased: 今後の修正・追加予定
- 各リリースは日付付きで記載

Unreleased
----------
- 修正予定:
  - data.pipeline._get_max_date にタイポ（return date.fro）が見られ、実行時エラーを引き起こします。date.fromisoformat 等に修正する必要があります。
  - jquants_client など外部依存のモック/テストカバレッジ強化。
  - DuckDB バージョン依存（executemany に空リスト不可）の扱いに関する説明とテストの追加。
- 機能追加検討:
  - strategy / execution / monitoring パッケージの実装拡充（現状インターフェースのみ公開）。
  - OpenAI 呼び出しのオンライン設定（モデル切替等）を環境変数で柔軟化。

[0.1.0] - 2026-04-01
--------------------

Added
- パッケージ基盤
  - kabusys パッケージ初期リリース。サブパッケージとして data, research, ai, research, monitoring, strategy, execution （__all__ による公開）を用意。

- 環境設定管理 (kabusys.config)
  - Settings クラスを導入し、環境変数および .env / .env.local から設定を安全に読み込む自動ロード機能を実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を起点）により CWD に依存しない .env ロードを実現。
  - .env パーサに以下を実装:
    - export KEY=val 形式の対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしでのインラインコメント（#）取り扱い
  - 自動ロードの無効化オプション: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 必須設定取得用の _require() と、各種設定プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）
  - 設定値検証（KABUSYS_ENV の許容値検査、LOG_LEVEL 検査）とヘルパー is_live / is_paper / is_dev

- AI モジュール
  - kabusys.ai.news_nlp:
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini + JSON Mode）でセンチメントを評価する score_news 関数を実装。
    - JST ベースのニュース時間ウィンドウ計算 (前日 15:00 JST ～ 当日 08:30 JST) を calc_news_window で提供（UTC 変換済み）。
    - バッチ処理（1 回の API 呼び出しで最大 20 銘柄）、記事数と文字数の上限トリミング、レスポンス検証、スコアの ±1.0 クリップ、部分書き換え（DELETE→INSERT）による冪等保存を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフとリトライの実装。API 失敗時はフェイルセーフでスキップ（例外を投げず継続）。
  - kabusys.ai.regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - prices_daily からの過去データ取得は target_date 未満のデータのみを使用することでルックアヘッドバイアスを排除。
    - マクロニュースは kabusys.ai.news_nlp の calc_news_window を利用して抽出、OpenAI 呼び出しは独立実装でモジュール結合を避ける設計。
    - API 失敗時は macro_sentiment=0.0 のフォールバック、DB 書き込みは BEGIN/DELETE/INSERT/COMMIT による冪等処理（失敗時は ROLLBACK）。

- Data / ETL
  - kabusys.data.pipeline:
    - ETLResult データクラスを導入し、ETL 実行の取得・保存・品質チェック結果やエラーを集約して返す仕組みを提供。
    - 差分フェッチ、バックフィル（日数指定）、品質チェックを組み合わせた ETL パイプライン設計に対応するインターフェース（実装はモジュール指針に準拠）。
    - DuckDB を前提とした実装（テーブル存在確認、最大日付取得等）。
  - kabusys.data.etl:
    - ETLResult を再エクスポート（公開インターフェース）。
  - kabusys.data.calendar_management:
    - market_calendar テーブルを用いた JPX カレンダー管理と夜間バッチ更新 calendar_update_job の実装。
    - 営業日判定ユーティリティ: is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days（DB データがない場合は曜日ベースのフォールバック）。
    - API からの差分取得、バックフィル、健全性チェックの設計（lookahead, backfill, sanity checks）。

- Research（因子・特徴量探索）
  - kabusys.research.factor_research:
    - calc_momentum, calc_volatility, calc_value を提供。すべて DuckDB の SQL を利用して計算し、(date, code) ベースの dict リストで結果を返す。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離
    - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率
    - Value: PER, ROE（raw_financials から最新財務情報を参照）
  - kabusys.research.feature_exploration:
    - calc_forward_returns（任意ホライズンでの将来リターン取得）、calc_ic（Spearman ランク相関による IC）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）の実装。
  - kabusys.research.__init__ で主要関数を再エクスポート。

- 共通設計上の配慮
  - ルックアヘッドバイアス回避: いずれのモジュールも datetime.today() / date.today() を直接参照せず、target_date ベースで計算。
  - DuckDB をストレージとして利用（ローカル分析向け）。
  - OpenAI API 呼び出しは JSON Mode を使い、レスポンスの厳密な検証を行う。
  - API エラー時のフェイルセーフ：LLM 呼び出し失敗でも処理全体が例外で停止しない（ログ出力してフォールバックまたはスキップ）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Known issues / 注意点
- data.pipeline._get_max_date に明らかなタイポがあり、実行時に例外が発生する可能性があります（該当箇所: return date.fro）。
  - 推奨修正: 型チェック後に正しい変換を行い、date オブジェクトを返す実装へ修正（例: return val if isinstance(val, date) else date.fromisoformat(str(val))）。
- jquants_client（外部 API クライアント）や実運用向けの credentials は本リリースに含まれていません。実行には環境変数（JQUANTS_REFRESH_TOKEN など）や外部クライアント実装が必要です。
- DuckDB バージョン依存:
  - executemany に空リストを渡すとエラーになることがあるため、空リストチェックを行う実装を採用しています。運用環境の DuckDB バージョンに注意してください。
- OpenAI SDK 依存:
  - openai.OpenAI クラスを利用しています。環境にインストールする OpenAI SDK のバージョン互換性に注意してください。
- テスト:
  - OpenAI 呼び出し部は _call_openai_api を patch によって差し替え可能な設計になっていますが、統合テスト・エンドツーエンドテストの整備が必要です。

その他
- 本リリースは「分析・研究・ETL の基盤」としての初期実装を提供します。strategy（売買ロジック）・execution（発注）・monitoring（プロセス監視）の実装拡充は今後の予定です。

クレジット
- 実装は DuckDB と OpenAI API（gpt-4o-mini）の利用を前提に設計されています。API キーは環境変数で安全に管理してください。

--- 
（注）本 CHANGELOG は提示されたソースコードから推測して作成しています。実際のリリースノートに使用する場合は、テスト結果や実運用での差分を反映してください。