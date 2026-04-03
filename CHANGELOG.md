Keep a Changelog
=================

すべての変更は https://keepachangelog.com/ja/ に準拠して記載しています。

0.1.0 - 2026-04-03
------------------

初期リリース。日本株自動売買プラットフォーム「KabuSys」のコア機能を実装しています。主な追加点・設計方針・フェイルセーフ動作は以下の通りです。

Added
- パッケージ基盤
  - パッケージバージョンを設定（kabusys.__version__ = "0.1.0"）および公開API（__all__）の定義。
- 環境設定管理（kabusys.config）
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動読み込みする仕組みを実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサーは export 先頭指定、クォート（シングル/ダブル）とバックスラッシュエスケープ、インラインコメントの扱いを考慮。
  - OS 環境変数保護（protected set）により .env.local による既存 OS 環境の上書きを防止可能。
  - 必須変数取得ヘルパー _require と Settings クラスを提供（J-Quants / kabu / LINE / DB パス / 監視閾値 / 環境モード / ログレベルなど）。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値にない場合は ValueError を送出）。
- AI（自然言語処理）機能（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON モードでバッチスコアリングを行う score_news を実装。
    - チャンク処理（最大 20 銘柄/チャンク）、1銘柄あたり最大記事数・文字数のトリム、レスポンス検証、スコアの ±1.0 クリップを実装。
    - 再試行（429・ネットワーク断・タイムアウト・5xx）に対する指数バックオフと最大リトライ制御を実装。API エラーやパース失敗時はフェイルセーフで該当チャンクをスキップ。
    - UTC ナイーブ datetime ベースのニュース収集ウィンドウ計算 calc_news_window（JST 前日15:00〜当日08:30 相当）を提供。
    - テスト用に _call_openai_api を差し替え可能（unittest.mock.patch を想定）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - prices_daily / raw_news / market_regime を使用。OpenAI を用いたマクロセンチメント評価は記事が存在する場合のみ実行。API 失敗時は macro_sentiment = 0.0 にフォールバック。
    - レジーム合成、閾値判定、market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - LLM 呼び出しは独立実装でモジュール間結合を避け、テストで差し替え可能。
- データ処理・ETL（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定ロジックを提供（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - market_calendar が空の場合は曜日ベース（土日を非営業日）でフォールバックする一貫した挙動を採用。
    - JPX カレンダー差分取得と保存を行う calendar_update_job（J-Quants クライアント経由）を実装。バックフィル・健全性チェックを実装し、API/保存失敗時は安全に 0 を返す。
  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを公開し、ETL 実行結果（取得件数・保存件数・品質問題・エラー等）を構造化して返す仕組みを導入。
    - 差分更新方針、バックフィル（デフォルト 3 日）や品質チェック（quality モジュール）との連携を想定した設計。
    - jquants_client を通じた idempotent 保存（ON CONFLICT DO UPDATE）を前提。
- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR、出来高系指標）、Value（PER, ROE）を計算する calc_momentum / calc_volatility / calc_value を実装。
    - DuckDB 上の SQL ウィンドウ関数を活用し、データ不足時は None を返すフェイルセーフ設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算 calc_forward_returns（任意ホライズン、入力バリデーションあり）、IC 計算 calc_ic（Spearmanのρ 計算）、ランク変換 rank、統計サマリー factor_summary を実装。
    - 外部依存を用いず標準ライブラリのみで統計処理を実装。
- モジュールの再エクスポート / 初期化ファイル
  - 各サブパッケージの __init__ で主要関数をエクスポート（例: kabusys.ai.__all__ に score_news、kabusys.research.__all__ に calc_* 等）。
  - kabusys.data.etl は pipeline.ETLResult を再エクスポート。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Notes / 設計上の重要な振る舞い・安全策
- ルックアヘッドバイアス防止
  - 各種処理（ニュース窓計算 / ファクター算出 / レジーム判定 / score_news 等）は内部で datetime.today() / date.today() を直接参照せず、外部から与えられる target_date を基準に処理を行う設計。
  - DB クエリは target_date 未満・未満/未満等の排他条件で将来データを参照しないよう注意が払われている。
- フェイルセーフ
  - OpenAI API 失敗時は基本的に例外を上位に波及させず（LLM スコアは 0.0 にフォールバック、該当チャンクはスキップ）、処理を継続する設計を採用。
  - DB 書き込みは明示的なトランザクション（BEGIN / COMMIT / ROLLBACK）で実施し、失敗時はロールバックを試みる。ロールバック自身が失敗した場合は警告ログを出力。
- テスト容易性
  - OpenAI API 呼び出し箇所は _call_openai_api を通すことで unittest.mock.patch により差し替え可能。
- DB 互換性
  - DuckDB の executemany に空リストを渡せない制約を考慮し、空リストチェックを行った上で executemany を呼ぶ実装になっている。
- ロギング
  - 各モジュールで詳細なログ出力（info/debug/warning/exception）を行うようにしており、運用時のトラブルシュートに配慮。

Security
- API キー/トークンは Settings 経由で環境変数から取得する想定。OpenAI API を利用する関数（score_news / score_regime）は API キーが未設定の場合 ValueError を送出して明示的に失敗する。

今後
- PBR・配当利回りなどバリューファクターの追加実装。
- モデルの切替やプロンプト改善、LLM 呼び出しの非同期化・バッチ最適化。
- jquants_client の具象実装とより詳細な品質チェックルールの追加。
- 実運用向けの監視・アラート・実行環境依存の設定周りの拡充。

--- 

この CHANGELOG はソースコードからの推測に基づいて作成しています。実際の変更履歴やリリースノートが別にある場合はそれを優先してください。