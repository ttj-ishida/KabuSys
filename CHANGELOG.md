Keep a Changelog準拠

すべての重要な変更履歴はこのファイルに記載します。フォーマット: https://keepachangelog.com/ja/ を参照。

## [0.1.0] - 2026-03-29
初回公開リリース。

### 追加
- パッケージ全体
  - kabusys パッケージ初期構成を追加。バージョンは `0.1.0`。
  - モジュール群を公開: data, strategy, execution, monitoring（__all__ によるエクスポート）。

- 設定・環境管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env（.env.local は上書き）。
  - 自動ロードの無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
  - .env パーサ実装: コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等に対応。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得:
    - J-Quants / kabu ステーション / Slack / DB パス（DuckDB/SQLite）等の設定を網羅。
    - 必須変数未設定時は ValueError を送出する `_require`。
    - `KABUSYS_ENV` と `LOG_LEVEL` の値検証（許容値チェック）を実装。
    - is_live / is_paper / is_dev のヘルパーを実装。

- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news・news_symbols を集約し OpenAI（gpt-4o-mini）を使って銘柄別センチメントを算出する `score_news` を実装。
    - JST 時刻ウィンドウの計算（前日15:00〜当日08:30 を UTC に変換）を `calc_news_window` で提供。
    - バッチ処理（最大 20 銘柄 / リクエスト）、1 銘柄あたりの最大記事数・文字数によるトリミング、JSON mode（厳密な JSON 応答）利用。
    - リトライ戦略: 429、ネットワーク断、タイムアウト、5xx サーバーエラーに対して指数バックオフを実装。
    - レスポンス検証: JSON 抜き出し、構造チェック（results 配列・code/score）、数値検証、既知コードのみ採用。スコアは ±1.0 にクリップ。
    - DuckDB へは冪等書き込み（DELETE → INSERT を executemany）し、部分失敗時に既存スコアの消失を防止。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能に実装（モジュール内プライベート関数経由）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定する `score_regime` を実装。
    - ma200 乖離算出（ルックアヘッド防止のため target_date 未満のみ使用）とマクロニュース抽出（マクロキーワードによるフィルタ）を組み合わせる。
    - OpenAI 呼び出しは独自実装、リトライ・フォールバック（API 失敗時は macro_sentiment = 0.0）あり。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を行い例外を伝播。

- データ（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーを扱うユーティリティを追加（market_calendar テーブル参照）。
    - 営業日判定、次/前営業日取得、期間内営業日リスト取得、SQ日判定を提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB データ優先、未登録日は曜日ベースでフォールバックする一貫したロジックを実装。
    - 夜間バッチ job（calendar_update_job）: J-Quants API から差分取得し market_calendar を冪等保存。バックフィル、健全性チェックを実装。

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETL の公開結果型 `ETLResult` を実装（取得数・保存数・品質問題・エラー等を保持）。
    - 差分更新、バックフィル、品質チェックの設計方針に基づくユーティリティを実装。DuckDB テーブル存在確認や最大日付取得等のヘルパーを提供。
    - `kabusys.data.etl` で ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - ファクター計算 / 特徴量探索を提供:
    - calc_momentum：1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility：20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等を計算。
    - calc_value：raw_financials から EPS/ROE を組み合わせて PER/ROE を算出（PBR 等は未実装）。
    - calc_forward_returns：指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。
    - calc_ic：スピアマンランク相関（Information Coefficient）を実装（欠損・同順位処理、最小サンプル検査）。
    - rank：平均ランク（同順位は平均ランク）を返すユーティリティ。
    - factor_summary：count/mean/std/min/max/median を計算する統計サマリー機能。
  - zscore_normalize など一部ユーティリティを data.stats から再エクスポート。

### 変更・設計上の注意（ドキュメント的な記載）
- ルックアヘッドバイアス対策
  - AI モジュール（news_nlp, regime_detector）および Research モジュールの多くは内部で datetime.today() / date.today() を直接参照せず、呼び出し側から target_date を渡す設計としています。これにより将来データの誤参照（ルックアヘッド）を防止します。

- フェイルセーフ／ロバストネス
  - OpenAI API の失敗時は例外をそのまま破壊的に伝播させず、可能な限りフォールバック（macro_sentiment = 0.0 や該当チャンクのスキップ）して処理を継続する設計です。DB 書き込みはトランザクションで保護され、失敗時に ROLLBACK を試行します。

- テスト容易性
  - OpenAI 呼び出し部分は内部のプライベート関数（_call_openai_api 等）に切り出し、unittest.mock.patch などで差し替え可能にしてあります。

- DuckDB 互換性
  - DuckDB の executemany の挙動（空リスト不可）等に配慮し、INSERT/DELETE の実行前にパラメータリストが空でないことを明示的に確認しています。

### 修正 (なし)
- このバージョンは初回リリースのため、既知のバグ修正の履歴はありません。

### セキュリティ
- 環境変数読み取りにより API キー等を扱うため、.env の取り扱いには注意してください。Settings は必須鍵の未設定を検出して例外を出します。

---

今後のリリースでは、以下などを想定しています:
- strategy / execution / monitoring モジュールの具体的実装とそれらを結合するワークフロー。
- AI 評価結果の継続的評価・キャリブレーション用ユーティリティ。
- J-Quants / kabu クライアント実装の拡充と統合テスト。

もし CHANGELOG に追加してほしい項目（例えば実装の抜け・重要な注釈など）があれば教えてください。