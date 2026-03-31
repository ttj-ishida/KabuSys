# Changelog

すべての注目すべき変更点を記録します。フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

なお、本CHANGELOGはソースコードの内容から推測して作成しています。

## [Unreleased]

- ドキュメント・テストなどの非機能的な改善予定や小さな調整をここに記載してください。

---

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買プラットフォームのコアライブラリを実装しました。主にデータ取得・ETL・カレンダー管理・研究用ファクター計算・AIベースのニュースセンチメント・市場レジーム判定などの機能を含みます。

### Added
- パッケージ初期化
  - kabusys パッケージ初期化ファイルを追加。バージョンは `0.1.0`、主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出（.git または pyproject.toml）に基づく自動 .env 読み込み。
  - `.env` と `.env.local` の優先度制御（OS 環境変数を保護する protected set）。
  - export 形式やクォート付き値、インラインコメント対応の堅牢な .env パーサ実装。
  - 自動読み込みを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` フラグ対応。
  - 設定クラス Settings を提供し、J-Quants / kabu API / Slack / DB パス /監視閾値 / 環境モード / ログレベルなどのプロパティを公開。未設定の必須環境変数は明示的に例外を投げる（_require）。

- AI モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価機能を実装。
    - 前日15:00 JST〜当日08:30 JSTのニュースウィンドウ計算（UTC naive datetime）を実装（calc_news_window）。
    - raw_news と news_symbols から銘柄ごとに記事を集約し、1銘柄あたりの記事数・文字数制限でトリムして送信。
    - バッチ処理（最大20銘柄/回）、JSON mode を利用したレスポンス検証、スコアの ±1.0 クリッピング。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、code/score の検証）により無効レスポンスはスキップ。
    - 得られたスコアを ai_scores テーブルへ冪等的に書き込む（対象コードのみ DELETE → INSERT）。
    - score_news 公開関数を提供。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）判定。
    - DuckDB からの ma200_ratio 計算（ルックアヘッド防止のため target_date 未満データのみ使用、データ不足時は中立扱い）。
    - マクロキーワードで raw_news をフィルタしてタイトル一覧を取得、LLM によるマクロセンチメント算出（JSON 出力を期待）。
    - OpenAI 呼び出しは独立実装でモジュール間結合を避ける設計。
    - API リトライ、5xx 判定、パース失敗時のフォールバック（macro_sentiment = 0.0）。
    - 合成スコアを market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - score_regime 公開関数を提供。

- 研究用モジュール (kabusys.research)
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム: mom_1m/mom_3m/mom_6m、および ma200_dev（200日移動平均乖離）を計算する calc_momentum を実装。
    - ボラティリティ/流動性: 20日 ATR, ATR 比率, 20日平均売買代金, 出来高比率を計算する calc_volatility を実装。
    - バリュー: raw_financials から直近財務データを取得して PER/ROE を計算する calc_value を実装。
    - DuckDB SQL を用いた効率的なウィンドウ関数実装、データ不足時の None 返却ルールを採用。

  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）に対するリターンを一括クエリで取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマン順位相関を実装。十分なサンプルがない場合は None を返す。
    - ランク変換ユーティリティ（rank）: 同順位は平均ランク、丸めによる ties 対策あり。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出するユーティリティを提供。
    - 研究用関数群を __all__ で公開。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX 市場カレンダー管理ロジックを実装（market_calendar テーブル参照）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB にデータがない場合は曜日ベース（土日を非営業日）によるフォールバックを行う。
    - 最大探索範囲制限や健全性チェック、バックフィル考慮の夜間更新ジョブ calendar_update_job を実装。
    - J-Quants クライアント経由で差分取得・保存（jq.fetch_market_calendar / jq.save_market_calendar 想定）を行う。

  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを定義し、ETL 実行結果（取得数・保存数・品質問題・エラー一覧）を表現。
    - 差分取得・バックフィル・品質チェックを想定した設計。jquants_client と quality モジュールと連携する想定。
    - kabusys.data.etl で ETLResult を再エクスポート。

- 設計方針／品質
  - 多くの関数で datetime.today()/date.today() を直接参照せず、引数で基準日を渡す設計（ルックアヘッドバイアスの防止）。
  - DB 書き込みは冪等性や部分失敗時の保護を重視（対象コードのみ置換する等）。
  - OpenAI 呼び出しに対するリトライ・バックオフ・エラーハンドリングを一貫して実装。
  - DuckDB のバージョン差異への互換性考慮（executemany 空リスト回避、list バインドの挙動回避など）。
  - ロギングを積極的に追加し、警告・情報を明確に出力。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし（ただし環境変数の取り扱いで OS 環境変数を保護する仕組みを実装）。

---

## 参照 / 備考
- 各関数・クラスはドキュメンテーション文字列（docstring）で挙動・設計思想が記載されています。運用時は .env.example を参考に必要な環境変数を設定してください（Settings が必須変数をチェックします）。
- OpenAI API 呼び出しを行う箇所は API キーの注入が可能で、テスト時には内部呼び出し関数をモックすることを想定しています。
- 実際の API クライアント（jquants_client, quality モジュール等）は本コード外に依存します。実行環境でそれらが提供されることを前提としています。