# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース

### Added
- パッケージ基盤
  - kabusys パッケージの基本エントリーポイントを追加（version = 0.1.0）。
  - パッケージ公開用の __all__ に data, strategy, execution, monitoring を定義。

- 環境設定 / 設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする仕組みを実装。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサを実装（export プレフィックス対応、シングル／ダブルクォート内のエスケープ、インラインコメントの扱いなど）。
  - .env 読み込み時の上書き制御（override）と OS 環境変数の保護（protected set）を実装。
  - Settings クラスを追加し、アプリ設定をプロパティ経由で取得可能に：
    - J-Quants / kabuステーション / Slack の必須トークン取得（未設定時は ValueError を送出）。
    - DB パス（duckdb/sqlite）のデフォルト値と Path 変換。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーション（許容値チェック）。
    - is_live / is_paper / is_dev の便利プロパティ。

- AI モジュール（kabusys.ai）
  - ニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）を実装。
  - news_nlp.score_news:
    - 前日 15:00 JST 〜 当日 08:30 JST に相当する UTC ウィンドウを計算して記事を集約。
    - 銘柄ごとに最新記事を最大件数・文字数でトリムし、最大 20 銘柄／チャンクで OpenAI（gpt-4o-mini）へ送信。
    - JSON Mode を利用したレスポンス処理、厳密なバリデーション、スコアの ±1.0 クリップ。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ（設定値あり）。
    - DuckDB への書き込みは部分置換（対象コードのみ DELETE → INSERT）で冪等性を確保。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - マクロキーワードによる raw_news フィルタリング、OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を算出。
    - レジーム合成ロジック、閾値（BULL/BEAR）、および market_regime テーブルへの冪等書き込みを実装。
  - OpenAI 呼び出しはテストで差し替え可能なラッパー関数化（ユニットテスト容易化）。
  - API 失敗時はフェイルセーフとして macro_sentiment=0.0（続行）する設計。

- Data モジュール（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理機能（market_calendar の参照・更新・夜間バッチ処理 calendar_update_job）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定・検索ユーティリティを実装。
    - market_calendar が未取得の場合は曜日ベース（土日除外）でのフォールバックを提供。
    - 更新ジョブはバックフィルや健全性チェック（将来日付の異常検知）を実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラーの集計）。
    - 差分取得・バックフィル・品質チェックを想定した ETL 層のユーティリティを実装。
    - DuckDB 存在チェック・最大日付取得等のヘルパーを実装。
  - etl の実装方針として、J-Quants クライアント経由での差分取得、冪等保存（ON CONFLICT 相当）の想定を文書化。

- Research モジュール（kabusys.research）
  - factor_research:
    - momentum / volatility / value ファクター計算を実装（prices_daily / raw_financials を参照）。
    - mom_1m / mom_3m / mom_6m / ma200_dev、atr_20 / atr_pct / avg_turnover / volume_ratio、per / roe 等を SQL ベースで算出。
    - データ不足時は None を返す安全設計。
  - feature_exploration:
    - calc_forward_returns（任意ホライズンの将来リターン計算、入力検証あり）を実装。
    - calc_ic（Spearman ランク相関による IC 計算）、rank（同順位は平均ランク）を実装。
    - factor_summary（count/mean/std/min/max/median）を実装。
  - 研究系ユーティリティは外部依存を使わず標準ライブラリ＋DuckDB SQL で実装。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- 環境変数に機密トークン（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）を期待する設計。これらが未設定の場合は一部機能が ValueError を送出するため、運用時には適切な環境管理が必要。
- .env 自動読み込みは OS 環境変数優先、.env.local による上書きを許可。OS 環境変数は保護され上書きされないよう設計。

### Notes / Implementation details（設計上の重要点）
- ルックアヘッドバイアス回避: datetime.today() / date.today() を直接参照する処理を避け、関数引数として target_date を受け取る設計を徹底。
- OpenAI 呼び出し:
  - モデル: gpt-4o-mini（JSON mode を利用して厳密な JSON 出力を期待）。
  - リトライ対象は 429・ネットワーク断・タイムアウト・5xx。その他は基本的にスキップして継続（フェイルセーフ）。
  - レスポンスは堅牢にパース・検証し、異常時はログに警告を出してスキップ。
- DuckDB 互換性配慮:
  - executemany に空リストを渡せない制約（DuckDB 0.10）を考慮して、空チェックを行ってから executemany を呼ぶ。
  - 日付型の取り扱いで文字列変換を行うユーティリティを提供（_to_date 等）。
- 冪等性:
  - DB 書き込みは基本的に削除→挿入の順で対象を限定して置換することで冪等性・部分失敗耐性を確保。

---

今後のリリース候補（想定機能）
- strategy / execution / monitoring 各層の実装（実取引連携、発注ロジック、監視アラート）
- J-Quants クライアントと実データの初回ロード用ユーティリティの追加
- 単体テスト及び CI の追加（OpenAI 呼び出しのモック化等）