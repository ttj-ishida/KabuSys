# CHANGELOG

すべての重要な変更点を Keep a Changelog の形式に従って記載します。日付はコードベースから推定したリリース日を使用しています。

フォーマット:
- [0.1.0] - 2026-04-01（初回リリース）

---

## [0.1.0] - 2026-04-01

初回リリース。日本株自動売買システム「KabuSys」のコアライブラリを提供します。以下は本リリースで追加された主な機能・設計方針・実装上の注意点の要約です。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を定義（src/kabusys/__init__.py、バージョン "0.1.0"）。
  - モジュール公開インタフェースの整理（data, strategy, execution, monitoring など）。

- 環境設定管理 (src/kabusys/config.py)
  - .env/.env.local 自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env パーサー実装: コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応。
  - 読み込み優先順位: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - 必須設定取得ヘルパー _require と Settings クラスを提供。J-Quants / kabu API / Slack / DB パス /監視閾値 / 環境（development/paper_trading/live）/ログレベル等のプロパティを定義。
  - 環境値の検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約して銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出し、ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算ユーティリティ calc_news_window を実装（前日15:00 JST〜当日08:30 JST を UTC に変換）。
    - バッチ処理（最大 20 銘柄/回）、1 銘柄あたりの記事・文字上限（記事数最大10、文字数最大3000）。
    - JSON Mode 応答を期待し、レスポンスのバリデーション処理を実装（results 配列、code/score の検証、スコアクリップ±1.0）。
    - API リトライ戦略（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）、失敗時はスキップして処理継続するフェイルセーフ設計。
    - DuckDB の executemany の制約を考慮した安全な DELETE/INSERT ロジック。
    - テスト用に _call_openai_api を差し替え可能（unit test でのモック容易化）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（Nikkei225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込み。
    - ma200_ratio 計算、マクロ用キーワードで raw_news をフィルタ、OpenAI（gpt-4o-mini, JSON mode）呼び出しで macro_sentiment を算出。
    - API 呼び出しのリトライ・エラーハンドリング、パース失敗時は macro_sentiment=0.0 とするフォールバック。
    - データ不足や未取得時のログ出力と中立扱い（ma200_ratio=1.0）等のフェイルセーフを実装。
    - OpenAI 呼び出しはモジュール内で独立実装し、他モジュールとプライベート関数を共有しない設計（結合度低減）。

- データ基盤 (src/kabusys/data)
  - 市場カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを利用した営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データがない場合の曜日ベースのフォールバック、部分的にしかデータがない場合でも一貫した挙動となる設計。
    - 夜間バッチジョブ calendar_update_job: J-Quants から差分取得して idempotent に保存（バックフィル、健全性チェック含む）。
  - ETL パイプライン (src/kabusys/data/pipeline.py / etl.py)
    - ETLResult データクラスを公開（etl.py から再エクスポート）。
    - 差分取得、保存、品質チェック（quality モジュールとの連携）を想定した ETL フレームワーク骨格を実装。
    - 初回取得用の最小日付、バックフィル設定、品質チェックの重大度管理等を含む。
    - DuckDB テーブル存在チェックや最大日付取得などの内部ユーティリティを実装。
  - jquants_client 連携を前提とした差分保存処理と設計方針（ドキュメント参照）。

- 研究用モジュール (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR）、Liquidity（20日平均売買代金・出来高比率）、Value（PER/ROE）を DuckDB 上の SQL/計算で提供。
    - 入力は prices_daily / raw_financials のみ。結果は (date, code) をキーとする dict のリストで返却。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン calc_forward_returns（任意ホライズン、horizons のバリデーションあり）。
    - IC（Information Coefficient）計算（Spearman の ρ、ランク変換実装）。
    - factor_summary（count/mean/std/min/max/median）と rank ユーティリティ。
    - 外部ライブラリに依存しない実装（標準ライブラリと DuckDB で完結）。

### 変更 (Changed)
- 設計方針の明示
  - すべての ML/AI スコアリング関数は datetime.today()/date.today() を参照しない設計（ルックアヘッドバイアス防止）。target_date を明示的に渡す API を採用。
  - OpenAI 呼び出しに対する堅牢なエラーハンドリングとリトライポリシーを採用（フェイルセーフでスコアのデフォルト化／スキップを行う）。

### 修正 (Fixed)
- DuckDB 互換性の考慮
  - executemany に空リストを渡せない DuckDB の制約への対応（空なら実行しないガード）。
  - DATE 値の変換ユーティリティ _to_date を実装して DuckDB の型に安全に対応。

### 注意点 / 既知の設計選択 (Notes)
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を使用。未指定時は ValueError を送出する明示的なチェックあり。
- AI モジュールは gpt-4o-mini（JSON mode）を想定してプロンプトを設計しており、レスポンス整形（厳密な JSON）の前提で動作する。実運用では API レスポンスの変化に注意が必要。
- 多くの処理で「失敗時に例外を投げず継続する（フェイルセーフ）」設計を採用しているため、部分的なデータ欠落下でもシステムは停止せずログに警告を出す。
- テスト容易性のため、OpenAI 呼び出しポイントは内部関数として切り出してありモック可能。

---

今後の予定（推測）
- strategy / execution / monitoring モジュールの実装拡充（発注ロジック、実行監視、Slack 通知等）。
- jquants_client や kabu ステーション API の具体的実装およびそれらとの統合テスト。
- docs の整備（StrategyModel.md, DataPlatform.md 等に基づく運用手順の追加）。

---

以上。追加で各モジュールごとの詳細な変更履歴（関数一覧やログメッセージ例）を含めた拡張版が必要であれば作成します。