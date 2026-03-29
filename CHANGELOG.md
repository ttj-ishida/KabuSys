Keep a Changelog
=================

すべての重要な変更をこのファイルに記載します。  
このプロジェクトは「Keep a Changelog」規約に準拠しています。

Unreleased
---------

- なし

0.1.0 - 2026-03-29
------------------

Added
- 初回公開: kabusys パッケージのコア機能を追加。
  - パッケージメタ情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を定義し、主要サブパッケージをエクスポート（data, research, ai 等）。
- 設定/環境変数管理:
  - src/kabusys/config.py を追加。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - export KEY=val、クォート文字列（エスケープ処理含む）、インラインコメントに対応する堅牢な .env パーサーを実装。
    - OS 環境変数を保護する protected 機構、override フラグにより .env.local の上書きをサポート。
    - 必須変数取得ヘルパー _require と Settings クラスを提供。J-Quants/Slack/OpenAI 等の必須設定をプロパティで公開。
    - KABUSYS_ENV / LOG_LEVEL の値検証、デフォルト値（development, INFO）と duckdb/sqlite のデフォルトパスを定義。
- AI（ニュースNLP / レジーム検出）:
  - src/kabusys/ai/news_nlp.py を追加。
    - ニュース記事を銘柄単位で集約し、OpenAI（gpt-4o-mini）の JSON mode を用いてセンチメントを算出。
    - JST ベースのニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を実装（calc_news_window）。
    - バッチ処理（最大 20 銘柄／リクエスト）、記事数・文字数トリム (_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK)、指数バックオフでのリトライ、レスポンスの厳密なバリデーションとスコアクリッピングを実装。
    - DuckDB への書き込みは idempotent（DELETE → INSERT）で部分失敗時に既存スコアを保護。
  - src/kabusys/ai/regime_detector.py を追加。
    - ETF 1321（Nikkei 225 連動ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算、マクロキーワードフィルタリング、OpenAI 呼び出し（JSON mode）、リトライ/フォールバック（API 失敗時は macro_sentiment=0.0）を実装。
    - market_regime テーブルへの冪等な書き込み（BEGIN / DELETE / INSERT / COMMIT）および例外時の ROLLBACK ロギング。
- Research（ファクター・特徴探索）:
  - src/kabusys/research/factor_research.py を追加。
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR、流動性（平均売買代金・出来高比）等のファクター計算を実装。
    - raw_financials から PER/ROE を組み合わせるバリューファクター calc_value を実装。
    - 全て DuckDB 上の SQL と最小限の Python で完結（外部 API にアクセスしない設計）。
  - src/kabusys/research/feature_exploration.py を追加。
    - 将来リターン計算（calc_forward_returns）、IC（スピアマン ρ を用いた rank ベースの calc_ic）、ランク付け、ファクターサマリー（count/mean/std/min/max/median）を実装。
    - 外部ライブラリに依存しない純 Python 実装。
  - research パッケージで主要関数を再エクスポート。
- Data プラットフォーム / ETL:
  - src/kabusys/data/calendar_management.py を追加。
    - market_calendar テーブルを利用した営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - J-Quants API から差分取得して市場カレンダーを更新する夜間ジョブ calendar_update_job（バックフィル・健全性チェックを含む）を実装。
    - DB の登録あり/なしに応じた曜日ベースのフォールバックを一貫して処理。
  - src/kabusys/data/pipeline.py / etl.py を追加。
    - ETLResult データクラス（ETL 実行結果の収集・変換）を実装し公開。
    - 差分取得・保存（idempotent）・品質チェックの設計を反映。バックフィル、最小日付制御、品質チェックの非致命性（収集は継続）などを実装。
  - DuckDB 互換性と実運用を考慮した細かな実装（ROW_NUMBER を用いた最新財務レコード取得、executemany の空リスト回避、date の変換ユーティリティ）を実装。
- その他ユーティリティ:
  - 各モジュールで詳細なログ・警告メッセージを追加し、障害時の診断を容易に。
  - OpenAI 呼び出しでのテスト容易性のため _call_openai_api を外部差し替え可能に設計（unittest.mock.patch で置換可）。

Changed
- 初期リリースのため該当なし（初回追加に相当）。

Fixed
- 初回リリース時点で以下の堅牢化を盛り込み:
  - lookahead バイアス防止: datetime.today()/date.today() を直接参照しない設計（すべて target_date 引数ベース）。
  - OpenAI 応答の JSON パース耐性: JSON mode でも前後に余計なテキストが混ざる場合の復元ロジックを実装。
  - API エラーの扱い: 429/ネットワーク断/タイムアウト/5xx を再試行対象とし、非 5xx は即スキップ。全リトライ失敗時はフォールバック（ニュース: スコアスキップ、レジーム: macro=0.0）して処理継続。
  - DuckDB 用の実運用考慮: executemany に空リストを渡さない、list 型バインドの回避、日付の型安全な取り扱い等。
  - .env パーサーの堅牢化（export プレフィックス / クォート内のエスケープ / コメント処理）。

Security
- 環境変数の必須チェックを実装:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（各機能利用時）など、未設定時は ValueError を投げて早期検出。
- .env 自動読み込みで OS 環境変数を上書きしない保護機能を実装（protected set）。

Notes / Migration
- 本バージョンは初回リリースのためマイグレーション無し。
- OpenAI API キーや J-Quants トークン等の環境変数を設定してから各 ETL / AI 機能を実行してください。
- DuckDB スキーマ（prices_daily, raw_news, ai_scores, market_regime, raw_financials, market_calendar 等）を事前に用意する必要があります（ドキュメントのスキーマ定義参照）。

Acknowledgements / Design
- 多くの処理で「冪等性」「フェイルセーフ」「ルックアヘッドバイアス回避」を設計原則として採用しています。
- 外部依存（OpenAI, J-Quants）は抽象化し、例外時はシステム全体を停止させない方針です。

今後の予定（目安）
- モデル/プロンプト改善、スコア正規化・キャリブレーション、モニタリング＆通知機能の強化。
- ETL パイプラインの詳細な品質チェック実装と可視化ツール連携。