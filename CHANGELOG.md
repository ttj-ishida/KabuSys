# Changelog

すべての付目立つ変更点を記録します。本書は Keep a Changelog の形式に準拠しています。  
各バージョンの項目は主にソースコードの実装・ドキュメント文字列から推測して記載しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-28
初回公開リリース。本リリースでは日本株自動売買システム「KabuSys」の基盤機能群（データ取得/ETL、マーケットカレンダー管理、リサーチ用ファクター計算、ニュース/マクロのAIスコアリング、設定管理など）を提供します。

### Added
- パッケージ化
  - パッケージトップに version と公開モジュールを定義（kabusys.__version__ = "0.1.0"）。
  - __all__ に ["data", "strategy", "execution", "monitoring"] を公開。

- 環境設定 / config
  - settings オブジェクト（Settings クラス）を導入し、環境変数経由でアプリ設定を集約（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パスなど）。
  - 自動 .env 読み込み機能を実装:
    - プロジェクトルートの探索（.git または pyproject.toml を基準）により .env / .env.local を自動ロード。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - 高度な .env パース機能:
    - export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等に対応。
  - 必須環境変数チェック（_require）と設定値の妥当性検証（KABUSYS_ENV の有効値チェック、LOG_LEVEL の検証など）。

- AI モジュール（kabusys.ai）
  - news_nlp.score_news:
    - raw_news / news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出。
    - タイムウィンドウ定義（JST 前日 15:00 〜 当日 08:30 に対応。内部は UTC naive datetime を返す calc_news_window を提供）。
    - チャンク処理（デフォルト 20 銘柄/チャンク）、記事数・文字数のトリム、JSON Mode レスポンスのバリデーション、スコアの ±1.0 クリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - DuckDB への冪等書き込み（DELETE → INSERT、トランザクション管理、ROLLBACK 保護）。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - マクロ抽出用キーワード群を使用して raw_news からタイトルを取得、OpenAI 呼び出し（JSON モード）で macro_sentiment を算出。
    - API エラー時は macro_sentiment=0.0 のフェイルセーフ。
    - 判定結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。HTTP 5xx 等はリトライロジックあり。

- Data / ETL（kabusys.data）
  - pipeline.ETLResult dataclass を提供し、ETL 実行結果（取得件数・保存件数・品質問題リスト・エラー）を構造化して返却。
  - ETL パイプラインのユーティリティ実装（差分取得のための最大日付取得等）。
  - etl モジュールで ETLResult を再エクスポート。
  - jquants_client 経由のデータ取得・保存（コード内参照）を想定した設計。

- カレンダー管理（kabusys.data.calendar_management）
  - market_calendar を基に営業日判定ユーティリティを提供:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
  - DB にデータがない場合は曜日ベースでフォールバック（土日非営業日）。
  - calendar_update_job: J-Quants API からカレンダーの差分取得・保存を行う夜間バッチジョブ。バックフィル（直近数日再取得）と健全性チェック（将来日付の異常検出）を実装。

- Research（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を算出（EPS=0/欠損時は None）。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）を一括取得する汎用実装。
    - calc_ic: スピアマンランク相関（IC）を計算するユーティリティ。NULL/非有限値除外、サンプル数不足時は None を返す。
    - rank, factor_summary: ランク付け（同順位は平均ランク）と基本統計量算出を実装。
  - data.stats.zscore_normalize を re-export。

- DuckDB を前提とした実装
  - 多数の処理で DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り SQL と Python を組み合わせて計算/集約を行う設計。
  - トランザクション管理、executemany の制約回避（空リスト回避）等の互換性対策を実装。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- OpenAI API キー（OPENAI_API_KEY）や各種トークン類は環境変数で管理する設計。必須項目は Settings のプロパティでチェックされ、未設定時は ValueError を投げる。

### Notable design decisions / Limitations
- ルックアヘッドバイアス防止のため、全ての日付参照処理で datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す）。
- AI 呼び出しで失敗が発生しても処理を継続するフェイルセーフ（多くの場面でデフォルトスコア 0.0 を使用）を採用。
- news_nlp の現フェーズでは sentiment_score と ai_score が同値で書き込まれる旨の実装注記あり。
- calc_value では PBR や配当利回りは未実装。
- JSON レスポンスの取り扱いでは、厳密な JSON 以外のノイズ（前後のテキスト）にも対応する復元ロジックを含む。

### Migration / Upgrade notes
- 環境変数と .env の取り扱いに関して既存ワークフローがある場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して自動ロードを抑制可能。
- DuckDB のバージョン互換性に伴い executemany に空リストを渡さない対策を行っているため、DB 周りの挙動に依存するコードは意図的な実装になっている。

---

参照: 各モジュールの docstring / 実装に基づき要点を抽出して記載しています。実際のリリースノート作成時にはテスト結果や API 仕様変更等の追記を推奨します。