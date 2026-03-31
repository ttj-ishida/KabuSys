# CHANGELOG

このプロジェクトは Keep a Changelog の慣習に準拠して変更履歴を管理します。  
フォーマット: https://keepachangelog.com/ja/

すべての日付はローカルリリース日（YYYY-MM-DD）を示します。

## [0.1.0] - 2026-03-31

初回公開リリース。主な追加点と設計方針の概要は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージ初期実装を追加。__version__ = 0.1.0、公開 API の __all__ を定義。
- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - 自動ロードの探索はパッケージファイル位置からプロジェクトルート（.git または pyproject.toml）を検索する方式を採用し、CWD に依存しない。
  - .env パーサーで export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いをサポート。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
  - Settings クラスを提供:
    - J-Quants / kabu ステーション / Slack / DB パス 等のプロパティを定義（必須項目は未設定時に ValueError を送出）。
    - KABUSYS_ENV の許容値検証（development / paper_trading / live）。
    - LOG_LEVEL の許容値検証。
    - duckdb/sqlite のパスを Path オブジェクトで返すユーティリティ。
- AI モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）に JSON mode で問い合わせ、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む。
    - バッチ処理（デフォルト 20 銘柄 / チャンク）・記事トリム（最大記事数・最大文字数）・指数バックオフによるリトライ（429/ネットワーク/タイムアウト/5xx）を実装。
    - レスポンス検証ロジック（JSON 抽出、results 配列・code と score の検証、スコアを ±1.0 にクリップ）を実装。
    - テスト容易性のため、OpenAI 呼び出し内部関数を patch 可能に設計。
  - regime_detector.score_regime:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出は news_nlp.calc_news_window を利用し、OpenAI への呼び出しに失敗した場合は macro_sentiment=0.0 とするフェイルセーフを採用。
    - OpenAI 呼び出しに対してリトライ・サニティチェック・レスポンスパースの堅牢化を実装。
- データ (kabusys.data)
  - calendar_management:
    - market_calendar を利用した営業日判定ユーティリティを追加（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar が未取得の場合の曜日ベースのフォールバック、DB データ優先の一貫した挙動、最大探索日数（_MAX_SEARCH_DAYS）による安全策を実装。
    - calendar_update_job: J-Quants クライアント経由でカレンダーを差分取得し冪等保存、バックフィルと健全性チェックを実装。
  - pipeline / ETL:
    - ETLResult データクラスを実装（ETL 実行結果の構造化、品質チェック情報とエラー集約、シリアライズ）。
    - ETL モジュールのユーティリティ（テーブル存在チェック / 最大日付取得 / 市場カレンダー調整ロジック等）を提供。
  - etl モジュールから ETLResult を再エクスポート。
  - jquants_client のラッパー呼び出しを想定した設計（fetch/save の差分 ETL を想定）。
- Research (kabusys.research)
  - factor_research:
    - calc_momentum / calc_volatility / calc_value の実装。prices_daily / raw_financials を用いたモメンタム・ボラティリティ・バリュー系ファクターの計算ロジックを提供。
    - ATR / 200日MA乖離 / 各種移動平均・出来高指標等を SQL + Python の組合せで計算。
  - feature_exploration:
    - calc_forward_returns（任意ホライズンの将来リターン取得）、calc_ic（スピアマンランク相関による IC）、rank（同順位は平均ランクを返す）、factor_summary（基本統計量集計）を実装。
  - 研究用ユーティリティをまとめて公開（zscore_normalize は kabusys.data.stats から参照）。
- 実装品質
  - DuckDB を主要ストレージとして利用する想定で、書き込み処理は冪等性（BEGIN / DELETE / INSERT / COMMIT）を考慮して実装。
  - ルックアヘッドバイアス回避のため、date.today()/datetime.today() を直接参照しない設計（target_date を明示的に受け取る API）。
  - 各所でログ出力を充実させ、エラー時に冪等性を保ちながら例外を適切に伝播させる設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY で注入可能。未設定時は明示的な ValueError を発生させることで誤操作を防止。

### Notes / Implementation details
- OpenAI 連携は gpt-4o-mini を想定し、JSON Mode を利用した厳密な構造化レスポンスを期待する設計。レスポンスパース失敗や API 障害時はフォールバック動作を定義しており、全体処理の安定性を優先しています。
- DuckDB の executemany に対する互換性（空リスト不可等）を考慮したガードを実装しています。
- テスト容易性のため、OpenAI 呼び出し部分（_call_openai_api）をモジュールローカルで実装しており unittest.mock.patch による差し替えを想定しています。

### Breaking Changes
- 初回リリースのため破壊的変更はありません。

---

今後のリリースでは、監視・実行モジュール（execution / monitoring）や追加の品質チェック、ドキュメント整備、細かなパフォーマンス改善や型アノテーション強化などを予定しています。