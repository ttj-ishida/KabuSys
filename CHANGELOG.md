# CHANGELOG

すべての注目すべき変更点をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

バージョンやリリースの粒度はコードベースから推測して作成しています。  
初期リリースとして v0.1.0 を作成しています（リリース日: 2026-04-04）。

## [Unreleased]

## [0.1.0] - 2026-04-04

初期リリース。本リリースでは日本株自動売買プラットフォーム「KabuSys」のコア機能群を実装しました。主要なコンポーネントは設定管理、データ ETL / カレンダ管理、調査（research）ユーティリティ、AI を用いたニュース NLP / 市場レジーム判定、および各種ファクター計算です。主な追加点は以下の通りです。

### Added
- パッケージメタ情報
  - `kabusys.__version__ = "0.1.0"` を定義。

- 環境変数 / 設定管理（src/kabusys/config.py）
  - `.env` ファイルまたは環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルート判定は `.git` または `pyproject.toml` を探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - `.env` パーサを実装（コメント行、export プレフィックス、クォート文字列のエスケープ処理、インラインコメントの扱いなどに対応）。
  - 既存 OS 環境変数を保護するための protected キー概念を採用（.env 読み込み時に上書きガード）。
  - 必須設定取得ユーティリティ `_require` と、アプリ設定ラッパ `Settings` を提供。
  - `Settings` で各種プロパティを用意（J-Quants トークン、kabu API 設定、LINE トークン、データベースパス、監視設定、閾値、環境・ログレベル判定ユーティリティ等）。
  - デフォルト値や検証ロジックを実装（例: `KABUSYS_ENV` の許容値検査、`LOG_LEVEL` 検査、パスの expanduser 処理 等）。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析機能を実装。
    - 対象時間ウィンドウ（JST 前日15:00 ～ 当日08:30）を UTC へ変換するロジック（calc_news_window）。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約（記事数と文字数の上限設定有り）。
    - バッチ送信（最大 20 銘柄/リクエスト）、JSON Mode を期待したレスポンス処理。
    - 429、ネットワーク断、タイムアウト、5xx に対する指数バックオフのリトライ実装。
    - レスポンスのバリデーション処理（JSON 抽出、results リスト、code の正規化、score の数値検査、±1.0 のクリップ）。
    - DuckDB の互換性対策（executemany に空リストを渡さないガード）。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（_call_openai_api を patch できる設計）。
    - 公開 API: `score_news(conn, target_date, api_key=None)`（成功時は書き込んだ銘柄数を返す。api_key 未指定時は環境変数 `OPENAI_API_KEY` を参照し未設定だと例外）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - マクロキーワードによる raw_news フィルタリングと OpenAI によるセンチメント評価（gpt-4o-mini、JSON モード）。
    - API エラーに対するリトライ実装（429 等と 5xx の扱い差分）とフェイルセーフ（API 失敗時は macro_sentiment = 0.0 を使用）。
    - ルックアヘッドバイアス回避の設計（target_date 未満のデータのみ参照し、datetime.today() を直接参照しない）。
    - 市場レジーム結果を `market_regime` テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 公開 API: `score_regime(conn, target_date, api_key=None)`（成功時 1 を返す。api_key 未設定は例外）。

- データプラットフォーム（src/kabusys/data）
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - 差分更新・保存・品質チェックワークフローを想定した ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラー等を格納）。
    - ETL 処理方針とパラメータ（最小データ開始日、カレンダー先読み、バックフィル日数等）を定義。
    - DuckDB テーブル存在確認ユーティリティ、最大日付取得等の補助関数を実装（ETL 実装の基礎を提供）。
    - 外部 jquants_client, quality モジュールと連携する設計を備える。
    - パブリック再エクスポート: `kabusys.data.ETLResult`。

  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー（market_calendar）を管理するユーティリティを実装。
    - 営業日判定 / 翌営業日 / 前営業日 / 期間内営業日リスト / SQ 日判定を提供。
    - DB にカレンダーがある場合は DB 値を優先、未登録日は曜日（平日）ベースでフォールバックする一貫設計。
    - 夜間バッチ job（calendar_update_job）を実装：J-Quants から差分取得し冪等的に保存。バックフィルと健全性チェックを実装。
    - 探索上限（最大探索日数）やバックフィル日数等の安全ガードを実装。

- リサーチ / ファクター群（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum: 1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）を計算（データ不足時は None）。
    - Volatility / Liquidity: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等を計算（欠測行は None）。
    - Value: raw_financials から最新財務を取得し PER / ROE を計算（EPS が 0/欠損の場合は None）。
    - SQL を多用した DuckDB ベースの実装で、外部 API 呼び出しを行わない設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン取得ユーティリティ（calc_forward_returns）を実装（horizons 検証・1 クエリで複数ホライズン取得）。
    - IC（Information Coefficient）計算（スピアマンのランク相関）を実装（欠損フィルタ、最小サンプルチェック）。
    - ランク変換ユーティリティ（同順位は平均ランク、丸め処理で ties を扱う）。
    - ファクター統計サマリー（count/mean/std/min/max/median）を実装。
  - 研究向けユーティリティ群をパッケージングしてエクスポート（zscore_normalize は data.stats から再利用）。

- ロギング / フェイルセーフ設計
  - 各所で詳細な logger 出力を実装。API 失敗時は大半が例外を上位に伝播させずフェイルセーフにフォールバックする（ただし DB 書き込み失敗等致命的なケースは例外を投げる）。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Deprecated
- 初期リリースのため該当なし。

### Removed
- 初期リリースのため該当なし。

### Security
- 初期リリースのため該当なし。

---

Notes / 注意事項
- OpenAI の API キーは `OPENAI_API_KEY` か各 API 呼び出しの引数で与える必要があります。未設定時は `ValueError` を送出する設計の箇所があります（score_news / score_regime）。
- ニュース窓や時刻は UTC naive datetime で扱われ、JST 基準のウィンドウを UTC へ変換して DB と照合します。タイムゾーンの混入に注意してください。
- DuckDB のバージョン互換性に配慮した実装（executemany の空リスト回避等）を行っていますが、実行環境の DuckDB バージョンによっては調整が必要になる場合があります。
- 本リリースは主にデータ処理・研究・判定ロジックを提供します。実際の発注（execution）や運用監視（monitoring）関連のモジュールはパッケージ公開インターフェースに示唆がありますが、ここに含まれるコードは主にデータ処理・研究・AI 判定部分です。

もし CHANGELOG に追加してほしい形式上の詳細（セクション分けや日付、ISSUE/PR 番号の紐付け等）があれば教えてください。