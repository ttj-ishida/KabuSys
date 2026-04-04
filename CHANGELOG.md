Keep a Changelog に準拠した CHANGELOG.md を以下に作成しました。コードベースの内容（モジュール名・関数・設計方針・既定値など）から推測して記載しています。必要に応じて日付・表現を調整してください。

CHANGELOG.md
=============
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠しています。  
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
- (今後追加・変更予定の項目をここに記載)

[0.1.0] - 2026-04-04
--------------------
Added
- 初回リリース: "KabuSys" — 日本株自動売買システムのベース実装を公開。
  - パッケージ公開: src/kabusys/__init__.py により主要サブパッケージ (data, strategy, execution, monitoring) を公開。
- 環境設定管理 (kabusys.config)
  - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml により検出）。
  - .env/.env.local の読み込み順序を定義（OS 環境 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env 行パーサを実装（export 形式、シングル／ダブルクォート、バックスラッシュエスケープ、コメントの取り扱いに対応）。
  - Settings クラスで各種設定をプロパティとして公開（J-Quants トークン、kabu API 設定、LINE トークン、DB パス、監視閾値、実行環境/ログレベル検証等）。
  - 環境変数未設定時に明示的なエラーを出す _require() を実装。
- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI (gpt-4o-mini, JSON mode) でセンチメントをスコア化。
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST）と calc_news_window 関数を提供。
    - バッチ処理 (最大20銘柄/呼び出し)、記事数/文字数トリム、JSON 応答の堅牢なパースとバリデーションを実装。
    - 再試行（429/ネットワーク/タイムアウト/5xx）と指数バックオフを実装。失敗時は例外を投げずスキップまたは部分書き込みでフェイルセーフ化。
    - score_news(conn, target_date, api_key=None) を公開。成功時は書き込んだ銘柄数を返す。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロキーワードフィルタ、OpenAI 呼び出し、再試行／フェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
    - 書き込みは market_regime テーブルへ冪等に行う（BEGIN/DELETE/INSERT/COMMIT）。score_regime(conn, target_date, api_key=None) を公開。
- Data / ETL / カレンダー (kabusys.data)
  - ETL パイプライン基盤 (kabusys.data.pipeline)
    - ETLResult データクラスを実装（取得数・保存数・品質チェック結果・エラー集約等）。
    - 差分取得・バックフィル・品質チェック・idempotent 保存を想定した設計（jquants_client 経由で保存）。
  - calendar_management
    - JPX カレンダー管理（market_calendar テーブル参照）と営業日判定ユーティリティ群を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が未取得時の曜日ベースのフォールバック、DB 優先ルール、最大探索日数制限や健全性チェックを実装。
    - calendar_update_job により J-Quants からの差分取得と冪等保存（バックフィル含む）を実装。
  - ETL 公開インターフェース (kabusys.data.etl) で ETLResult を再エクスポート。
- Research (kabusys.research)
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算を提供。
    - calc_momentum, calc_volatility, calc_value を公開。DuckDB の prices_daily / raw_financials を参照して計算。
    - 設計上、外部 API 呼び出しは行わず、結果は (date, code) ベースの dict リストで返す。
  - feature_exploration: 将来リターン・IC・統計サマリー等のユーティリティを実装。
    - calc_forward_returns（任意ホライズン、入力検証あり）、calc_ic（Spearman の ρ）、rank、factor_summary を提供。
    - pandas 等非依存で標準ライブラリ + DuckDB で動作するよう設計。
- DuckDB をデフォルトの分析 DB として利用。デフォルトのパスは duckdb: data/kabusys.duckdb、sqlite: data/monitoring.db。
- 実行監視関連の設定（pid ファイル、kill flag、CPU/メモリ/ディスク閾値）を Settings で提供。

Fixed / Improved
- .env パーサの堅牢化: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等に対応。
- OpenAI 応答パースの耐性向上: JSON mode でも前後に余計なテキストが混在するケースを想定して最外側の {} を抽出してパースを試行。
- DuckDB executemany の互換性考慮: 空リストでの executemany を避けるガードを追加（DuckDB 0.10 互換性対応）。
- DB 書き込みは冪等性を重視（DELETE → INSERT の置換方式）して部分失敗時に既存データを保護。
- API 呼び出しの再試行ロジックとログ出力を整備（リトライ回数・指数バックオフ・5xx と非 5xx の扱い差別化）。

Security
- OpenAI API キー未設定時に明確な ValueError を発生させて失敗を早期検出する仕様を導入（score_news / score_regime）。

Notes / Design decisions
- ルックアヘッドバイアス防止: 全 AI / リサーチ処理は内部で datetime.today() / date.today() を参照せず、明示的な target_date を受け取る設計。
- フェイルセーフ方針: API 失敗や部分的な処理失敗時にも例外で全処理を止めず、ログ出力とスキップで継続する（ただし DB 書き込み失敗時は例外伝播）。
- JSON Mode を利用した LLM 呼び出しに対して応答のバリデーションを厳格に実施。
- jquants_client / quality モジュール経由での外部 API 取得や品質チェックと組み合わせる想定。

Acknowledgements
- 本 CHANGELOG はコードベースの内容（モジュール、関数名、docstring、定数、設計方針）から推測して作成しています。実際のリリースノートや変更履歴として正式に使用する場合は、変更者によるレビュー・補足（リリース担当者名、厳密な日付、追加の既知の問題や制約）をお願いします。