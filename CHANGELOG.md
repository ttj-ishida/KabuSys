CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。
このファイルはコードベースの内容から推測して作成しています。

注記
----
- バージョン番号はパッケージ内の __version__ = "0.1.0" に基づく「初版 (0.1.0)」を記載しています。
- 日付はこの CHANGELOG 作成時点の日付を使用しています（推定）。

[Unreleased]
------------
（現在なし）

[0.1.0] - 2026-03-28
--------------------

Added
-----
- 基本パッケージを追加（kabusys v0.1.0）
  - パッケージ初期化: src/kabusys/__init__.py（公開モジュール: data, strategy, execution, monitoring）
- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env ファイル自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml ）
  - .env/.env.local の読み込み順序と override / protected キー機能を実装
  - export KEY=val, クォート/エスケープ、インラインコメントの堅牢なパース実装
  - 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等のプロパティを公開
  - env/log_level の値検証（許容値セット）を実装
- AI モジュールを追加（src/kabusys/ai）
  - ニュースセンチメント解析: news_nlp.score_news
    - OpenAI（gpt-4o-mini）を用いたバッチセンチメント評価
    - タイムウィンドウ計算（前日15:00 JST 〜 当日08:30 JST）と記事集約ロジック
    - バッチサイズ・記事数・文字数制限、JSON Mode のレスポンスバリデーション
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）とエクスポネンシャルバックオフ
    - DuckDB への冪等書き込み（部分失敗時に既存データ保護する DELETE → INSERT の戦略）
  - 市場レジーム判定: regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離とマクロニュースの LLM センチメントを重み付け合成して日次レジーム判定（bull/neutral/bear）
    - マクロキーワードによる記事抽出、LLM 呼び出し、スコア合成、冪等な DB 書き込み
    - API キー注入（引数または環境変数）対応
  - AI モジュール共通の設計方針:
    - datetime.today()/date.today() を直接参照しない（ルックアヘッドバイアス対策）
    - テスト容易性のため _call_openai_api を差し替え可能（unittest.mock でパッチ可能）
    - API 失敗時はフォールバック値（例えば macro_sentiment=0.0）で継続するフェイルセーフ設計
- Data モジュール（src/kabusys/data）
  - マーケットカレンダー管理: calendar_management
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定ユーティリティを実装
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に更新するジョブ実装（バックフィル / 健全性チェック含む）
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック
  - ETL パイプライン: pipeline, etl
    - ETLResult データクラス（取得数 / 保存数 / 品質問題 / エラー情報を保持）を実装
    - 差分更新・バックフィル・品質チェックを考慮した ETL 設計（jquants_client 経由での保存）
    - DuckDB 互換性考慮（executemany に空リストを渡さない等）
  - ユーティリティ: _table_exists / _to_date 等の汎用ヘルパ実装
- Research モジュール（src/kabusys/research）
  - ファクター計算: factor_research.calc_momentum / calc_volatility / calc_value
    - Momentum (1M/3M/6M)、200日MA乖離、ATR、平均売買代金等を DuckDB SQL で計算
  - 特徴量探索: feature_exploration.calc_forward_returns / calc_ic / rank / factor_summary
    - 将来リターン計算（horizons パラメタ検証）、Spearman 相関（ランク相関）による IC、統計サマリー等
  - research/__init__.py で主要関数をエクスポート（zscore_normalize は data.stats から提供）
- ロギング・診断
  - 各処理に logger.debug/info/warning/exception を配置して実行時のトレースを容易に

Changed
-------
- （初版のため該当なし）

Fixed
-----
- JSON パースの堅牢化
  - news_nlp/regime_detector の LLM レスポンスパースで JSONDecodeError が発生した場合、最外の {} を抽出して復元を試みる処理を追加（部分的な余計なテキスト混入への耐性）
- API 呼び出しの回復力向上
  - OpenAI 呼び出しで RateLimit / 接続断 / タイムアウト / 5xx を判定してリトライする実装を追加（エクスポネンシャルバックオフ）
  - server-side の 5xx とそれ以外のエラーを区別してリトライ可否を制御
- データ不足時の安全なフォールバック
  - MA200 計算でデータが不足する場合は中立値（1.0）を返す、関連関数で警告ログ出力
  - news_nlp/score_news や regime_detector で LLM 呼び出しが失敗した場合は例外を投げずフォールバックスコアで継続
- DuckDB 互換性対策
  - executemany に空リストを渡さないチェック（DuckDB 0.10 の制約回避）
  - 日付値変換ユーティリティ（_to_date）を追加して DuckDB の日付型互換性を確保

Deprecated
----------
- （初版のため該当なし）

Security
--------
- 環境変数読み込みで OS の環境変数を保護する protected キー機構を導入（.env の上書きから保護）
- API キーは関数引数で注入可能にし、テスト時に安全に差し替えできる設計

Notes / Known limitations
-------------------------
- OpenAI API は gpt-4o-mini を想定している（モデル変更は定数で管理）。商用運用前にレイテンシ・コスト評価が必要。
- 本リリースは「分析・研究・データ基盤」部分が中心であり、実際の発注・実行（execution）ロジックは別モジュール（公開済み名あり）に委ねられている想定。
- news_nlp/regime_detector は LLM の出力に依存するため、運用時はレスポンスの品質監視とレート/課金管理が必要。
- calendar_update_job / pipeline の外部 API 呼び出し（J-Quants 等）は例外を捕捉して 0 を返すフェイルセーフだが、失敗原因の検知・再試行ポリシーは呼び出し元で制御することを推奨。

Contributors
------------
- 初版: 開発者（コードベースから推測して作成）