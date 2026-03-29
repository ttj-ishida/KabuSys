# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

## [0.1.0] - 2026-03-29

初期リリース。日本株のデータ取得・ETL、マーケットカレンダー管理、ファクター計算、ニュース/NLP を用いた AI スコアリング、ならびに市場レジーム判定を行う基盤ライブラリを提供します。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報とエクスポートを定義 (kabusys.__init__).
  - __version__ を "0.1.0" に設定。

- 環境設定 (kabusys.config)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - 高度な .env パーサを実装:
    - コメント・空行スキップ、export プレフィックス対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理。
    - クォートなしでのインラインコメント処理（直前が空白/タブの場合）。
  - 自動読み込みの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 環境変数保護機構（OS 環境変数を上書きしないための protected セット）。
  - Settings クラスを追加し、アプリケーション設定をプロパティで取得可能:
    - J-Quants / kabu API / Slack / DB パス（DuckDB・SQLite） / 環境モード（development/paper_trading/live） / ログレベル 等。
    - 必須設定未存在時は ValueError を送出。
    - デフォルト値: KABUSYS_ENV=development, KABUSYS_API_BASE_URL のデフォルト等。
    - ユーティリティプロパティ: is_live / is_paper / is_dev。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp):
    - raw_news / news_symbols を銘柄別に集約し、OpenAI (gpt-4o-mini) の JSON Mode を用いて銘柄ごとのセンチメントスコアを生成。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリ）。
    - バッチ処理 (_BATCH_SIZE=20)、1 銘柄あたりのトリミング上限（記事数・文字数）を実装。
    - リトライ戦略（429/接続断/タイムアウト/5xx）を実装し、エクスポネンシャルバックオフで再試行。
    - レスポンスのバリデーションと数値クリップ（±1.0）。
    - DuckDB への冪等書き込み（該当コードのみ DELETE → INSERT）。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能に実装（_call_openai_api を patch 可能）。
  - 市場レジーム判定 (kabusys.ai.regime_detector):
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次のレジーム判定（bull/neutral/bear）を行う。
    - prices_daily, raw_news, market_regime を利用し、計算結果を冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI 呼び出しのリトライ・フェイルセーフ（エラー時は macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス防止のため date 引数ベースで動作（datetime.today() を参照しない）。
    - テスト容易性のため _call_openai_api の差し替え可能設計。

- データ基盤 (kabusys.data)
  - ETL パイプライン基盤 (kabusys.data.pipeline):
    - ETLResult データクラスを追加（取得数・保存数・品質問題・エラー等を集約）。
    - 差分取得・バックフィル・品質チェック方針に対応するユーティリティ関数を実装（テーブル存在チェック、最大日付取得など）。
    - DuckDB との互換性考慮（executemany の空リスト禁止等）。
  - etl モジュールは ETLResult を再エクスポート (kabusys.data.etl)。
  - マーケットカレンダー管理 (kabusys.data.calendar_management):
    - market_calendar を用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データ優先・未登録日は曜日フォールバックする一貫したロジック。
    - カレンダーの夜間差分更新ジョブ（calendar_update_job）を実装。J-Quants API から差分取得して保存（バックフィル・健全性チェックを含む）。
    - 最大探索範囲制限（_MAX_SEARCH_DAYS）により無限ループを防止。
    - jquants_client 経由で API にアクセスする設計（外部クライアントとの分離）。

- リサーチ (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research):
    - モメンタム: 約1/3/6ヶ月リターン、200 日 MA 乖離（ma200_dev）を計算。
    - ボラティリティ/流動性: 20 日 ATR（atr_20, atr_pct）、20 日平均売買代金、出来高比率を計算。
    - バリュー: raw_financials から取得した EPS/ROE を用いて PER/ROE を算出。
    - DuckDB SQL を中心とした実装で、外部 API を呼ばない安全設計。
  - 特徴量探索 (kabusys.research.feature_exploration):
    - 将来リターン計算（calc_forward_returns: 任意ホライズン fwd_1d, fwd_5d, fwd_21d 等）。
    - IC（Information Coefficient）計算（スピアマンの順位相関）とランク関数（同順位は平均ランク）。
    - factor_summary による基本統計量（count/mean/std/min/max/median）算出。
    - pandas 等の外部依存なしで標準ライブラリ/SQL ベースで実装。

### 変更 (Changed)
- DuckDB 周りの互換性を意識した実装になっている:
  - executemany に空リストを渡さない保護コード（DuckDB 0.10 の制約対応）。
  - 日付型の取り扱いで date/fromisoformat の安全な変換ロジックを追加。

### 修正 (Fixed)
- (初回リリースのため該当なし)

### 注意事項 (Notes)
- AI 機能（score_news, score_regime）は OpenAI API キーが必要です。api_key 引数を渡すか、環境変数 OPENAI_API_KEY を設定してください。未設定時は ValueError を送出します。
- AI 呼び出しは外部 API に依存するため、429/接続断/タイムアウト/5xx を想定したリトライ・フォールバック（スコア 0.0）を実装しています。API の失敗が全機能を停止させることはありませんが、該当スコアは中立扱いになります。
- いくつかの関数はルックアヘッドバイアスを避けるために常に target_date 引数に依存し、datetime.today()/date.today() を内部参照しない設計です（一貫性のため）。
- カレンダー・ETL・ファクター計算は DuckDB 内のテーブル（prices_daily, raw_news, raw_financials, market_calendar, news_symbols, ai_scores, market_regime 等）を前提とします。これらのテーブルが存在しない場合は空の結果やフォールバック動作になります。
- .env ロードはプロジェクトルート検出に基づき実行されます。パッケージ配布後やテスト時に自動ロードを抑止したい場合、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- calendar_update_job は jquants_client.fetch_market_calendar / save_market_calendar を呼び出します。これらのクライアント実装は外部に依存します。

### 既知の制約 (Known limitations)
- ai.news_nlp の出力は JSON モードを期待しますが、LLM によっては余分なテキストが含まれる場合があり、その場合は最外側の JSON オブジェクト抽出ロジックで復元を試みます。完全な互換性は保証されません。
- calc_forward_returns の horizons は 1～252 の整数である必要があります（検証あり）。
- calendar_update_job の健全性チェックにより、market_calendar の last_date が極端に未来の場合は更新をスキップします。

---

今後のリリースでは以下を予定しています:
- 追加のファクタ群・リスク調整
- モジュール間テストの整備、CI による DuckDB バージョンカバレッジ
- jquants_client と kabu API の具体的実装例・ラッパーの公開

もし本リリースに関する不具合や改善要望がありましたら issue を作成してください。