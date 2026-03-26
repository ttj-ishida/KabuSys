# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

全てのリリースはセマンティックバージョニングに準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-26
初回リリース。日本株自動売買システムのコアライブラリを実装しました。以下の主要機能・モジュールを追加しています。

### Added
- パッケージの基礎
  - パッケージ初期化: kabusys.__init__（バージョン "0.1.0"、主要サブパッケージを公開: data, strategy, execution, monitoring）
- 設定・環境変数管理
  - kabusys.config
    - .env ファイル（.env, .env.local）と OS 環境変数を組み合わせた自動ロード機能を実装
    - KABUSYS_DISABLE_AUTO_ENV_LOAD フラグで自動ロードを無効化可能
    - .env パースの堅牢化（コメント、export 形式、クォート内エスケープ、インラインコメント判定などに対応）
    - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得（J-Quants / kabu station / Slack / DB パス / 環境モード / ログレベル等）
    - 必須設定取得時に未設定で ValueError を送出する _require 実装
    - 環境値の妥当性チェック（KABUSYS_ENV / LOG_LEVEL の有効値検証）

- AI（LLM）関連
  - kabusys.ai パッケージ公開 API: score_news
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いて銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを取得して ai_scores テーブルへ書き込み
    - ニュース収集ウィンドウ計算（JST ベース → UTC naive datetime を返す calc_news_window）
    - バッチ処理（1コールあたり最大 _BATCH_SIZE=20 銘柄）と文字数制限（最大 _MAX_CHARS_PER_STOCK）
    - 再試行ロジック（429, ネットワーク断, タイムアウト, 5xx に対して指数バックオフでリトライ）
    - レスポンス検証（JSON 抽出、results 配列、code/score の型検証、スコアの ±1.0 でクリップ）
    - テスト容易性のため _call_openai_api を patch 可能に実装
    - フェイルセーフ: API 失敗時は該当チャンクをスキップして他銘柄は継続

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定
    - ma200_ratio 計算（ルックアヘッド排除: target_date 未満のデータのみ使用）
    - マクロキーワードで raw_news をフィルタして LLM に渡し macro_sentiment を評価（_MACRO_KEYWORDS によるフィルタ）
    - OpenAI 呼び出しのリトライ／フェイルセーフ（API 失敗時は macro_sentiment=0.0 として続行）
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装
    - テスト容易性のため _call_openai_api を差し替え可能に実装

- Data / ETL
  - kabusys.data パッケージ
    - calendar_management
      - JPX カレンダー管理（market_calendar テーブルの参照・更新ロジック）
      - 営業日判定 API: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
      - DB にカレンダーがない場合は曜日ベースのフォールバック（週末=非営業日）
      - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に更新するジョブ実装（バックフィル・健全性チェックを含む）
    - etl: ETLResult を再エクスポート
    - pipeline
      - ETLResult dataclass（target_date, fetched/saved 件数, quality_issues, errors 等）
      - 差分取得・バックフィル・品質チェックを想定した ETL 基盤のユーティリティ（テーブル存在チェック、最大日付取得など）

- Research（解析）機能
  - kabusys.research パッケージ
    - factor_research
      - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を計算
      - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算
      - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を計算（最新財務レコードを参照）
      - 設計として DuckDB 上の SQL を中心に実装し、外部 API への依存なし
    - feature_exploration
      - calc_forward_returns: 任意ホライズンに対する将来リターンを一括取得（horizons のバリデーションあり）
      - calc_ic: スピアマン順位相関（Information Coefficient）を計算
      - rank: 同順位（ties）を平均ランクにするランク関数（丸め処理で tie 検出の安定化）
      - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算
    - 解析ユーティリティ（zscore_normalize は kabusys.data.stats から再利用）

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を投げることで明示的に失敗させる設計。

### その他の設計上の注記（ドキュメント的に重要）
- ルックアヘッドバイアス対策: ニューススコアリング・レジーム判定・ファクター計算等の各モジュールは内部で datetime.today()/date.today() に依存せず、外部から与えられる target_date を基準に処理を行うよう設計されています。
- DB 書き込みは可能な限り冪等性を担保（DELETE→INSERT など）し、部分失敗時に既存データを不必要に上書きしない方針です。
- LLM 呼び出しは JSON Mode を利用し、結果を厳密にパース・検証することで不正な出力への耐性を高めています。  
- テスト容易性: OpenAI 呼び出し部分（_call_openai_api）はモジュール内で分離されており、ユニットテストでの patch による置換が想定されています。
- DuckDB 互換性配慮: executemany に空リストを渡さない等の互換性処理を含む。

Contributors: 初期実装

（注）本 CHANGELOG はソースコードのドキュメンテーション文字列・定数・関数名等から推測して作成しています。実際のリリースノートに合わせて追記・修正してください。