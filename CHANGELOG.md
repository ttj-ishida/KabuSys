Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。

[Unreleased]
------------

- （現時点の変更はありません）

[0.1.0] - 2026-04-04
-------------------

Added
- 初期リリースを公開。
- パッケージ構成:
  - kabusys (コアパッケージ)
    - data: ETL / カレンダー管理 / パイプライン関連ユーティリティ（DuckDB ベース）
    - research: ファクター計算・特徴量探索モジュール
    - ai: ニュース NLP と市場レジーム判定（OpenAI 経由のスコアリング）
    - config: 環境変数・設定管理
    - （将来の拡張を想定して monitoring 等をエクスポート）
- 環境変数/設定管理 (kabusys.config)
  - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env ファイルのパースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント（スペース/タブで前置）の扱いに対応。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - Settings クラスを提供し、J-Quants / kabu / LINE / DB パス / 監視しきい値 / 実行環境などのプロパティ経由で設定値を取得。
  - 必須設定未指定時は ValueError を発生させる（明示的なエラーにより誤設定を検出）。
  - KABUSYS_ENV と LOG_LEVEL の入力検証を実装（許容値のチェック）。
- AI ニュース NLP (kabusys.ai.news_nlp)
  - raw_news と news_symbols を元に、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）へバッチ送信しセンチメントを ai_scores テーブルへ書き込む。
  - バッチ処理: 最大 20 銘柄／チャンク、1銘柄あたり最大記事数・文字数でトリム。
  - OpenAI 呼出しは JSON Mode を利用し、レスポンスの厳格なバリデーションと ±1.0 のクリップを実施。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライを実装。その他のエラーはスキップして継続（フェイルセーフ）。
  - テスト容易性のため内部の _call_openai_api を patch 可能に設計。
  - レスポンスパース失敗や部分失敗時でも既存スコアを不用意に消さないよう、書き込みは対象コードのみの DELETE → INSERT を採用。
- 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ冪等書き込み。
  - マクロ記事抽出のためのキーワードリストを提供（日本・米国・グローバルの代表語句）。
  - OpenAI 呼出しに対するリトライ、API エラーの取り扱い、JSON パース失敗時のフォールバック（macro_sentiment=0.0）。
  - ルックアヘッドバイアスを防止する設計（内部で datetime.today()/date.today() を参照しない。target_date 未満のデータのみ使用）。
- データ / カレンダー管理 (kabusys.data.calendar_management)
  - market_calendar を使った営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
  - DB 登録がない場合は曜日ベースのフォールバック（平日＝営業日）を一貫して使用。
  - calendar_update_job: J-Quants から差分取得して market_calendar に冪等保存。バックフィル・健全性チェックを実装。
- ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl)
  - ETLResult データクラスを定義して ETL の実行結果（取得数・保存数・品質問題・エラー等）を構造化して返せるようにした。
  - 差分更新・バックフィル・品質チェックのための基盤ロジックを実装設計（実装内で説明）。
- 研究（Research）ユーティリティ (kabusys.research)
  - ファクター計算: calc_momentum / calc_value / calc_volatility（prices_daily / raw_financials を参照）。
  - 特徴量探索: calc_forward_returns / calc_ic / factor_summary / rank。
  - Zスコア正規化ユーティリティを data.stats 側から再エクスポート。
  - すべて DuckDB 接続を受け取り SQL と純粋な Python で実行（外部 API や pandas 等に依存しない）。
- ロギングとフォールバック方針
  - 外部 API 失敗時は例外で即終了させずログ出力して安全なデフォルト（中立スコアやスキップ）で継続する設計。
  - DB 書き込み時は冪等処理（BEGIN / DELETE / INSERT / COMMIT / ROLLBACK の使用）を徹底。

Changed
- （初回リリースのため変更履歴なし）

Fixed
- （初回リリースのため修正履歴なし）

Security
- （初回リリースのためセキュリティ項目なし）

Notes / 設計上の重要点
- ルックアヘッドバイアス防止:
  - AI スコアリングやレジーム判定など時系列に敏感な処理では、内部で date.today()/datetime.today() を直接参照せず、外部から与えた target_date を基準として処理する方針を採用。
- テストしやすさ:
  - OpenAI 呼出し関数は内部で切り替え可能（patch 可能）にしてあり、ユニットテストで API 呼び出しをモックしやすい設計。
- DuckDB を主なデータストアとして想定。executemany の空リストバインド等、DuckDB の実装制約に配慮した実装を行っている。

今後の予定（非網羅）
- monitoring モジュールの追加/拡充（パッケージの __all__ に準備あり）
- ETL / 品質チェックの更なる充実（自動アラート・履歴トラッキング等）
- より細かいドキュメント・使用例の追加

-----