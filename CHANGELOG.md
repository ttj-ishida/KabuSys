Keep a Changelog に準拠した CHANGELOG.md（日本語）
=============================================

このファイルは kabusys パッケージの変更履歴を記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

（現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-04
-------------------

初回公開リリース。以下の主要機能・モジュールを実装しています。

Added
- パッケージ基盤
  - パッケージバージョンを追加: kabusys.__version__ == "0.1.0"。
  - モジュール公開: data, strategy, execution, monitoring を __all__ に追加。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートは __file__ の親階層から .git または pyproject.toml を探索して特定（CWD非依存）。
    - 読み込み順序: OS 環境変数 > .env.local（上書き） > .env（未設定のみ）。
    - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサーを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理、インラインコメント取り扱いをサポート）。
  - Settings クラスを追加し、型化されたプロパティで各種設定を提供（J-Quants / kabu / LINE / DB パス / 監視閾値 / 環境 / ログレベル等）。
  - 必須環境変数が未設定の際に ValueError を投げる _require ロジックを導入。
  - 設定値に対する入力検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news, news_symbols を元に銘柄別ニュースセンチメントを OpenAI（gpt-4o-mini）に問い合わせて ai_scores テーブルへ保存する score_news を実装。
  - 処理の特徴:
    - JST基準のニュース時間ウィンドウ計算機能（calc_news_window）。
    - 銘柄ごとに最新の最大記事数・最大文字数でトリムしてまとめるロジック。
    - バッチ処理（1回の API 呼び出しで最大 20 銘柄）・チャンク処理。
    - JSON mode を利用したレスポンス想定、レスポンスの堅牢なバリデーションと部分成功時の保護（取得した銘柄のみ置換）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - スコアを ±1.0 にクリップ。
    - API 呼び出し箇所をテスト容易に差し替え可能（_call_openai_api を patch 可能）。
  - エラー処理方針: API エラーやパース失敗は例外を投げずフェイルセーフにフォールバック（該当チャンクはスキップ）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
  - 処理の特徴:
    - ma200 比率計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）。
    - マクロキーワードで raw_news タイトルを抽出して LLM に投げるロジック。
    - OpenAI 呼び出しは独自実装で、リトライ・エラーハンドリングを備える。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実行。
    - API 失敗やレスポンスパース失敗時は macro_sentiment=0.0 を採用して継続（フェイルセーフ）。

- データ基盤（kabusys.data）
  - ETL パイプラインのインターフェースを公開（ETLResult を再エクスポート）。
  - pipeline モジュール（kabusys.data.pipeline）:
    - ETLResult dataclass を実装（取得数・保存数・品質問題・エラーの集約、辞書化 to_dict を提供）。
    - 差分更新・バックフィル・品質チェックに関する設計方針とユーティリティを実装（テーブル存在確認・最大日付取得のための内部ユーティリティ）。
    - ETL のデフォルトバックフィル日数等の定数を定義。
  - カレンダー管理（kabusys.data.calendar_management）:
    - JPX カレンダーを管理し、営業日判定のユーティリティ関数を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar がない場合は曜日ベース（土日除去）でフォールバックする一貫した挙動を採用。
    - 夜間バッチ更新 job（calendar_update_job）を実装。J-Quants クライアント経由で差分取得・バックフィル・健全性チェック・保存を行う。
    - next/prev_trading_day は探索上限（日数）を設定して無限ループを防止。

- リサーチ機能（kabusys.research）
  - factor_research:
    - モメンタム（1/3/6ヶ月リターン、200日 MA 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER, ROE）等の計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上で SQL を用いて効率的に計算する設計。
    - データ不足時の None 扱いなど堅牢性を確保。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等外部依存を持たず標準ライブラリで実装。
  - data.stats の zscore_normalize を再エクスポートするインターフェースを追加。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- セキュリティ関連の変更はなし。ただし OpenAI API キーや各種秘密情報は環境変数での提供を想定。Settings は必須キー未設定時に明示的にエラーを出すため、実運用では環境変数管理に注意してください。

注意事項（使用上の重要ポイント）
- 必須の環境変数:
  - JQUANTS_REFRESH_TOKEN（Settings.jquants_refresh_token）
  - KABU_API_PASSWORD（Settings.kabu_api_password）
  - OpenAI API キーは score_news / score_regime の api_key 引数、または環境変数 OPENAI_API_KEY に設定する必要があります。未設定の場合は ValueError が発生します。
- 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト用途など）。
- DuckDB の想定スキーマ／テーブル:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等を参照する実装が含まれます。これらのテーブル構造は本リリースの SQL クエリ実装に依存します。
- LLM 呼び出しの設計:
  - レート制限や一時的な障害に対してリトライ＋バックオフを行いますが、最終的に失敗したチャンクはスキップし、他の処理は継続します（フェイルセーフ）。
  - レスポンスの JSON パースや形式チェックは厳格に行い、不正なレスポンスはスキップされます。
- ルックアヘッドバイアス対策:
  - score_news / score_regime 等は内部で datetime.today() を参照せず、必ず外部から与えられた target_date を基準に処理します。
- DB 書き込みは可能な限り冪等（DELETE→INSERT、ON CONFLICT方針など）を採用し、部分失敗時に既存データを不必要に消さない工夫をしています。
- 既知の制限:
  - raw_financials からの PBR や配当利回りはこのバージョンでは未実装（注記あり）。
  - DuckDB の executemany に対して空リストバインドが不可なバージョン向けに保護コードを入れています。

互換性（Breaking Changes）
- 初回リリースのため互換性に関する破壊的変更はありません。ただし今後のバージョンで DB スキーマや環境変数名を変更する可能性があります。

将来の改善候補（TODO）
- news_nlp / regime_detector の LLM プロンプト改善とテストカバレッジ強化。
- ETL の品質チェック結果に基づく自動アクション（アラートやリトライ戦略）。
- ファクター計算のパフォーマンス最適化および追加ファクター（PBR・配当利回りなど）。

署名
- 本 CHANGELOG はソースコードから実装内容を推測して作成しています。実際のドキュメントやリリースノートは必要に応じて補足してください。