# CHANGELOG

すべての重要な変更を記録します。本ファイルは Keep a Changelog の慣習に従っています。  

最新リリース
- リリース日付はパッケージ内の __version__ やコードベースから推測して付与しています。

## [0.1.0] - 2026-04-01

### 追加
- パッケージ初回公開相当の機能群を実装・公開。
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = 0.1.0、主要サブパッケージを __all__ で公開）。
- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）に基づくため、CWD に依存しない。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化可能。
    - 読み込み優先度: OS 環境変数 > .env.local > .env（.env.local は上書き）で読み込み。
  - .env パーサーは以下に対応:
    - 空行 / コメント行、先頭に export を付けた形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ
    - クォートなしの行でのインラインコメント処理（直前がスペース/タブの場合にコメント扱い）
    - ファイル読み込み失敗時は警告を出力（例外は抑止）
  - Settings クラスで主要設定をプロパティとして公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパス: DUCKDB_PATH（data/kabusys.duckdb）, SQLITE_PATH（data/monitoring.db）
    - 監視PIDファイル / リソース閾値（CPU/MEM/DISK）
    - 環境種別 KABUSYS_ENV（development / paper_trading / live）の検証
    - ログレベル LOG_LEVEL の検証
    - ヘルパー: is_live / is_paper / is_dev
- AI（自然言語処理）モジュール（kabusys.ai）
  - ニュース向け NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを構築。
    - OpenAI（gpt-4o-mini, JSON mode）へバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - バッチ処理は最大 20 銘柄/コール、1 銘柄あたり記事数上限・文字数トリムを実施（トークン肥大対策）。
    - リトライ戦略: 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフ。
    - レスポンス検証を厳格化（JSON パース、"results" リスト、code と score、未知コードの無視、数値チェック、スコアの ±1.0 クリップ）。
    - 書き込みは冪等性を考慮し、取得できたコードのみ DELETE → INSERT（部分失敗時に既存データを保護）。
    - lookahead バイアスを避ける設計（datetime.today / date.today を参照せず、target_date ベース）。
  - 市場レジーム検出（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を日次判定。
    - マクロニュースは raw_news からマクロキーワードでフィルタ（最大 20 件）し、OpenAI（gpt-4o-mini）でマクロセンチメントを評価。
    - API エラー時は macro_sentiment = 0.0 としてフォールバック（フェイルセーフ）。
    - レジーム判定結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI 呼び出しは独立した内部関数化され、テスト容易性を考慮（モック差し替え可能）。
- Research（研究/因子分析）モジュール（kabusys.research）
  - factor_research:
    - モメンタムファクター（1M/3M/6M リターン、200日 MA 乖離）
    - ボラティリティ/流動性（20日 ATR、ATR 比率、20日平均売買代金、出来高比）
    - バリュー（PER、ROE：raw_financials から取得）
    - DuckDB 上の SQL + Python 組合せで実装。外部 API にはアクセスしない。
    - データ不足時の取り扱い（条件を満たさない場合は None を返す）。
  - feature_exploration:
    - 将来リターン calc_forward_returns（任意ホライズン、検証用）
    - IC（Information Coefficient）計算 calc_ic（Spearman 相関に相当するランク相関）
    - rank, factor_summary（統計サマリ：count/mean/std/min/max/median）
    - 外部ライブラリに依存しない純粋 Python 実装、lookahead バイアス回避設計。
  - research パッケージは zscore_normalize（kabusys.data.stats）を再エクスポート。
- Data（データ基盤）モジュール（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理（market_calendar テーブル読み書き、祝日/半日/SQ 日管理）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日ユーティリティを提供。
    - DB にデータがない場合は曜日ベース（平日のみ営業）でフォールバック。
    - next/prev_trading_day は探索上限 (_MAX_SEARCH_DAYS) を設け無限ループを回避。
    - calendar_update_job により J-Quants API から差分取得・バックフィル（_BACKFILL_DAYS）・健全性チェックを行い冪等保存を試行。
  - pipeline / etl:
    - ETLResult データクラスを定義し ETL 実行結果（取得数・保存数・品質問題リスト・エラー等）を表現。
    - ETL の設計方針として差分更新、backfill、品質チェック（quality モジュール）を想定した実装。
    - kabusys.data.etl で ETLResult を再エクスポート。
  - 各種内部ユーティリティ（テーブル存在チェック、最大日付取得等）を実装。
- DuckDB を主要データストアとして利用する設計をコード全体で採用（型や日付変換ユーティリティを含む）。
- OpenAI 統合
  - gpt-4o-mini を想定した Chat Completions（JSON mode）でレスポンスを厳格に扱う実装。
  - API 呼び出しでのリトライ・バックオフ・エラー分類（RateLimitError / APIConnectionError / APITimeoutError / APIError）に対応。

### 変更
- 初版のため該当なし。

### 修正
- 初版のため該当なし。

### 非推奨
- 初版のため該当なし。

### 注意事項 / 実装上の設計判断（開発者向け）
- lookahead バイアス防止を徹底（datetime.today() などを内部参照しない）。すべてのバッチ処理は呼び出し側から target_date を明示的に渡す想定。
- OpenAI レスポンスのパースや DB 書き込みはフェイルセーフ寄りの設計（API エラーやパース失敗はログ出力してスキップし、例外を波及させない箇所がある一方で、DB 書き込み失敗時はエラーを投げる）。
- .env の自動読み込みはプロジェクトルート探索で行うため、インストール後やテスト環境での振る舞いに注意（必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化）。

---

（この CHANGELOG は、提供されたソースコードから機能・設計意図を読み取り推測して作成したものです。実際のリリースノートとして用いる場合は、差分やコミット履歴に基づいて調整してください。）