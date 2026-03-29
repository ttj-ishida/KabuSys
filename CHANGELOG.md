# Changelog

すべての変更は Keep a Changelog のガイドラインに準拠しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 2026-03-29
初期公開リリース。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
  - パッケージレベルで主要サブパッケージを公開（data, strategy, execution, monitoring を __all__ で列挙）。

- 設定 / 環境変数管理 (`kabusys.config`)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルート判定は .git または pyproject.toml を参照）。
  - export KEY=val 形式やクォート付き値、行コメントの扱いなどを考慮した .env パーサ実装。
  - OS 環境変数を保護する protected オプションによる上書き制御、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境 等の設定プロパティを公開。各種バリデーション（KABUSYS_ENV, LOG_LEVEL）を実装。
  - 必須環境変数未設定時には明示的な ValueError を送出。

- データ基盤 / カレンダー (`kabusys.data.calendar_management`)
  - JPX マーケットカレンダー管理ロジックを実装（market_calendar テーブルの読み書き、祝日・SQ判定、営業日探索）。
  - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日ユーティリティを提供。
  - market_calendar が未取得のケースに対する曜日ベースのフォールバックを備え、一貫性を保つ設計。
  - calendar_update_job を実装し、J-Quants クライアント経由での差分取得・冪等保存（バックフィル・健全性チェック付き）を提供。

- ETLパイプライン / 補助 (`kabusys.data.pipeline`, `kabusys.data.etl`)
  - ETLResult データクラスを追加（ETL 実行結果の集約、品質問題・エラー情報の保持、辞書化ユーティリティ）。
  - DuckDB を前提とした差分取得・最終取得日解析ユーティリティを実装（テーブル存在チェック、最大日付取得など）。
  - jquants_client / quality モジュールと連携する設計（差分取得・保存・品質チェックのワークフローに対応）。

- AI ベースのニュース解析 / レジーム判定 (`kabusys.ai.news_nlp`, `kabusys.ai.regime_detector`)
  - ニュースセンチメントスコアリング（score_news）
    - raw_news / news_symbols を元に、銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）へ送信する処理を実装。
    - バッチ処理（最大20銘柄／チャンク）、記事数・文字数上限トリム、JSON Mode を用いたレスポンスバリデーションを搭載。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対するエクスポネンシャルバックオフとリトライ実装。
    - レスポンス検証（results 配列・code/score の存在チェック、数値変換、±1 でのクリップ）。DuckDB の executemany 空リスト制約への対応（空の場合は実行しない）。
    - calc_news_window による JST ベースのタイムウィンドウ計算を実装（ルックアヘッドを避けるため target_date に依存する設計）。
    - API キー注入に対応（api_key 引数または環境変数 OPENAI_API_KEY）。テスト容易性のため _call_openai_api を差し替え可能。

  - 市場レジーム判定（score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算（ルックアヘッドを防ぐため target_date 未満のデータのみ使用、データ不足時は中立扱い）。
    - マクロキーワードによる raw_news 抽出（最大 N 件）→ OpenAI によるセンチメント評価（JSON 返却期待）→ 合成スコアの算出。
    - OpenAI 呼び出しのリトライ／フォールバック（API エラーやパース失敗時は macro_sentiment=0.0）を実装。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、例外時は ROLLBACK）。

- 研究（Research）ユーティリティ (`kabusys.research`)
  - factor_research: calc_momentum, calc_value, calc_volatility を実装。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。データ不足時の None 処理。
    - Value: raw_financials からの EPS/ROE を用いた PER/ROE 計算（report_date <= target_date の最新レコードを使用）。
    - Volatility: 20 日 ATR、ATR の相対値（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - すべて DuckDB SQL を活用した実装で、外部 API へのアクセスは行わない。
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank を実装。
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）での将来リターンを LEAD を用いてまとめて取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）をランク関数を使って算出。データ不足時は None。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクで扱う安定したランク化関数。
  - kabusys.data.stats の zscore_normalize を再エクスポート（research.__init__）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数ロード時に OS 環境変数を保護する仕組みを導入（.env の上書き制御）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

### Notes / 設計上の重要事項
- ルックアヘッドバイアス対策として、各処理は datetime.today() / date.today() を直接参照せず、必ず target_date に基づくウィンドウ計算を行う設計になっています。
- OpenAI への呼び出しは JSON Mode（response_format={"type":"json_object"}）を期待していますが、パースや余計な前後テキストに対する堅牢性も考慮しています。
- OpenAI クライアント呼び出し部分はテストしやすいように内部で抽象化（_call_openai_api を patch 可能）されています。
- DuckDB（特に 0.10 系）固有の挙動（executemany に空リストを渡せない等）に対する互換対応を行っています。
- データベース書き込みは可能な限り冪等（DELETE→INSERT、トランザクション管理）を意識しています。
- プレースホルダ: __all__ に strategy, execution, monitoring が列挙されていますが、このリリースで外部発注／実行ロジック（実口座連携等）の詳細な実装は含まれていません。これらは今後のリリースで拡充予定です。

### Known issues / TODO
- OpenAI モデル名・API の変更やレート制限ポリシーの変更に伴う挙動確認・対応（モデル/レスポンス仕様の変更に脆弱）。
- strategy / execution / monitoring の具象実装（発注・ポートフォリオ管理・監視）を今後追加予定。
- jquants_client / quality モジュールとの結合部分は外部依存のため、API 変更に応じたテストが必要。

--  
（以上）