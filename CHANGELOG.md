CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースの内容から推測して作成した初期の変更履歴（リリースノート）です。

フォーマット:
- 追加: 新機能や公開 API
- 変更: 既存機能の重要な変更
- 修正: バグ修正や安定化
- 注意事項: 互換性や運用上の注意点

Unreleased
----------
（なし）

[0.1.0] - 2026-03-27
--------------------

Added
- パッケージ初期公開
  - パッケージメタ情報: kabusys.__version__ = 0.1.0、トップレベルで data/strategy/execution/monitoring を公開。

- 環境設定管理 (kabusys.config)
  - .env ファイルと環境変数から設定値を読み込む自動ロードを実装。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索し、CWDに依存しない動作）。
  - 高度な .env パーサーを実装:
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメント/コメント判定の取り扱い
  - .env と .env.local の優先度・上書き制御を実装。OS 環境変数を保護する protected キーセットを考慮。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト用）。
  - Settings クラスを提供し、アプリケーションで必要な設定値（J-Quants / kabu API / Slack トークン、DB パス、実行環境/ログレベル判定等）をプロパティ経由で取得可能に。
  - 環境変数の必須チェックを行い未設定時は明示的なエラーを発生させる _require() を実装。
  - KABUSYS_ENV や LOG_LEVEL の許容値チェック（バリデーション）を実装。

- AI モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング (news_nlp):
    - raw_news / news_symbols から記事を銘柄別に集約し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信して銘柄ごとにセンチメント（-1.0〜1.0）を算出。
    - 計算ウィンドウ（JST基準）と DuckDB を用いた時刻処理を実装。
    - バッチ処理、1チャンクあたり最大銘柄数の制御、1銘柄あたりの記事数/文字数のトリム機能を実装。
    - API 呼び出しで 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。
    - JSON レスポンスの堅牢なバリデーション（余分な前後テキストの復元、結果形式チェック、未知コードの無視、数値チェック）を実装。
    - ai_scores テーブルへの冪等更新（対象コードのみ DELETE → INSERT）を実装し、部分失敗時に既存スコアを保護。
    - テスト用フック: _call_openai_api をモック可能（unittest.mock.patch）。

  - 市場レジーム判定 (regime_detector):
    - ETF 1321（225連動ETF）の200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily と raw_news を用いて ma200_ratio とマクロ記事タイトルを取得。
    - OpenAI（gpt-4o-mini、JSON Mode）でマクロセンチメントを評価。API 障害時はフェイルセーフとして macro_sentiment = 0.0 を採用。
    - レジームスコアの合成、閾値によるラベル付け、market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - OpenAI 呼び出しは news_nlp とは意図的に別実装とし、モジュール間結合を避ける設計。

- リサーチモジュール (kabusys.research)
  - factor_research:
    - モメンタム（約1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER・ROE）計算を実装。
    - DuckDB 内の prices_daily / raw_financials を参照して安全に計算。データ不足時の None 処理を明示。
    - 関数: calc_momentum, calc_volatility, calc_value を提供し、(date, code) をキーとする dict のリストを返す。

  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）での fwd_?d を一括取得。horizons 入力検証あり。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関をランク変換と共に実装。小サンプルや分散0のケースは None を返す。
    - ランク変換ユーティリティ（rank）とファクター統計サマリー関数（factor_summary）を実装。
    - pandas 等に依存せず、標準ライブラリと DuckDB を使用する実装。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (calendar_management):
    - market_calendar テーブルを用いた営業日判定とユーティリティを実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - market_calendar が未取得の場合は曜日ベース（土日非営業）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新する夜間バッチ処理を実装。バックフィル・健全性チェック（将来日付異常検出）を備える。
    - DuckDB 型変換ユーティリティ等も提供。

  - ETL パイプライン (pipeline, etl):
    - ETLResult データクラスを公開（pipeline.ETLResult を etl に再エクスポート）。
    - ETL の補助関数（テーブル存在チェック、最大日付取得、トレーディングデイ調整等）を実装。
    - 差分更新・バックフィル・品質チェック連携を想定した設計（jquants_client と quality モジュールと連携）。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Notes / 設計上の重要点
- ルックアヘッドバイアス対策:
  - 各処理（AI スコアリング / レジーム判定 / ファクター計算）は内部で datetime.today() / date.today() に依存せず、呼び出し側から target_date を受け取る設計。
  - DB クエリは target_date 未満／以内の排他条件を明確にし、将来データを参照しないように実装。

- フェイルセーフ性:
  - OpenAI 等外部 API の失敗時はゼロやスキップで継続する戦略を採用し、例外で全体処理を停止しないよう配慮（ただし DB 書き込みでの例外は上位へ伝播）。

- テストフレンドリー:
  - OpenAI 呼び出し箇所をモック可能にしてユニットテストで差し替えやすい設計。

- DB（DuckDB）互換性:
  - DuckDB の executemany の制約等（空リスト不可）に配慮した実装がある。
  - SQL クエリ内でのウィンドウ関数活用や ROW_NUMBER による最新財務レコード取得など、DuckDB を前提とした最適化がなされている。

Known limitations / Future work
- PBR・配当利回りなど一部バリューファクターは未実装（calc_value の注記参照）。
- jquants_client / quality モジュールの実装（このコード一覧には含まれていない）と連携して初めて ETL が完結する。
- strategy / execution / monitoring パッケージの内容は本変更リストでは確認できないため、運用時はそれらの API 仕様を合わせて確認する必要あり。

ライセンス
- 本 CHANGELOG はコードから推測して作成したものであり、実際のコミット履歴に基づくものではありません。実際のリリースノート作成時は Git の履歴や CHANGELOG の正規記録を参照してください。