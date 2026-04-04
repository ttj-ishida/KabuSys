# Changelog

すべての重大な変更点をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

全般:
- このプロジェクトは duckdb と OpenAI（openai SDK）に依存するコンポーネントを含みます。
- ライブラリ設計上の共通方針として、ルックアヘッドバイアス回避のため datetime.today()/date.today() を直接参照しない実装、DuckDB への冪等書き込み、API 呼び出しの堅牢なリトライ/フォールバック戦略を採用しています。
- テスト容易性のために OpenAI 呼び出し箇所は差し替え可能（モジュール内の _call_openai_api を unittest.mock で patch）になっています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-04
最初の公開リリース。

### Added
- パッケージ基礎
  - kabusys パッケージ初期化（version=0.1.0）。__all__ に主要サブパッケージを公開。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を追加。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト向け）。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理）。
  - protected（OS 環境変数）を尊重する上書き制御、override フラグ対応。
  - Settings クラスを提供し、J-Quants / kabu / LINE / DB / 監視 / システム関連の設定プロパティを公開。
    - 必須環境変数のチェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
    - デフォルト値を持つ設定（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等）。
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値セットを明示）。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols からニュースを収集し、銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - window 計算（JST 基準の前日 15:00 ～ 当日 08:30 の UTC 変換）を calc_news_window として実装。
    - バッチサイズ、記事数・文字数のトリム制御、JSON Mode のレスポンスバリデーション、スコアの ±1 クリップ。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。失敗時はスキップして継続するフェイルセーフ設計。
    - DuckDB への書き込みは「部分失敗時に既存データを保護する」戦略（対象コードのみ DELETE → INSERT）を採用。
    - DuckDB 0.10 の executemany に関する空リスト制約を考慮した処理保護。
    - 公開 API: score_news(conn, target_date, api_key=None) — 書き込んだ銘柄数を返す。
  - レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロセンチメント（LLM、重み 30%）を合成して日次の市場レジームを判定（'bull' / 'neutral' / 'bear'）。
    - LLM 呼び出しは gpt-4o-mini、JSON レスポンスを想定。API 障害時は macro_sentiment=0.0 にフォールバック。
    - ma200_ratio 計算は target_date 未満のデータのみを使用（ルックアヘッド回避）。
    - 判定結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 公開 API: score_regime(conn, target_date, api_key=None) — 成功時 1 を返す。
  - テスト向けフック: OpenAI 呼び出しを差し替え可能にしてユニットテストを容易に。

- 研究（research）関連（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA乖離率）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20）, atr_pct, avg_turnover, volume_ratio を計算。NULL/データ不足を適切に扱う。
    - calc_value: raw_financials と prices_daily を組み合わせて PER・ROE を算出。EPS が 0 または欠損の場合は PER は None。
    - すべて DuckDB + SQL ベースで計算し、外部 API にはアクセスしない設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを営業日ベースで計算。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算（有効レコードが 3 未満なら None）。
    - rank, factor_summary: ランク付け（同順位は平均ランク）と基本統計量を計算するユーティリティを実装。
    - pandas 等の外部ライブラリに依存しない純標準ライブラリ実装。

- データプラットフォーム（kabusys.data）
  - calendar_management
    - market_calendar テーブルを利用した営業日判定ロジックを提供（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）。
    - market_calendar 未取得時は曜日ベース（土日除外）でフォールバック。
    - calendar_update_job: J-Quants API（jquants_client）から差分取得し market_calendar テーブルへ冪等保存。バックフィル・健全性チェックを実装。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETL の結果を表す ETLResult データクラスを追加（取得数・保存数・品質問題・エラーメッセージ等を保持）。
    - 差分更新・バックフィル・品質チェックの方針・ユーティリティを備えた ETL 基盤（jquants_client, quality モジュールとの連携想定）。
  - etl モジュールは ETLResult を再エクスポート。

### Changed
- 初回リリースのため該当なし（以降のリリースで追記予定）。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 環境変数の取り扱いに関する保護設計（既存 OS 環境変数の保護、パスワード等は必須チェック）を実装。

### 注意／移行メモ
- 必須環境変数
  - OPENAI_API_KEY（AI モジュール利用時）、JQUANTS_REFRESH_TOKEN（J-Quants API 利用時）、KABU_API_PASSWORD（kabu API 利用時）などが必要です。Settings クラスで未設定時は ValueError が発生します。
- 自動 .env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストで便利です）。
- DuckDB への書き込みは冪等性を重視していますが、既存の DB スキーマ（ai_scores, market_regime, prices_daily, raw_news, raw_financials, news_symbols, market_calendar 等）が必要です。
- OpenAI 呼び出しでは JSON Mode を想定しています。レスポンス整形の違いに備え、若干の復元ロジック（文字列中の最外側 {} を抽出）を加えていますが、API レスポンスの安定化が望ましいです。

---
今後のリリースでは運用上の改善（エラー観測性の向上、非同期処理、追加ファクター等）や API クライアント抽象化を予定しています。問題・要望があれば Issue を作成してください。