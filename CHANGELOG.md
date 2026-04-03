# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に従って記載しています。  
フォーマット: カテゴリ (Added / Changed / Fixed / Security / …) に分け、各リリースごとに要約を記載しています。

注記:
- この履歴はソースコードから推測して作成した初期リリース向けの要約です。
- 実行には DuckDB、OpenAI クライアント等の外部依存が必要です。環境変数で各種設定を行います（README や .env.example を参照してください）。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-03
初回公開リリース。日本株自動売買／データ基盤・研究用ユーティリティの基礎機能を実装。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョンを __version__ = "0.1.0" として定義。
  - 公開サブパッケージ: data, research, ai, execution, strategy, monitoring の初期エクスポート（__all__ に含む）。

- 設定・環境管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする仕組みを追加。
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを実装（コメント、export プレフィックス、クォートとエスケープ処理、インラインコメントの扱い等に対応）。
  - Settings クラスを実装し、J-Quants / kabuAPI / LINE / DB パス / 監視設定 / システム設定（KABUSYS_ENV, LOG_LEVEL）などをプロパティとして提供。
  - 必須環境変数取得用の _require() を提供（未設定時に ValueError を送出）。
  - デフォルト値や型変換（Path、float、bool など）を含む設定取得を実装。

- データ基盤: ETL とカレンダー管理 (kabusys.data)
  - ETL:
    - pipeline モジュールに ETLResult データクラスを追加。ETL の取得数・保存数、品質チェック問題、エラー一覧を保持できる。
    - ETL の差分更新・バックフィル概念、品質チェックとの連携方針を実装方針として定義（実際の jquants_client 呼び出しは jquants_client 側で実装）。
    - data.etl で ETLResult を再エクスポート。
  - カレンダー管理:
    - market_calendar テーブルを基に営業日判定ロジックを実装: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - DB にデータがない場合は曜日ベース（平日のみ営業日）でフォールバックする一貫した挙動を採用。
    - calendar_update_job を提供し、J-Quants からの差分取得 → DB へ冪等保存（ON CONFLICT 相当）を行う。バックフィルや健全性チェック（将来日付の異常検出）を実装。
  - DuckDB を前提としたデータ操作ユーティリティを提供（テーブル存在確認、日付変換など）。

- 研究（Research）モジュール (kabusys.research)
  - ファクター計算:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離 (ma200_dev) を計算。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: EPS/ROE に基づく PER, ROE を計算（raw_financials に依存）。
  - 特徴量探索:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得する実装。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - rank, factor_summary: ランク化ユーティリティおよび基本統計量（count/mean/std/min/max/median）を提供。
  - zscore_normalize を kabusys.data.stats から re-export。

- AI（NLP）モジュール (kabusys.ai)
  - news_nlp:
    - raw_news と news_symbols を集約して銘柄ごとの記事を構成し、OpenAI（gpt-4o-mini）で銘柄別センチメントを取得して ai_scores テーブルへ書き込む実装。
    - プロンプト設計（JSON Mode を要求）、レスポンスのバリデーション（JSON 抽出、results リスト、code と score の検証）、スコアクリップ（±1.0）を実装。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/回）、1銘柄あたりの記事数/文字数上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）でトークン肥大化に対処。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフによるリトライを実装。その他エラーはフェイルセーフにより個別チャンクをスキップして処理継続。
    - テスト容易性のため _call_openai_api を patch で差し替え可能な実装。
  - regime_detector:
    - ETF 1321（TOPIX 日経225 連動 ETF 相当）の直近 200 日 MA 乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成し、日次で market_regime テーブルに書き込む機能を実装。
    - prices_daily からの MA 算出（ルックアヘッド防止のため target_date 未満のデータのみ使用）と、news_nlp の calc_news_window を用いた記事抽出、OpenAI によるマクロセンチメント推定を組み合わせる。
    - LLM 呼び出しは独立実装でモジュール間の結合を抑制。API エラー時は macro_sentiment=0.0 として続行（フェイルセーフ）。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。

### Changed
- （初回リリースのため過去バージョンからの変更はなし）

### Fixed
- （初回リリースのため既知のバグ修正履歴なし）

### Security / Notes
- OpenAI API キーは引数で注入可能（api_key）か、環境変数 OPENAI_API_KEY を利用。未設定時は ValueError を投げる箇所があるためデプロイ時に必須。
- 環境変数に機微情報（API キー等）をロードする挙動は .env/.env.local を通じて行われる。OS 環境変数を保護するために .env 読み込みでは既存の OS 環境変数を上書きしない（.env.local は上書き可）。
- DuckDB を用いる設計のため、DuckDB バージョン差異（executemany と空リストの扱い等）に配慮した実装になっている。
- ルックアヘッドバイアス防止: 日付参照に datetime.today()/date.today() を直接使用しない設計（target_date を明示的に受け取る）。

### Implementation notes / テスト容易性
- OpenAI 呼び出しは _call_openai_api を介して実行され、ユニットテスト時はパッチ差し替えで API をモック可能。
- calendar_update_job / pipeline 等は例外を捕捉してログを出力し、失敗時は部分的に 0 を返す（夜間バッチや ETL の堅牢性を重視）。
- DB 書き込み部分はトランザクション (BEGIN/COMMIT/ROLLBACK) を用いた冪等処理を行う実装がされている。

---

今後のリリース案（想定）
- AI レスポンスのマルチモデル対応やトークン使用量計測の追加
- 実運用向けのモニタリング/アラート機能強化（LINE 通知連携の利用例等）
- ETL のスケジューリング / 並列化 / 差分抽出の最適化

もし特定ファイルや機能ごとにより詳細な変更履歴（行レベルの差分や設計上の注意点）をご希望であれば、その旨を教えてください。必要に応じてセクションを分けて詳述します。