Changelog
=========
すべての注目すべき変更を記録します。  
このファイルは「Keep a Changelog」の形式に従っています。  

[Unreleased]: https://example.com/compare/HEAD...v0.1.0
[0.1.0]: https://example.com/releases/tag/v0.1.0

## [0.1.0] - 2026-04-02
初回公開リリース。日本株自動売買／データ基盤のコアライブラリを提供します。以下はコードベースから推測してまとめた主要な追加機能・設計方針・重要な挙動です。

### Added
- パッケージ基礎
  - パッケージバージョンを定義（kabusys.__version__ = "0.1.0"）し、主要サブパッケージ（data, strategy, execution, monitoring）を __all__ で公開。

- 環境設定管理 (kabusys.config)
  - .env ファイルと環境変数の自動ロード機能を実装（OS 環境変数 > .env.local > .env の優先順）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサーを強化（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント考慮）。
  - _load_env_file による既存環境変数保護（protected set）と override オプション。
  - Settings クラスでアプリ設定をプロパティとして提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, DUCKDB_PATH 等）。KABUSYS_ENV / LOG_LEVEL のバリデーション実装。
  - デフォルト値（KABU_API_BASE_URL, データベースパス、監視閾値等）を提供。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング（news_nlp.score_news）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へバッチ送信。
    - JST 時間ウィンドウを厳密に定義（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して比較）。
    - チャンク処理（最大 20 銘柄/チャンク）、1 銘柄あたりの記事数・文字数上限（トリム）を実装。
    - JSON Mode を利用しレスポンスをバリデーション、スコアを ±1.0 にクリップ。
    - 取得成功分のみ ai_scores テーブルを置換書き込み（DELETE → INSERT）して部分失敗時の既存データ保護。
    - API エラー（429・ネットワーク断・タイムアウト・5xx）に対する指数バックオフリトライ実装。非リトライ対象エラーはスキップして継続。
    - テスト用に _call_openai_api を差し替え可能（unittest.mock.patch で差替え想定）。

  - 市場レジーム判定（ai.regime_detector.score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - マクロニュース抽出（キーワードリスト）、LLM（gpt-4o-mini）呼び出し、失敗時は macro_sentiment=0.0 のフォールバック。
    - スコア合成（clip）および市場レジームテーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - OpenAI 呼び出しでのリトライ・エラーハンドリングを詳細に実装。

- データプラットフォーム (kabusys.data)
  - カレンダー管理（data.calendar_management）
    - market_calendar テーブルを基に営業日判定、next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等を提供。
    - DB にデータが無い場合は曜日ベースでフォールバック（週末を非営業日扱い）。DB 登録あり→DB優先、未登録日は曜日フォールバックの一貫処理。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィル日数と健全性チェックを実装）。
    - 探索上限（_MAX_SEARCH_DAYS）により無限ループを防止。

  - ETL パイプライン（data.pipeline, data.etl）
    - ETLResult データクラスを公開（ターゲット日、取得/保存件数、品質問題、エラー集約、has_errors / has_quality_errors, to_dict）。
    - 差分更新・バックフィル・品質チェック（quality モジュール経由）を想定した設計。J-Quants クライアント（jquants_client）を経由して保存処理を行う想定。

- 研究モジュール (kabusys.research)
  - factor_research: calc_momentum, calc_volatility, calc_value を提供。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - Volatility: 20 日 ATR（true_range の NULL 伝播制御）、相対 ATR、20 日平均売買代金、出来高比率等。
    - Value: raw_financials から最新財務を結合して PER/ROE を算出（EPS 0/欠損は None）。
    - 全て DuckDB の prices_daily / raw_financials テーブルを参照、関数は (date, code) キーの辞書リストを返却。
  - feature_exploration: calc_forward_returns, calc_ic, rank, factor_summary を提供。
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で計算（リード関数を利用）。
    - calc_ic: スピアマンランク相関（ランクは平均ランクで ties は平均化）、有効レコード < 3 は None。
    - factor_summary: count/mean/std/min/max/median を None を除いて計算。

### Changed
- 設計上の方針明確化（コード内 docstring）
  - ほとんどの分析／スコアリング処理で datetime.today()/date.today() を直接参照せず、target_date を引数で受け取ることでルックアヘッドバイアスを防止する設計となっている点を明記。
  - DuckDB の executemany に関する互換性考慮（空パラメータの扱い）を実装・注記。

### Fixed / Robustness
- AI API 呼び出しでの堅牢性向上
  - JSON パース失敗や予期しないレスポンスに対して安全にフォールバック（警告ログ出力、空結果・中立スコアを使用）。
  - OpenAI API 呼び出しの異常系（RateLimit, APIConnectionError, APITimeoutError, APIError）の扱いを詳細に分岐してリトライ判定。

- DB 書き込みの冪等化と部分失敗保護
  - ai_scores や market_regime 等のテーブル更新は、対象コード/日付を限定して DELETE→INSERT の置換を書き込み、部分失敗で既存データを破壊しない設計。

### Notes / Implementation details
- OpenAI クライアント使用箇所は OpenAI(api_key=...) を直接生成。テスト時に _call_openai_api を patch して外部通信をモック可能。
- news_nlp と regime_detector はそれぞれ独立した _call_openai_api 実装を持ち、モジュール間で private 関数を共有しない方針。
- 一部実装は DuckDB の型やバインド仕様に依存（例: list をバインドする場合の互換性注意）。
- calendar_update_job と ETL フローは jquants_client モジュール（外部 API wrapper）に依存しており、fetch/save の失敗時は例外捕捉して 0 を返却するフェイルセーフ設計。

### Deprecated
- なし（初回公開）

### Removed
- なし（初回公開）

### Security
- なしの指摘。ただし環境変数や API キー（OpenAI, J-Quants 等）を必要とするため、運用時は秘密情報の取り扱いに注意してください（.env/.env.local の適切な管理を推奨）。

---

注: この CHANGELOG は提供されたソースコードの内容・docstring から推測して作成しています。実際の変更履歴やリリースノートとして公開する場合は、開発履歴やコミットメッセージと突合せの上、追記・修正してください。