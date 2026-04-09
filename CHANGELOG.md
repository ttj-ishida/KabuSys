CHANGELOG
=========

すべての変更は Keep a Changelog の書式に従っています。  
https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-09
--------------------

Added
- パッケージ初回公開（kabusys 0.1.0）。
- 基本モジュール群を実装・公開:
  - kabusys.config: 環境変数／.env 管理。プロジェクトルート検出（.git / pyproject.toml）に基づく自動 .env ロード、優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能を追加。.env パースは export プレフィックス、クォート・エスケープ、インラインコメント等に対応。
  - Settings クラス: J-Quants / kabu API / LINE / DB パス / Paper Trading / 監視閾値 / 実行環境・ログレベル等をプロパティ経由で取得。必須値未設定時は明示的な例外を発生させる（_require）。
  - kabusys.ai.news_nlp: ニュース記事の LLM センチメント解析。gpt-4o-mini の JSON Mode を利用したバッチスコアリング（最大20銘柄/チャンク）、チャンクごとのリトライ（429/ネットワーク/5xx）と指数バックオフ、レスポンスの堅牢なバリデーション・スコアクリッピング（±1.0）、DuckDB の raw_news/news_symbols/ai_scores を用いた idempotent 書き込みロジック。
  - kabusys.ai.regime_detector: ETF(1321) の 200 日移動平均乖離とニュースマクロセンチメントを重み付け（70%/30%）して日次市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込み。OpenAI API 呼び出しは独立実装でモジュール結合を避け、API障害時はフォールバック（macro_sentiment=0.0）するフェイルセーフを備える。
  - kabusys.data.pipeline / etl: ETL の高レベル API と ETLResult データクラスを提供。差分取得・バックフィル・品質チェックを想定した設計。品質問題は収集して返却（Fail-Fast にはしない）。
  - kabusys.data.calendar_management: JPX マーケットカレンダーの夜間差分更新ジョブ(calendar_update_job) と営業日判定ユーティリティ(is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day)。market_calendar が未登録のときは曜日フォールバック（週末非営業日）。DB 登録ありの場合は DB 値優先、未登録日は一貫したフォールバックを行う。
  - kabusys.research: ファクター計算・探索モジュール群を実装。calc_momentum / calc_value / calc_volatility（ATR・流動性等）、calc_forward_returns（任意ホライズン）、calc_ic（Spearman ランク相関）、rank、factor_summary、zscore_normalize（data.stats から再エクスポート）などを提供。DuckDB SQL + Python による自己完結型実装。
- OpenAI クライアント呼び出し部（news_nlp, regime_detector）はテスト差し替え可能（モジュール内 private 関数を patch して置換可能）。
- DuckDB を主要 DB として利用する設計を採用し、クエリは lookahead やルックアヘッドバイアスに注意して実装（target_date 未満／排他条件など）。

Changed
- （初版リリースのため該当なし）

Fixed
- （初版リリースのため該当なし）

Security
- 環境変数の取り扱いに注意した保護機構を実装（.env の上書き時に OS 環境変数を保護する protected set）。OPENAI_API_KEY 等の必須キーがない場合は明示的なエラーを返すことで誤動作を防止。

Notes / Implementation details
- ルックアヘッドバイアス防止: 全ての日付計算は内部で現在時刻 (datetime.today()/date.today()) を直接参照するコードを最小化。各関数は target_date を受け取り、その周辺のウィンドウを決定する方式を採用。
- API 呼び出しの堅牢性: 429/ネットワーク断/タイムアウト/5xx に対しては指数バックオフでリトライし、最終的に失敗した場合は安全側の既定値（例: macro_sentiment=0.0）で継続する方針。
- DB 書き込みは冪等性を意識（DELETE → INSERT など）。DuckDB の executemany の仕様差異（空リスト不可）を考慮した防御的実装あり。
- JSON Mode を期待するが、LLM の余計な前後テキストを検出して最外の {} を抽出するなど現実のレスポンスノイズに対処する実装を含む。
- Paper Trading 機能向けに PAPER_FILL_MODE などの設定があり、許容値バリデーションを行う。
- ログ出力・警告を多用し、異常時にサイレントフェイルしない設計。

Known limitations / TODO
- PBR・配当利回り等のバリューファクターは未実装（calc_value の注記）。
- monitoring パッケージは __all__ に含まれるが（パッケージ公開意図あり）、本差分での詳細実装は限定的。
- 外部依存: openai SDK の API 仕様の変化に対して status_code 取得を安全に行う等の互換性考慮はしているが、将来的な SDK 変更に追従が必要。
- 単体テスト・統合テストは別途整備が必要（OpenAI 呼び出しはモック可能に実装済み）。

署名
----
この CHANGELOG は現行ソースコードから推測して作成しています。実際のリリースノートとして利用する場合は、開発履歴（コミットログ・リリースポリシー）に基づく追補を推奨します。