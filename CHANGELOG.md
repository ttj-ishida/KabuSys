CHANGELOG
=========

すべての変更は Keep a Changelog の慣習に従って記載しています。  
フォーマット: https://keepachangelog.com/（日本語訳に準拠）

このリポジトリの初回リリースに相当する変更履歴を、ソースコードから推測して作成しています。

[Unreleased]
-------------

（なし）

[0.1.0] - 2026-03-28
-------------------

初回リリース。日本株自動売買プラットフォームのコア機能群を実装しました。主な追加内容は以下の通りです。

Added
- パッケージの基本情報
  - kabusys パッケージ（__version__ = "0.1.0"）。
  - パッケージ公開API: data, strategy, execution, monitoring を __all__ に設定。

- 環境設定管理（kabusys.config）
  - .env ファイルと環境変数からの設定自動読み込み機能を実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD に依存しない）。
    - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は override=True）。
    - .env 解析は export KEY=val やクォート、エスケープ、インラインコメント等に対応。
  - Settings クラスでアプリ設定をプロパティとして公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須化（未設定時は ValueError）。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/...）の検証。
    - データベースパスのデフォルト: duckdb -> data/kabusys.duckdb, sqlite -> data/monitoring.db。
    - is_live / is_paper / is_dev ヘルパー。

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news + news_symbols を入力に OpenAI（gpt-4o-mini, JSON mode）で銘柄ごとのセンチメント評価を実行する score_news を実装。
  - 処理の特徴:
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で算出（内部は UTC naive datetime）。
    - 1銘柄あたり最大記事数・文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）でトリム。
    - API 呼び出しはチャンク単位（最大 _BATCH_SIZE = 20 銘柄）で実行。
    - RateLimit/ネットワーク/タイムアウト/5xx に対して指数バックオフでリトライ。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code と score の検証）。
    - スコアは ±1.0 にクリップ。
    - 書き込みは冪等性を意識（対象コードだけ DELETE → INSERT）し、部分失敗時に既存データを保護。
    - DuckDB の executemany に関する互換性考慮（空リストの処理回避）。
  - エラー時の挙動:
    - API/パース失敗時は該当チャンクをスキップして継続（フェイルセーフ）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）と、ニュース由来の LLM センチメント（重み 30%）を合成して日次で市場レジームを判定する score_regime を実装。
  - 処理の特徴:
    - ma200_ratio の計算は target_date 未満のデータのみを使いルックアヘッドを防止。
    - マクロキーワードによる raw_news タイトル抽出（最大 _MAX_MACRO_ARTICLES 件）。
    - OpenAI（gpt-4o-mini）呼び出しは JSON モードで行い、429/ネットワーク/タイムアウト/5xx に対してリトライ実装。
    - API 失敗時の安全措置として macro_sentiment=0.0 を使う（例外を上げず進行）。
    - 最終的な regime_score の閾値により "bull"/"neutral"/"bear" を判定。
    - market_regime テーブルへの書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等操作。書込み失敗時は ROLLBACK を試みて上位へ例外を伝播。
  - 設計上、datetime.today()/date.today() を内部で参照せず、呼び出し側が target_date を供給することでルックアヘッドバイアスを排除。

- データ ETL・パイプライン（kabusys.data.pipeline, etl）
  - ETLResult データクラスを実装し、ETL 実行結果（取得数・保存数・品質問題・エラー）を構造化して返却可能に。
  - 差分更新、バックフィル、品質チェック等の処理フロー設計を実装。
  - 内部ユーティリティ:
    - DuckDB 上のテーブル存在確認、最大日付取得など。

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - JPX カレンダー取得・保持と営業日判定ユーティリティを実装。
  - 提供 API:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - calendar_update_job: J-Quants API から差分取得して market_calendar を更新（バックフィル、健全性チェックあり）。
  - 特徴:
    - market_calendar 未取得時は曜日ベースでフォールバック（土日非営業）。
    - DB 登録がある場合は DB 値優先。未登録日は曜日フォールバックで一貫性を保つ。
    - 探索上限（_MAX_SEARCH_DAYS）を設け無限ループ防止。
    - ON CONFLICT DO UPDATE 相当の冪等保存を想定した実装と J-Quants クライアント呼び出しの例外ハンドリング。

- 研究（research）モジュール（kabusys.research）
  - ファクター計算と特徴量探索機能を実装・公開:
    - calc_momentum, calc_value, calc_volatility（ファクター計算）
    - calc_forward_returns, calc_ic, factor_summary, rank（特徴量探索・統計）
    - zscore_normalize は data.stats から再エクスポート
  - 各関数の設計ポイント:
    - DuckDB 接続を受け取り prices_daily / raw_financials 等の DB テーブルのみ参照（外部 API にアクセスしない）。
    - モメンタム: 1M/3M/6M リターン、MA200 乖離（データ不足時は None）。
    - ボラティリティ: ATR 20 日、ATR 比率、平均売買代金、出来高比率（ウィンドウ不足時は None）。
    - バリュー: EPS/ROE を用いた PER/ROE（最新財務レコードを target_date 以前から取得）。
    - 将来リターン計算は複数ホライズンに対応し、一度の SQL でまとめて取得。
    - Spearman（ランク）ベースの IC を実装（rank 関数は同順位を平均ランクで処理）。
    - 統計サマリー（count, mean, std, min, max, median）を算出。

- 内部実装上の品質対応
  - DuckDB の取り扱いに関する互換性配慮（executemany の空リスト回避、日付の型変換ユーティリティ等）。
  - API 呼び出し部分（OpenAI や J-Quants）では例外発生時にログを出し、可能な限りフェイルセーフで継続する設計。
  - 詳細なログ出力（debug/info/warning/exception）を各処理に追加。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 環境変数の扱いに注意:
  - 必須トークン（OpenAI や各 API トークン）は Settings 経由で取得し、未設定時は ValueError を送出することで起動ミスを防止。
  - .env の自動ロードはプロジェクトルート検出に基づき、誤ったカレントディレクトリに依存しない実装。

Notes / Developer hints
- OpenAI を利用する機能（score_news, score_regime）は api_key 引数でキー注入可能。テスト時は api_key を直接渡すか環境変数 OPENAI_API_KEY を設定してください。
- テストの容易性のため、OpenAI 呼び出しはモジュール内で _call_openai_api をラップしているため、unittest.mock.patch による差し替えが想定されています（kabusys.ai.news_nlp._call_openai_api / kabusys.ai.regime_detector._call_openai_api）。
- ルックアヘッドバイアス対策として、日付参照はすべて呼び出し側で target_date を指定する設計です。内部で date.today() や datetime.today() を使わない方針に従っています。
- DuckDB に関する注意:
  - executemany に空リストを渡すとエラーになるバージョンがあるため、実装内で空チェックを行っています。
  - 日付型は関数内で安全に date オブジェクトへ変換します。

既知の制約 / 留意点
- OpenAI のレスポンスに依存するため、モデル仕様や SDK のバージョン差による挙動変化に注意（status_code の有無などに対する耐性を一部実装済み）。
- 一部処理（ニュース集約やファクター計算）は DuckDB 内のデータ品質に依存するため、事前にデータの品質チェックを行うことが推奨されます（ETL の quality チェック機能参照）。
- 本リリースは初期実装であり、将来的に API 形状やエラー処理、ログの細分化などが変更される可能性があります。

ライセンス、貢献方法、その他メタ情報はリポジトリの README / CONTRIBUTING を参照してください。