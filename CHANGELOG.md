CHANGELOG
=========

すべての注目すべき変更をここに記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- 変更はバージョンごとに分類しています（Added / Changed / Fixed / Security）。
- 日付はリリース日を示します。

Unreleased
----------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-04
-------------------

初回公開リリース。

Added
- パッケージ全体
  - kabusys パッケージの初期版を公開。バージョンは src/kabusys/__init__.py にて "0.1.0" を設定。

- 環境設定 / 設定管理 (kabusys.config)
  - .env 自動読み込み機能を実装
    - プロジェクトルートを __file__ を起点に親ディレクトリから探索（.git または pyproject.toml を判定）。
    - OS 環境変数 > .env.local > .env の優先順位で読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パース機能を強化
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ対応、インラインコメントの取り扱い制御。
  - Settings クラスを提供（settings インスタンスをエクスポート）
    - J-Quants / kabuステーション / LINE / データベース / 監視 / システム系のプロパティを取得。
    - 必須環境変数未設定時は _require() により ValueError を送出。
    - KABUSYS_ENV, LOG_LEVEL の値検証（有効値集合を定義）。
    - パスは pathlib.Path に変換・expanduser して返却。
    - 便利プロパティ: is_live, is_paper, is_dev。

- AI モジュール (kabusys.ai)
  - ニュースセンチメント (kabusys.ai.news_nlp)
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI (モデル: gpt-4o-mini, JSON mode) でセンチメントを算出。
    - 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window() で計算。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄／コール）、1銘柄あたりのトリム（記事数・文字数制限）を実装。
    - 再試行ポリシー: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - レスポンスの厳密なバリデーション: JSON 抽出、results リスト検査、code/score の検査、数値/有限性チェック、スコアを ±1.0 にクリップ。
    - 書き込みは部分失敗耐性を持たせた idempotent な DELETE → INSERT の実装（ai_scores テーブル）。
    - テストしやすさのため _call_openai_api は差し替え可能（unittest.mock.patch を想定）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム ('bull' / 'neutral' / 'bear') を算出。
    - マクロキーワードで raw_news をフィルタし、最大記事数を制限して LLM に渡す。
    - OpenAI 呼び出しは JSON モードで行い、API エラー時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - レジームスコアのクリップと閾値判定を実装。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出。

- データ / カレンダー管理 (kabusys.data.calendar_management)
  - JPX カレンダー管理機能を提供
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - DB (market_calendar) があれば DB 値優先、未登録日は曜日ベース（週末は非営業日）でフォールバックする一貫した判定ロジック。
    - 最大探索日数で無限ループを防止する実装（_MAX_SEARCH_DAYS）。
  - calendar_update_job を実装
    - J-Quants API（jquants_client）から差分取得し market_calendar を冪等保存。
    - バックフィル（直近 _BACKFILL_DAYS の再フェッチ）と健全性チェック（過度の未来日付はスキップ）を実装。

- データ / ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
  - ETLResult dataclass を実装して ETL 結果を構造化（to_dict, has_errors, has_quality_errors を提供）。
  - ETL の設計方針（差分更新、バックフィル、品質チェックの扱い、id_token 注入など）をコードに反映。
  - etl モジュールで ETLResult を再エクスポート。

- 研究用モジュール (kabusys.research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。データ不足は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（EPS が 0/欠損なら None）。
    - 全て DuckDB SQL を用いて一括処理し、(date, code) ベースの dict リストを返す。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons のバリデーションあり。
    - calc_ic: Spearman（ランク相関）で IC を計算。3 銘柄未満で None を返す。
    - rank: 同順位は平均ランクを返す（丸め処理で ties の検出漏れを防止）。
    - factor_summary: count/mean/std/min/max/median を算出（None を除外）。
  - research パッケージの __all__ を整備して主要関数を公開。

- テスト・開発支援
  - API 呼び出し箇所（AI モジュールの _call_openai_api 等）は差し替え可能に実装し、ユニットテストでモックしやすいよう配慮。

Design notes / Implementation details (リリースノート補足)
- ルックアヘッドバイアス回避
  - 各種処理（news/ai/regime/research）は内部で datetime.today() / date.today() を直接参照せず、外部から与えた target_date を基準に処理する設計。
  - DB クエリは target_date より前のみを参照する等、未来データ参照を避ける実装が徹底されている。
- DB 書き込みの冪等性
  - AI スコア・レジームなどのテーブル更新は DELETE→INSERT のパターンや ON CONFLICT 相当の方針で冪等化。
  - 部分失敗時に既存データを不必要に消さない工夫（コードを絞って DELETE→INSERT）。
- フェイルセーフ戦略
  - OpenAI API の失敗時は例外を上位に投げずにデフォルトスコアで継続（macro_sentiment=0.0 等）する処理を導入し、パイプライン全体の停止を防止。
- 互換性
  - DuckDB 0.10 の制約（executemany に空リスト不可等）へ配慮した実装。
- コンフィグの安全性
  - OS 環境変数を protected set として .env で上書きされないようにする実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Acknowledgements / Notes
- OpenAI API（gpt-4o-mini）を利用する機能が含まれます。運用時は API キー管理・コストにご注意ください。
- J-Quants / kabuステーション 等外部 API クライアントは kabusys.data.jquants_client, kabusys.data.jquants_client.save_* などを前提としています。実環境で使用する際はそれらのクライアント実装と環境変数を適切に設定してください。

-----