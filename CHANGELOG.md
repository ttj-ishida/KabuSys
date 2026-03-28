# Changelog

すべての注記は Keep a Changelog の方針に従い、重要な変更点・追加機能・修正点を記録します。  
このファイルはコードベースから推測して作成した初期リリースの変更履歴です。

全般的な注意:
- 本プロジェクトは日本株の自動売買／リサーチ／データ基盤を意図したライブラリ群です（kabusys パッケージ）。
- 内部的に DuckDB をデータストアとして利用し、外部 API（J-Quants、OpenAI、kabuステーション 等）に依存する機能を含みます。
- LLM 呼び出しは gpt-4o-mini を想定した JSON モードで行い、冗長なテキストを安全に扱うためのバリデーション・フェイルセーフ処理を実装しています。

## [Unreleased]

- （今後の変更をここに記録）

## [0.1.0] - 2026-03-28

Added
- 基本パッケージ初期実装
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
  - モジュール公開: data, strategy, execution, monitoring を __all__ で公開

- 環境設定管理（kabusys.config）
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ローダを実装
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化に対応
    - プロジェクトルートの検出は __file__ の親ディレクトリから .git または pyproject.toml を探索（CWD に依存しない）
  - .env パーサ実装（export 形式、クォート・エスケープ、インラインコメントの取り扱い対応）
  - Settings クラスを提供（settings インスタンス経由で取得）
    - 必須環境変数のチェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）
    - デフォルト値・検証（KABUSYS_ENV の有効値チェック、LOG_LEVEL の検証、パスの展開等）
    - is_live / is_paper / is_dev 等のユーティリティプロパティ

- AI（ニュース NLP / レジーム判定）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - raw_news と news_symbols を集約し、銘柄毎に gpt-4o-mini へバッチ送信してセンチメント（ai_score）を計算・ai_scores テーブルへ冪等書き込み
    - バッチ処理・トリム（記事数上限・文字数上限）・最大バッチサイズ制限を実装
    - JSON レスポンスのバリデーション、未知コードや数値パースエラーは無害にスキップ
    - リトライ（429・ネットワーク・タイムアウト・5xx）を指数バックオフで実施
    - API 未設定時は ValueError を送出
    - 返り値は書き込んだ銘柄数
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と macro センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定
    - マクロニュースは news_nlp.calc_news_window を用いてフィルタ（キーワードリスト）し、LLM で macro_sentiment を取得
    - LLM 呼び出し失敗時は macro_sentiment = 0.0 とするフェイルセーフ
    - レジームスコアとラベルを market_regime テーブルへトランザクションで冪等書き込み
    - API 未設定時は ValueError を送出

  - LLM 呼び出し設計
    - gpt-4o-mini を JSON レスポンスモードで利用
    - JSON パース失敗や余計な前後テキストを含む場合に最外の {} を抽出して復元するロバスト処理
    - テスト容易性のため _call_openai_api を内部で分離（ユニットテストでモック可能）

- Data（データ基盤）
  - calendar_management
    - market_calendar を用いた営業日判定ロジックを提供
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB 登録が無い場合は曜日ベース（土日）でフォールバックする一貫した挙動
    - 最大探索日数による安全対策（_MAX_SEARCH_DAYS）
    - night batch job: calendar_update_job(conn, lookahead_days) により J-Quants API から差分で取得し冪等保存（バックフィル・健全性チェックを含む）
  - ETL pipeline（data.pipeline）
    - ETLResult データクラスを公開（ETL 実行結果の集約、品質問題・エラーの集計）
    - 差分取得・保存・品質チェックを行うための設計（バックフィル日数・最小データ日・品質チェック重み付けを含む）
    - _get_max_date, _table_exists などの内部ユーティリティ実装

- Research（研究用ユーティリティ）
  - factor_research
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、ma200_dev（200日MA乖離）を計算
    - calc_volatility(conn, target_date): 20日 ATR、相対ATR、平均売買代金、出来高比率を計算
    - calc_value(conn, target_date): latest 財務データと価格を組合せて PER / ROE を計算
    - DuckDB のウィンドウ関数を活用した SQL ベース実装、データ不足時の None 扱い、ログ出力
  - feature_exploration
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターンをまとめて取得（複数ホライズン対応、入力検証）
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を実装（最低サンプル数のガードあり）
    - rank(values): 同順位は平均ランクで扱うランク関数（丸めによる ties 対応）
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリ

- その他
  - data.etl は pipeline.ETLResult を再エクスポート
  - research パッケージから主な関数を __all__ で再公開（テストや利用時の import 簡略化）
  - DuckDB 互換性考慮（executemany の空リスト回避等）

Changed
- （初回リリースのため特定の「変更」履歴はなし。設計決定やフォールバック動作はドキュメントとして明記）

Fixed
- （初回リリースのため特定の「修正」履歴はなし）

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーや各種シークレットは Settings で必須チェックを行う。環境変数管理 (.env) は自動で読み込まれるが、KABUSYS_DISABLE_AUTO_ENV_LOAD による上書きを許容。

Notes / 設計上の重要点（開発者向け要約）
- ルックアヘッドバイアス対策: 日付ロジックは datetime.today() / date.today() を内部で参照せず、必ず target_date を引数で受け取る実装（AI スコア・レジーム判定・ETL 等）。
- LLM 呼び出しは堅牢化: JSON パースの復元処理、冪等性確保、リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフを導入。API 失敗時は例外を投げずにフォールバックする箇所が多く、運用時のフェイルセーフを重視。
- DB 書き込みはトランザクション内で DELETE→INSERT を行い、部分失敗時の既存データ保護を考慮。
- DuckDB のバージョン差異（executemany の空リスト制約等）を考慮した実装上の工夫あり。

開発・運用に関する推奨事項
- 必要な環境変数（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を .env（.env.local）で管理し、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード制御を理解すること。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）が初期化済みであることを確認すること。
- LLM 呼び出し部分はユニットテストのために _call_openai_api をモックできるよう設計されているので、CI では外部 API をモックしてテストを行うこと。

---

（この CHANGELOG はコード内容から推測して作成したものであり、実際のコミット履歴や変更履歴と異なる場合があります。リリース時には実際のコミットログや変更差分に基づき適宜更新してください。）