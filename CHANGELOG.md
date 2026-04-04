# Changelog

すべての変更は Keep a Changelog の形式に準拠します。慣例に従いバージョン番号 / 日付 / セクション（Added / Changed / Fixed / Removed / Security）で記載しています。

## [0.1.0] - 2026-04-04

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ公開情報:
    - src/kabusys/__init__.py: __version__="0.1.0", パブリックモジュール一覧のエクスポート（data, strategy, execution, monitoring）。
- 環境設定管理
  - src/kabusys/config.py:
    - .env ファイルと環境変数の読み込み自動化（プロジェクトルート検出: .git または pyproject.toml を起点に探索）。
    - .env/.env.local の優先度管理（OS 環境変数 > .env.local > .env）、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
    - .env 行パーサの実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
    - 環境変数必須チェック用の _require と Settings クラスを提供（各種 API トークン、DB パス、監視閾値、ログレベル・環境モードの検証を含む）。
    - 設定プロパティにバリデーション（KABUSYS_ENV / LOG_LEVEL の許容値チェック等）を実装。
- AI（自然言語処理）機能
  - src/kabusys/ai/news_nlp.py:
    - ニュース記事のセンチメントを LLM（gpt-4o-mini）で評価し、ai_scores テーブルへ書き込むバッチ処理を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）と記事集約（news_symbols JOIN）を実装。
    - 1 銘柄あたりの記事数／文字数上限（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）でトリム。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）・JSON Mode を利用した堅牢な API 呼び出しとレスポンス検証。
    - レート制限・ネットワーク断・タイムアウト・5xx に対するリトライ（指数バックオフ）とフェイルセーフ（失敗時はスキップして継続）。
    - レスポンス検証ロジック（JSON 抽出、results 配列の検証、コード正規化、数値変換、スコアの ±1.0 クリップ）。
    - テスト容易化のため _call_openai_api を patch 可能に設計。
  - src/kabusys/ai/regime_detector.py:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照し、calc_news_window を利用したウィンドウ取得、_calc_ma200_ratio、_fetch_macro_news、_score_macro（LLM 呼び出し）を実装。
    - LLM 呼び出しは gpt-4o-mini の JSON Mode を使用。API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフを採用。
    - 計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
    - API キーを引数注入可能にし、未指定時は環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出。
- データプラットフォーム / ETL
  - src/kabusys/data/pipeline.py:
    - ETLResult データクラスの実装（ETL 実行結果の集約、品質チェック結果・エラー一覧保持、辞書変換ユーティリティ）。
    - 差分更新の方針、バックフィル、品質チェックとの連携を想定した設計。
  - src/kabusys/data/etl.py:
    - pipeline.ETLResult の公開再エクスポート。
  - src/kabusys/data/calendar_management.py:
    - JPX マーケットカレンダーの管理と夜間バッチ更新処理（calendar_update_job）を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日判定ユーティリティを提供。
    - market_calendar が未取得のケースを考慮した曜日ベースのフォールバック、DB 登録値の優先利用、最大探索日数制約（_MAX_SEARCH_DAYS）などの安全設計。
    - J-Quants クライアント（jquants_client）を用いた差分取得と保存処理の呼び出し、バックフィル・健全性チェックを実装。
- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py:
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER・ROE）を DuckDB の prices_daily / raw_financials を用いて計算する関数群（calc_momentum, calc_volatility, calc_value）を実装。
    - データ不足時は None を返す設計。SQL ウィンドウ関数を活用した実装。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応、最大ホライズン検証）。
    - ランク相関による IC（calc_ic）およびランク変換ユーティリティ（rank）。
    - ファクター統計要約（factor_summary）を標準ライブラリのみで実装。
  - src/kabusys/research/__init__.py:
    - 主要関数群の再エクスポートを提供（calc_momentum, calc_value, calc_volatility, zscore_normalize 等）。
- データモジュールのその他
  - DuckDB を想定した設計（DuckDBPyConnection 型注釈、executemany の空リスト回避等の互換性対処）。
  - ロギングメッセージを各処理に追加し、運用での観察を容易に。

### Changed
- 初回リリースのため変更履歴なし（新規追加のみ）。

### Fixed
- 初回リリースのため修正履歴なし。

### Security
- 初回リリースのためセキュリティ関連の既知の脆弱性はなし。ただし API キーや機密情報は Settings 経由で環境変数として管理することを想定。

---

注意事項 / 実装上の重要点（運用者向け）
- OpenAI（LLM）呼び出しは外部 API に依存するため、API キー管理・レート制限に注意してください。各 AI モジュールは失敗時にフェイルセーフ（スコア 0.0 やスキップ）するよう設計されていますが、継続的なモニタリングを推奨します。
- .env 自動読み込みはプロジェクトルート検出に依存します。パッケージ配布後やテスト時に自動ロードを抑止する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のバージョン差異（executemany の挙動など）に配慮した実装が行われていますが、実際の運用環境での互換性確認を行ってください。
- calendar_update_job 等のバッチは外部 API（J-Quants）の戻り値やネットワークエラーに依存します。失敗時はログに例外が記録され 0 を返すため、監査ログや再実行ロジックを運用側で用意することを推奨します。