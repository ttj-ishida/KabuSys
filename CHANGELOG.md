# Changelog

すべての重要な変更は Keep a Changelog の構成に従って記載します。  
このファイルはプロジェクトの機能追加・修正・設計方針などを追跡する目的で作成されています。

注意: 本 CHANGELOG は提供されたコードベースから推測して作成しています。

## [0.1.0] - 2026-03-28

初回公開リリース。日本株のデータ取得・前処理・リサーチ・AIベースのニュースセンチメント評価・市場レジーム判定・カレンダー管理などを行う自動売買支援ライブラリの基本機能を実装。

### Added
- パッケージ初期化
  - kabusys パッケージを公開。__version__ = "0.1.0"、主要サブパッケージ（data, strategy, execution, monitoring）を __all__ に定義。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート判定: .git または pyproject.toml を起点にルートを自動検出（カレントワーキングディレクトリに依存しない）。
  - 高度な .env パーサを実装:
    - export KEY=val 形式対応、シングル／ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い（クォート有無による挙動差分）などに対応。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による無効化（テスト用フック）。
  - 上書き保護: OS 環境変数を protected として .env の上書きを制御。
  - Settings クラスを提供し、必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）をプロパティとして取得。KABUSYS_ENV / LOG_LEVEL の値検証やデフォルト値（kabu API base URL, DB パスなど）を提供。

- AI モジュール
  - kabusys.ai.news_nlp
    - raw_news / news_symbols を元にニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む処理を実装。
    - 時間ウィンドウ: target_date の前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して DB と比較）を採用。
    - バッチ処理: 最大 20 銘柄単位で API 送信、1 銘柄あたりの最大記事数・文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）でプロンプト肥大化を抑制。
    - 再試行戦略: 429（Rate Limit）・ネットワーク断・タイムアウト・5xx に対して指数バックオフリトライを実装。その他のエラーはスキップして継続（フェイルセーフ）。
    - レスポンス検証: JSON パース、results 配列・要素構造・スコア数値性を確認、不正応答は無視。必要に応じて最外の {} を抽出して復元する工夫あり。
    - DB 書き込みは冪等化（DELETE → INSERT）し、部分失敗時に既存データを保護する（書き込み対象コードのみ削除して挿入）。
    - テスト容易性: _call_openai_api をパッチ差し替え可能にしてユニットテスト対応。

  - kabusys.ai.regime_detector
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、news_nlp によるマクロセンチメント（重み 30%）を組み合わせて日次の市場レジーム（bull / neutral / bear）を算出。
    - マクロニュース抽出はキーワードリスト（日本・米国の主要キーワード）でフィルタ。最大記事数制限あり。
    - OpenAI 呼び出しは JSON モードで実施、失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - レジームスコア合成後、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時はロールバックして例外を伝播。
    - API 呼び出しの再試行・エラー分類（5xx とそれ以外）を実装。テスト用に _call_openai_api を差し替え可能。

- リサーチ機能 (kabusys.research)
  - calc_momentum, calc_value, calc_volatility を提供（kabusys.research.factor_research）。
    - Momentum: mom_1m / mom_3m / mom_6m, ma200_dev（200日移動平均乖離）を SQL で計算。データ不足時は None。
    - Volatility / Liquidity: 20日 ATR（ATR の計算ロジック）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率などを計算。トゥルーレンジの NULL 伝播制御を実装。
    - Value: raw_financials から直近レポートを取得して PER / ROE を計算（EPS が 0/欠損の場合は None）。PBR / 配当利回りは未実装。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンをまとめて取得する SQL 実装。ホライズンパラメータの検証あり。
    - calc_ic: Spearman ランク相関（Information Coefficient）を実装。None 値除外・有効レコード数チェック（>=3）。
    - rank / factor_summary: ランク変換（同順位は平均ランク）・統計サマリー（count/mean/std/min/max/median）を提供。
  - zscore_normalize を kabusys.data.stats から再公開（kabusys.research.__init__）。

- データプラットフォーム (kabusys.data)
  - calendar_management
    - market_calendar テーブルを利用した営業日判定ユーティリティを実装。
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - DB にカレンダー情報がない場合は曜日ベースのフォールバック（土日を非営業日とする）。
    - next/prev_trading_day では DB 登録値を優先し、未登録日は曜日フォールバックで一貫性を保つ。探索上限を _MAX_SEARCH_DAYS で制限して無限ループを防止。
    - calendar_update_job: J-Quants API（jquants_client 経由）から差分取得して market_calendar を冪等に更新。バックフィル（日数設定）と健全性チェック（未来日付の異常検知）を実装。
  - ETL / pipeline
    - ETLResult データクラスを公開（kabusys.data.pipeline.ETLResult を kabusys.data.etl で再エクスポート）。
    - ETL の設計方針を実装（差分更新、backfill、品質チェックとの連携、id_token 注入など）。
    - DuckDB を前提としたテーブル存在チェック、max date 取得ユーティリティ等を実装。

- テスト・運用性
  - OpenAI 呼び出し箇所はテスト時に関数を差し替え可能（unittest.mock.patch で _call_openai_api を置換）としてユニットテスト容易化を配慮。
  - ロギング（logger）を各モジュールに導入し、失敗時のフォールバックや詳細ログを出力。

### Changed
- 初回リリースのため該当なし（新規実装中心）。

### Fixed
- 初回リリースのため該当なし。

### Security
- 機密情報の扱いに配慮:
  - 環境変数読み込み時に OS 環境変数の上書きを保護する仕組みを実装。
  - 必須トークン（OpenAI API、Slack、kabu API、J-Quants リフレッシュトークン等）を Settings で明示的に取得し、未設定時は ValueError を発生させることで明確にエラー検出。

### Notes / Known limitations
- OpenAI との統合は gpt-4o-mini を想定した JSON Mode を利用しているが、実運用では API 仕様／コスト面の検証が必要。
- ai_scores / market_regime などへの DB 書き込みは DuckDB を前提に実装しており、DuckDB のバージョン差異（executemany の空リスト扱いなど）に注意した実装上の配慮がある。
- 一部のファクター（PBR、配当利回り）は未実装。
- calendar_update_job / ETL は jquants_client（kabusys.data.jquants_client）への依存があるため、API キーやクライアント実装の差し替えが必要。
- datetime.now()/date.today() の直接参照を避ける設計（ルックアヘッドバイアス防止）だが、外部から与える target_date の取り扱いに注意。

もし追加でリリース履歴の細分化（プレリリース、パッチ、マイナー追加機能等）や、各モジュールごとの変更差分（コミット単位）を想定した詳細化が必要であれば、該当箇所のコミットメッセージや機能要求に基づいて更新案を作成します。