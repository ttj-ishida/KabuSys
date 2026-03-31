# CHANGELOG

すべての重要な変更をこのファイルで管理します。フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。  

現在のリリース:
- [0.1.0] - 2026-03-31

## [0.1.0] - 2026-03-31
初回公開リリース。本パッケージは日本株の自動売買・データ基盤・研究用ユーティリティ群を提供します。主に DuckDB を用いたデータ操作、J-Quants / kabu ステーション など外部 API との連携、OpenAI（gpt-4o-mini）を利用したニュース NLP を中心機能としています。

### 追加（Added）
- パッケージ構成
  - kabusys パッケージ初期構成を追加。公開モジュール: data, strategy, execution, monitoring（__all__に定義）。
  - バージョン: 0.1.0 を設定。

- 設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする仕組みを実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロード無効化が可能。
  - export 形式やクォート、コメントなどを考慮した .env パーサー実装（保護キー機能、上書きオプション）。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス / 監視閾値 / 環境（development/paper_trading/live） / ログレベル等をプロパティ経由で取得可能。
  - 必須環境変数未設定時に ValueError を送出する _require ユーティリティを実装。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約し、銘柄毎にニュースをまとめて OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
  - API リトライ（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実装（デフォルト最大再試行回数）。
  - レスポンス検証（JSON 抽出、構造チェック、スコア数値検証、コード照合）を行い、スコアを ±1 にクリップ。
  - ai_scores テーブルへ冪等的に（DELETE → INSERT）上書き保存。部分失敗時に他コードの既存スコアを保護する設計。
  - calc_news_window: JST ベースのニュース集計ウィンドウ計算ユーティリティを提供。
  - score_news API: DuckDB 接続と target_date を受け取り、書き込み件数を返す。api_key を引数注入可能（テスト容易性）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
  - DuckDB からの価格/ニュース取得、OpenAI 呼び出し（api_key 注入可）、リトライ・フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
  - 計算結果を market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で保存。
  - ルックアヘッドバイアス回避のため date 引数ベース設計（datetime.today() を参照しない）。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M のリターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組合せて PER、ROE を算出（欠損時は None）。
    - 全て DuckDB を用いた SQL ベース実装で、外部 API への影響なし。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（日数）に対する将来リターンを計算。horizons のバリデーション（正の整数かつ <=252）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコード 3 件未満で None）。
    - rank / factor_summary: ランキング（同順位平均ランク）と基本統計量算出ユーティリティを提供。
  - すべて標準ライブラリ + DuckDB で実装（pandas 等に非依存）。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar を用いた営業日判定・次営業日/前営業日/期間内営業日取得/is_sq_day 等のユーティリティを実装。
    - DB 登録がない場合は曜日ベースのフォールバック（土日を非営業日扱い）。
    - calendar_update_job: J-Quants クライアント（jquants_client）から差分取得して market_calendar を更新する夜間バッチジョブ（バックフィルと健全性チェックあり）。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL の取得数・保存数・品質問題・エラーなどを集約）。
    - ETL 実行方針（差分更新、バックフィル、品質チェック、id_token 注入）をコード化（pipeline モジュールの骨子を提供）。
    - jquants_client と quality モジュールを用いた差分取得・保存・品質検査のための基盤を用意。

- 外部連携・設計上のポイント
  - DuckDB を主要なローカル DB として利用する想定（接続オブジェクトを関数引数で注入）。
  - OpenAI（gpt-4o-mini）をニュース解析用に利用。API キーは引数注入または環境変数 OPENAI_API_KEY を参照。
  - J-Quants（市場データ）や kabu API（発注系）、Slack（通知用）の設定項目を Settings で管理。
  - ルックアヘッドバイアス対策: 公開 API は日付引数ベースで動作し、date.today()/datetime.today() を内部で参照しない設計。
  - テストしやすさ: OpenAI 呼び出しや内部関数を patch / モック可能に設計（例: _call_openai_api の差し替え）。

### 変更（Changed）
- 初回リリースのため該当なし。

### 修正（Fixed）
- 初回リリースのため該当なし。

### 非推奨（Deprecated）
- 初回リリースのため該当なし。

### 削除（Removed）
- 初回リリースのため該当なし。

### セキュリティ（Security）
- 初回リリースのため該当なし。ただし API キーやトークンは環境変数で管理する想定。

## 注意事項 / 互換性
- DuckDB のバージョン差異により executemany に空リストを渡せない制約を考慮した実装が含まれます（空パラメータ時は実行スキップ）。
- OpenAI SDK の API エラー型や status_code の有無に互換性を持たせたエラーハンドリングを実装していますが、将来の SDK 変更がある場合は追加対応が必要となる可能性があります。
- .env の自動ロードはプロジェクトルート検出に依存します。配布後やパッケージ化環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って制御してください。
- 本リリースは「データ取得・解析・研究」側の機能を中心に実装しており、発注ロジック（strategy / execution / monitoring の具体実装）は別途実装／公開される想定です。

---

今後の変更や個別の利用方法（関数シグネチャ、テーブルスキーマ等）については、各モジュールのドキュメント／コードコメントを参照してください。