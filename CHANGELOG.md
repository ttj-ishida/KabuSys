# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このファイルではリポジトリから推測した初期リリースの内容を日本語でまとめています。

[Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。本バージョンは主要なサブパッケージ（データ取得/ETL、研究用ファクター、AI ニュース解析、環境設定等）を提供します。

### Added
- パッケージ基盤
  - pakage 名: kabusys、バージョン: 0.1.0
  - __all__ により主要サブパッケージを公開: data, strategy, execution, monitoring

- 環境設定 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動ロード（優先順位: OS 環境変数 > .env.local > .env）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env 解析ロジック強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応
    - 行内コメントの扱い（クォートあり/なしでの違い）に対応
  - OS 環境変数の保護（読み込み時に protected セットを使用）
  - Settings クラスを提供し、主要設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV (validation: development / paper_trading / live)
    - LOG_LEVEL (validation: DEBUG/INFO/WARNING/ERROR/CRITICAL)
    - is_live / is_paper / is_dev ヘルパー

- データプラットフォーム (kabusys.data)
  - calendar_management:
    - JPX マーケットカレンダー管理用ユーティリティ（market_calendar テーブル操作）
    - 営業日判定: is_trading_day, is_sq_day
    - 営業日探索: next_trading_day, prev_trading_day, get_trading_days
    - calendar_update_job: J-Quants から差分取得・バックフィル・健全性チェック・冪等保存
    - DB 未取得時は曜日ベースのフォールバック（週末を非営業日扱い）
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.etl 経由で再エクスポート）
    - 差分更新、バックフィル、品質チェック（quality モジュールと連携）を想定した設計
    - 各種内部ユーティリティ: テーブル存在チェック、最大日付取得など
  - jquants_client を通じた外部 API 統合を想定（fetch/save 関数の利用）

- AI / NLP (kabusys.ai)
  - news_nlp:
    - raw_news / news_symbols を集約して銘柄ごとにニューステキストをまとめ、OpenAI（gpt-4o-mini / JSON mode）へバッチ送信して銘柄ごとのセンチメント（ai_score）を計算
    - タイムウィンドウ計算（JST基準 → UTC naive datetime へ変換）: calc_news_window
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/コール）、1銘柄あたり記事数・文字数の上限トリム
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ
    - レスポンスの堅牢なバリデーションとパース（JSON mode でも前後の雑テキストを復元する処理等）
    - スコアを ±1.0 にクリップ
    - DB 書き込みは部分的置換（DELETE → INSERT）で冪等性と部分失敗耐性を確保
    - API キー注入可能（api_key 引数または OPENAI_API_KEY 環境変数）
    - フェイルセーフ: API 失敗時は個別チャンクをスキップし他の処理を継続
  - regime_detector:
    - ETF 1321（日経225連動ETF）の 200 日移動平均乖離（重み 70%）とニュース由来の LLM マクロセンチメント（重み 30%）を組み合わせて、日次で市場レジーム（bull / neutral / bear）を判定
    - ma200_ratio 計算（target_date 未満のデータのみ利用しルックアヘッドバイアスを防止）
    - マクロニュース取得（ニュースウィンドウに対するキーワードフィルタリング）
    - OpenAI（gpt-4o-mini）呼び出しによる macro_sentiment 評価（JSON 出力を期待）
    - API 呼び出しのリトライ、5xx とそれ以外での扱い分け、失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）
    - 最終スコア合成と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - テスト向けに _call_openai_api をモック差し替え可能

- 研究用分析 (kabusys.research)
  - factor_research:
    - Momentum ファクター（1M/3M/6M リターン、200 日 MA 乖離）
    - Volatility / Liquidity（20 日 ATR、ATR 比率、平均売買代金、出来高比率）
    - Value ファクター（PER、ROE、raw_financials 結合）
    - DuckDB を用いた SQL ベースの実装。結果は (date, code) キーを持つ dict のリストで返却
    - データ不足時の None 扱い、ログ出力
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns: 任意ホライズン、デフォルト [1,5,21]）
    - IC（Information Coefficient）計算（calc_ic: スピアマン ρ ベースのランク相関）
    - ランク変換ユーティリティ（rank: 同順位は平均ランク）
    - 統計サマリー（factor_summary: count, mean, std, min, max, median）
    - 外部ライブラリに依存せず標準ライブラリのみで実装

- ロギング・設計方針
  - 多くのモジュールで詳細なログ（info/warning/debug）を出力
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() の直接参照を避ける設計を明示
  - DuckDB を主要なデータ格納エンジンとして利用する設計前提

### Changed
- 初回公開のため該当なし（初期実装）

### Fixed
- 初回公開のため該当なし（初期実装）

### Deprecated
- なし

### Removed
- なし

### Security
- 環境変数の取り扱いに注意:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等の機密情報が必須
  - .env 自動ロードは無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）だが、運用時は安全なシークレット管理を推奨

### Notes / Known limitations
- DuckDB および OpenAI Python SDK への依存がある。実行環境にこれらが必要。
- jquants_client と quality モジュールは外部 API クライアント/品質検査ロジックを前提としており、実装（またはモック）が必要。
- news_nlp / regime_detector は外部 LLM 呼び出しを行うため API コストとレイテンシが発生する。
- 一部の DB バインド（DuckDB の executemany の空リスト制約等）を回避するための実装が含まれている点に留意。

---

（補足）
本 CHANGELOG は提供されたコードベースの内容から推測して作成したものであり、実際のリリースノートと差異がある可能性があります。必要であれば、各モジュールの変更点や今後の予定（Unreleased セクション）を追記します。