CHANGELOG
=========

すべての目立つ変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

v0.1.0 - 2026-03-28
-------------------

Added
- 初回公開: KabuSys パッケージ v0.1.0 を追加。
  - パッケージ構成:
    - kabusys: パッケージのエントリポイント。__version__ = "0.1.0" を定義。
    - kabusys.config
      - .env ファイルまたは環境変数から設定を読み込むユーティリティを実装。
      - プロジェクトルート検出 (.git または pyproject.toml) に基づき自動で .env / .env.local をロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
      - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
      - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境 (development|paper_trading|live) / ログレベルなどのプロパティを取得可能。未設定の必須変数は ValueError を送出。
    - kabusys.ai
      - ai.news_nlp
        - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI (gpt-4o-mini) を用いたセンチメント解析を行い ai_scores テーブルへ書き込む score_news を提供。
        - JST ベースのニュースウィンドウ計算 (前日 15:00 JST ～ 当日 08:30 JST) を実装 (calc_news_window)。
        - バッチ処理（最大 20 銘柄）、1銘柄あたりの最大記事数/文字数トリム、JSON mode のレスポンス検証、429/ネットワーク/5xx に対する指数バックオフリトライ、フェイルセーフ（API失敗時は対象銘柄をスキップ）を実装。
        - DuckDB への書き込みは冪等性を考慮（取得済みコードのみ DELETE → INSERT）し、DuckDB の executemany 制約へ配慮。
      - ai.regime_detector
        - ETF 1321 の 200 日移動平均乖離 (重み 70%) とマクロニュースの LLM センチメント (重み 30%) を合成して日次の市場レジーム（bull/neutral/bear）を計算する score_regime を提供。
        - ma200_ratio の計算、マクロキーワードによる raw_news 抽出、OpenAI 呼び出し（gpt-4o-mini）による macro_sentiment 評価、スコア合成、market_regime への冪等書き込みを実装。
        - ルックアヘッドバイアス防止の設計（target_date 未満データのみ参照、datetime.today() を直接参照しない）。
        - API 失敗時のフェイルセーフ（macro_sentiment = 0.0）とリトライ/エラーハンドリング。
    - kabusys.research
      - factor_research
        - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比）およびバリュー（PER、ROE）を計算する関数群: calc_momentum, calc_volatility, calc_value。
        - DuckDB 上で SQL と Python を組み合わせて高速に計算。データ不足時の None 処理を明記。
      - feature_exploration
        - 将来リターン計算 calc_forward_returns（任意ホライズン対応）、IC 計算 calc_ic（スピアマンのランク相関）、統計サマリー factor_summary、rank 関数を実装。
        - pandas 等の外部ライブラリに依存せず、純粋な Python / SQL 実装。
      - zscore_normalize を data.stats から再エクスポートする仕組みを提供。
    - kabusys.data
      - calendar_management
        - market_calendar による営業日判定・次/前営業日取得・営業日一覧取得・SQ日判定 (is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day) を実装。
        - market_calendar が未取得の場合は曜日ベース（土日非営業日）でのフォールバックを行う設計。
        - calendar_update_job により J-Quants API から差分取得し market_calendar を冪等に更新（バックフィル・健全性チェックあり）。
      - pipeline
        - ETL の差分取得・保存・品質チェックのための基盤を実装。
        - ETLResult データクラスを追加し、ETL の各種カウント、品質問題リスト、エラーリストを保持。has_errors / has_quality_errors / to_dict を提供。
      - etl
        - pipeline.ETLResult を公開インターフェースとして再エクスポート。
      - DuckDB 前提のユーティリティ関数（テーブル存在チェック、最大日付取得など）を提供。
  - テストやモックを容易にするため、OpenAI 呼び出し箇所 (_call_openai_api) はパッチで差し替え可能に実装。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Deprecated
- 初版のため該当なし。

Removed
- 初版のため該当なし。

Security
- 初版のため該当なし。

Notes / 備考
- 期待する DB スキーマ（テーブル名）:
  - prices_daily, raw_news, ai_scores, news_symbols, market_regime, raw_financials, market_calendar などが使用される。
- OpenAI との連携は gpt-4o-mini を想定した JSON mode を利用する設計。API の仕様変更により将来的に調整が必要になる可能性あり。
- .env 自動読み込みはプロジェクトルート検出に依存するため、配布後に意図せず .env が読み込まれることを防ぐには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- 設計上、ルックアヘッドバイアスを避けるため datetime.today() / date.today() を直接用いず、呼び出し側から target_date を明示的に渡す方式を採用しています（一部のバッチジョブは内部で date.today() を利用）。
- DuckDB の executemany に対する互換性（空リスト禁止）に配慮した実装が含まれます。
- エラー時は例外伝播と同時にロールバックを試みる設計（DB 書き込み時の安全処理を実装）。

今後の予定（非保証）
- パフォーマンスやエラーハンドリングの微調整、OpenAI SDK のバージョン変化への対応、追加の品質チェックルールやモニタリング機能の拡充。