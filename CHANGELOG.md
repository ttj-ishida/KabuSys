# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の慣例に従って記載しています。  
このプロジェクトはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買支援ライブラリ「KabuSys」の基盤機能を実装しました。  
主にデータ取得/ETL、マーケットカレンダー管理、ファクター計算、ニュースNLP（LLM）によるセンチメント集約、そして市場レジーム判定の機能を含みます。

### 追加 (Added)
- パッケージ基礎
  - パッケージ初期化（kabusys.__init__）とバージョン管理（__version__ = "0.1.0"）。
  - モジュール公開インターフェースの定義（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理 (kabusys.config)
  - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
  - export 形式やクォート付き値、インラインコメントの扱いに対応した .env パーサー実装。
  - 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）に対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス等の設定をプロパティ経由で安全に取得。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL 等）と必須環境変数未設定時のエラー（_require）。

- AI / ニュース分析 (kabusys.ai)
  - ニュースセンチメント集約（news_nlp.score_news）
    - 指定タイムウィンドウ（前日15:00 JST〜当日08:30 JST）で raw_news と news_symbols を集約。
    - 銘柄毎に最新記事を結合し文字数・記事数で制限（トリム）。
    - OpenAI（gpt-4o-mini）へのバッチ送信（最大 20 銘柄／チャンク）。
    - JSON Mode 応答パースと堅牢なバリデーション（results 配列、code/score 検証）。
    - リトライ（429・ネットワーク・タイムアウト・5xx）を指数バックオフで処理。
    - 成功した銘柄スコアのみを ai_scores テーブルへ冪等的に置換（DELETE → INSERT）。
    - テスト容易性のため _call_openai_api を patch で差し替え可能。
  - 市場レジーム判定（ai.regime_detector.score_regime）
    - ETF 1321（225連動）の200日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - DuckDB 上の prices_daily / raw_news を参照しルックアヘッドを排除するクエリ設計。
    - OpenAI 呼び出しのリトライ・フォールバック実装（失敗時 macro_sentiment=0.0）。
    - market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）とロールバック処理。

- データプラットフォーム (kabusys.data)
  - マーケットカレンダー管理（calendar_management）
    - market_calendar テーブルを用いた営業日判定 API（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバック。
    - JPX カレンダー差分取得バッチ（calendar_update_job）と保存ロジック（バックフィル・健全性チェック）。
  - ETL パイプラインインターフェース（pipeline.ETLResult の公開 re-export via data.etl）
    - ETL 実行結果を表す ETLResult データクラス（取得数・保存数・品質問題・エラー集約、シリアライズ機能）。
  - ETL 実装（data.pipeline）
    - 差分取得・バックフィル・品質チェック方針をコード化（詳細は doc と実装参照）。
    - DuckDB を前提とした最大日付取得・テーブル存在チェック等のユーティリティ。

- リサーチ / ファクター (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M）、200日MA乖離、ATR（20日）、出来高・売買代金関連の計算。
    - DuckDB を用いた SQL ベースの実装で (date, code) 単位の辞書リストを返す形式。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns, 任意ホライズン対応）。
    - IC（Information Coefficient）計算（スピアマンランク相関）。
    - ランク関数（同順位は平均ランク）とファクター統計サマリー（count/mean/std/min/max/median）。
  - research パッケージの公開 API を整備（関数再エクスポート）。

### 変更 (Changed)
- 設計上の意思決定と安全策を反映
  - 分析・スコアリング関数内で datetime.today() / date.today() を直接参照しない実装に統一（ルックアヘッドバイアス防止）。すべて target_date 引数で日付を受け取る設計。
  - OpenAI 呼び出し部分はモジュール間でプライベート関数を共有せず、それぞれ専用の _call_openai_api を定義しており、テストで差し替えやすくしている。
  - DuckDB の互換性（executemany の空リスト制約等）を考慮した実装（空チェックを明示的に行う）。

### 修正 (Fixed)
- エラー/フォールトトレランスの強化
  - OpenAI API の失敗（ネットワーク/タイムアウト/429/5xx）に対してリトライとログ出力を実装。最終的に例外を上位に伝播させずフォールバック値（例: macro_sentiment=0.0）で継続する箇所を明確化。
  - DB 書き込み時のトランザクション管理（BEGIN/COMMIT/ROLLBACK）とロールバック失敗時の警告ログ出力を追加。
  - raw_news / news_nlp の JSON パースで余分な前後テキストが入るケースに対する復元ロジックを実装（最外の { } を抽出してパース）。

### 既知の制約 (Known issues / Notes)
- 外部依存:
  - OpenAI SDK（OpenAI クライアント）および DuckDB を利用。実行環境にこれらが必要。
- テーブル前提:
  - 多くの関数が DuckDB 内の特定テーブル（prices_daily, raw_news, ai_scores, market_calendar, raw_financials, news_symbols 等）を前提とする。テーブルスキーマ・存在は呼び出し側で保証する必要がある。
- 部分失敗時のデータ保護:
  - ai_scores 等への書き込みは「取得成功分のみ上書き」することで部分失敗時の既存データ保護を行うが、完全なトランザクション分離や高度なロールフォワード機能は未実装。
- バージョン / 設定:
  - デフォルトの DB パスは settings により data/kabusys.duckdb / data/monitoring.db などに設定。環境に合わせて DUCKDB_PATH / SQLITE_PATH を設定すること。

### ドキュメント / テスト支援
- テスト容易性のため以下を用意/考慮:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動 .env ロードの無効化。
  - news_nlp / regime_detector の OpenAI 呼び出しをモックするための patch ポイント（各モジュールの _call_openai_api）。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの実装強化（本リリースでは基盤機能主体）。
- ai モデル評価の拡張（モデル選択のパラメータ化、返却形式の強化）。
- ETL のスケジューリング・監視ダッシュボード連携。

ご要望があれば、各モジュールごとの詳細な変更説明や利用例（コードスニペット）、マイグレーション手順（既存データベースからの移行など）を追記します。