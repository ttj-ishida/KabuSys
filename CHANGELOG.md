# Changelog

すべての変更は Keep a Changelog の形式に従います。  
シンボリックな初期リリース情報は、コードベースから推測して作成しています。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-28

初回リリース — 日本株自動売買 / データ処理 / リサーチ基盤の骨格を提供します。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）。公開モジュール: data, strategy, execution, monitoring。
- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local 自動読み込み機能。プロジェクトルートの特定は .git または pyproject.toml を基準とし、CWD に依存しない探索を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化機能。
  - .env パーサを実装:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなし行でのインラインコメント（#）の扱い（直前が空白/タブのときのみコメントと判断）
  - _load_env_file にて OS 環境変数を保護する protected キーセットを導入（.env.local は既存の OS 環境変数を上書きしない）。
  - Settings クラスを追加し、J-Quants / kabuステーション / Slack / DB パス / システム設定（KABUSYS_ENV, LOG_LEVEL）のプロパティ経由取得とバリデーションを実装。
    - DUCKDB_PATH / SQLITE_PATH のデフォルトを設定（data/kabusys.duckdb, data/monitoring.db）。
    - KABUSYS_ENV 値検査（development, paper_trading, live）およびログレベル検査を実装。
- AI / ニュースセンチメント (kabusys.ai.news_nlp)
  - raw_news / news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）へ JSON Mode で問い合わせて銘柄ごとのセンチメント（-1.0〜1.0）を算出する score_news を実装。
  - ウィンドウ定義（JST 前日15:00〜当日08:30 → UTC換算）を calc_news_window で提供。
  - バッチ処理（最大20銘柄/チャンク）、1銘柄あたりの記事上限（件数・文字数トリム）を実装。
  - API 呼び出しでの 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライを実装。その他エラーはスキップしてフェイルセーフを保持。
  - レスポンスの厳密バリデーションと数値クリッピング（±1.0）。JSON に余計な前後テキストが混ざるケースへの復元ロジックも実装。
  - DuckDB への書き込みは部分失敗時の既存スコア保護のため、対象コードのみ DELETE → INSERT を行う冪等的な更新を実装（executemany の空リスト制約に配慮）。
  - テスト用に内部の OpenAI 呼び出し関数はモジュールローカルで容易にパッチ可能（unittest.mock.patch を想定）。
- AI / 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
  - prices_daily からの MA200 計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）と、raw_news からマクロキーワードでのタイトル抽出を実装。
  - OpenAI 呼び出し（gpt-4o-mini）での JSON パース、安全なリトライ、API 障害時のフェイルセーフ（macro_sentiment=0.0）を実装。
  - 計算結果は market_regime テーブルに冪等的に書き込まれる（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時はロールバックし例外を伝播。
- リサーチ機能 (kabusys.research)
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を prices_daily から計算。
    - calc_volatility: 20日 ATR（atr_20）・相対ATR（atr_pct）・20日平均売買代金・出来高比率を計算。
    - calc_value: raw_financials の最新財務データと価格を組み合わせて PER / ROE を計算。
    - DuckDB を主体とした SQL ベース実装で、外部 API に依存しない設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンに対する将来リターン（デフォルト [1,5,21]）を一括 SQL で取得。
    - calc_ic: スピアマンランク相関（IC）を実装。レコード不足（<3）で None を返す。
    - rank: 同順位は平均ランクで扱うランク関数（丸めによる ties 対策あり）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを実装。
- データ基盤 (kabusys.data)
  - calendar_management:
    - market_calendar を用いた営業日判定ロジック（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - market_calendar 未取得時は曜日ベースのフォールバック（週末除外）を採用。
    - calendar_update_job: J-Quants API から差分取得 → jq.save_market_calendar により冪等保存、バックフィル／健全性チェック実装。
  - pipeline / etl:
    - ETLResult データクラスを実装（取得数・保存数・品質問題・エラー収集など）。
    - _get_max_date 等のユーティリティを実装し差分更新ロジックの下地を提供。
  - etl モジュールで ETLResult を再エクスポート。
  - jquants_client（参照されるがこの差分では未記載）経由での取得/保存を想定した抽象化を行う。
- その他
  - ログメッセージを豊富に追加（情報 / 警告 / 例外ログ）し、運用上の可観測性を向上。
  - 全体設計方針として「datetime.today()/date.today() を直接参照しない」ことを明記し、ルックアヘッドバイアスを防止。

### 変更 (Changed)
- 初版リリースのため、"変更" は特になし（新規実装が主体）。

### 修正 (Fixed)
- 初版リリースのため、"修正" は特になし。

### 互換性（Breaking Changes）
- 初版リリースのため既知の破壊的変更はありません。ただし今後の API 設計でデータベーススキーマや環境変数名を変更する可能性があります。

### 注意点 / 実装上の設計判断
- OpenAI 呼び出しは gpt-4o-mini をデフォルトに設定。API キーは api_key 引数または環境変数 OPENAI_API_KEY で供給する必要があります。未指定時は ValueError を送出します。
- API 障害時はフェイルセーフによりスコアを 0.0 にフォールバック（例外を上げずに継続）する設計を多く採用しています（運用継続性重視）。
- DuckDB の executemany に関する互換性問題（空リスト不可）に対応するため、空時は処理をスキップするガードを挿入しています。
- テスト容易性のため、内部の API 呼び出し関数（_kabusys.ai.*._call_openai_api）はパッチ可能なローカル実装になっています。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの実装拡充（本リリースではエントリポイントのみ公開）。
- jquants_client の実装例・モック提供、CI テスト・ユニットテスト整備。
- モデル（LLM）入出力のさらなる堅牢化とロギング／監査出力の改善。