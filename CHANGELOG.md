# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-28

初回公開リリース。日本株自動売買プラットフォームのコアライブラリを提供します。
主な目的はデータ取得・ETL、マーケットカレンダー管理、ファクター計算、ニュースNLPおよび市場レジーム判定、並びに各種ユーティリティの提供です。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージの公開 API を __all__ で整理（data、research、ai 等のモジュール群を想定）。

- 環境設定 (src/kabusys/config.py)
  - .env ファイル自動読み込み機能をプロジェクトルート（.git または pyproject.toml を探索）から実装。
  - .env/.env.local の優先順位処理（OS環境変数優先、.env.local は上書きが可能）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑止フラグ対応。
  - export KEY=val 形式やクォーテーション・エスケープ、行内コメント処理に対応する独自パーサ実装。
  - 必須環境変数取得ヘルパー (_require) と Settings クラスを提供（J-Quants、kabu API、Slack、DB パス等の設定）。
  - 環境チェック: KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の値検証を実装。
  - デフォルトの DB パス（DUCKDB_PATH、SQLITE_PATH）のデフォルト値と Path 変換。

- AI モジュール (src/kabusys/ai)
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）を calc_news_window で提供。
    - バッチサイズ、記事数上限、文字数トリムなどトークン肥大化対策を実装。
    - JSON Mode を利用したレスポンス検証 / 抽出ロジック（余分な前後テキスト対策含む）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。リトライ後も問題があればスキップ（フェイルセーフ）。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能に設計（_call_openai_api を patch 可能）。

  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み70%）とニュース由来の LLM センチメント（重み30%）を合成して日次市場レジーム（bull/neutral/bear）を判定・保存。
    - MA 計算はルックアヘッド防止のため target_date 未満のデータのみ使用。データ不足時は中立値（1.0 など）でフォールバック。
    - OpenAI 呼び出しは別実装で、API エラーやパース失敗時は macro_sentiment=0.0 にフォールバック。
    - score_regime による冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。

- Data モジュール (src/kabusys/data)
  - calendar_management（src/kabusys/data/calendar_management.py）
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装（J-Quants から差分取得して market_calendar に保存）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定 API を提供。
    - market_calendar が未取得の場合は曜日ベース（土日非営業）でのフォールバックを実装。
    - 探索範囲の上限 (_MAX_SEARCH_DAYS) による無限ループ防止、バックフィル等の健全性検査を実装。

  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを実装し、ETL 実行結果の集約（取得数・保存数・品質問題・エラー一覧）を表現。
    - 差分更新、バックフィル、品質チェックの枠組みを盛り込んだパイプライン基盤の設計を反映。
    - jquants_client 経由の保存処理を前提とした idempotent な保存設計についての文書化。

- Research モジュール (src/kabusys/research)
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER、ROE）などのファクター計算を実装。prices_daily / raw_financials を参照。
    - データ不足時の None フォールバック、SQL ベースの集計で営業日ベースの窓管理を実装。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、統計サマリー（factor_summary）、ランク付けユーティリティ（rank）を提供。
    - rank は同順位の平均ランク計算、浮動小数点丸め対策（round(v,12)）を実装。
  - research パッケージの __all__ で主要関数を再エクスポート。

- その他
  - データベース関連: DuckDB を主要な分析 DB として採用（関数は DuckDB 接続を受け取る設計）。
  - ロギングメッセージを各処理に追加し、運用時の観察性を確保。
  - トランザクション処理時の例外発生時に ROLLBACK を行い失敗ログを残す設計。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 既知の注意点 / 設計上の重要事項 (Notes)
- ルックアヘッドバイアス防止
  - AI スコアリングやレジーム判定等の関数は内部で datetime.today() や date.today() を参照せず、全て caller が与える target_date に依存する設計です。運用・テスト時は target_date の指定に注意してください。
- フェイルセーフ
  - OpenAI API 呼び出しの多くは、エラー時に例外を投げず中立スコアやスキップで継続するよう設計されています（例: macro_sentiment = 0.0、スコア未取得時は対象銘柄をスキップ）。重大な失敗をアラートするためログ出力は行いますが、ETL や夜間処理の継続性を優先します。
- トランザクションと冪等性
  - DB 書き込みは可能な限り冪等（DELETE→INSERT、ON CONFLICT 期待）かつトランザクションで保護しています。部分失敗が起きた場合でも既存データを不必要に消さないよう配慮しています。
- テスト支援
  - OpenAI への API 呼び出し部分は内部的に関数化され（_call_openai_api 等）、unittest.mock.patch による差し替えでテスト可能です。
- 環境変数の制約
  - Settings の必須項目（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID など）は未設定の場合 ValueError を送出します。CI/デプロイ前に .env を用意することを推奨します。

### セキュリティ (Security)
- リリースにおける既知のセキュリティ問題はありませんが、OpenAI API キーや各種トークンは環境変数で扱う設計のため、機密情報の管理にはご注意ください（.env ファイルの取り扱い、リポジトリへのコミット禁止など）。

---

今後の予定（例）
- ai モジュールのモデル代替（gpt-4 系など）や結果キャッシュの追加
- ETL の並列化・差分効率化、品質チェックのルール追加
- テストカバレッジ拡充・CI ワークフロー定義

（この CHANGELOG はコードベースの実装内容から推測して作成しています。実際のリリースノート作成時は運用側の変更履歴と合わせて調整してください。）