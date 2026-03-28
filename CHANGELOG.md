# CHANGELOG

すべての重大な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

最新: Unreleased

## [Unreleased]
- 次期リリースでの変更点はここに記載します。

## [0.1.0] - 2026-03-28
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期構成を追加。__version__ = 0.1.0 を設定。
  - パッケージ公開 API (__all__) を data, strategy, execution, monitoring に設定。

- 設定管理
  - kabusys.config: .env ファイルおよび環境変数から設定を自動読み込みするユーティリティを実装。
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
    - .env/.env.local の読み込み順序（OS 環境変数 > .env.local > .env）を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - 環境変数のパースは export 形式やクォート、インラインコメント、エスケープに対応。
    - 必須値取得用の _require と Settings クラスを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN 等）。
    - 設定検証: KABUSYS_ENV と LOG_LEVEL の値チェックを実装。
    - デフォルト値: KABUSYS API ベース URL、DB パス (DuckDB/SQLite) など。

- データプラットフォーム
  - kabusys.data.pipeline / etl: ETL パイプライン基盤を追加。
    - ETLResult データクラスを追加し、取得数・保存数・品質問題・エラーの集約をサポート。
    - 差分取得、バックフィル、品質チェックの設計方針を定義。
  - kabusys.data.calendar_management: 市場カレンダー管理と営業日ロジックを追加。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - DB にデータがない場合は曜日ベースでフォールバック（週末は休場扱い）。
    - calendar_update_job による J-Quants からの夜間差分取得と冪等保存。
    - 最大探索日数やバックフィル、健全性チェック等の保護措置を実装。

- リサーチ / ファクター
  - kabusys.research.factor_research:
    - Momentum: mom_1m, mom_3m, mom_6m、ma200_dev（200日移動平均乖離）を計算する calc_momentum を実装。
    - Volatility / Liquidity: atr_20, atr_pct, avg_turnover, volume_ratio を計算する calc_volatility を実装。
    - Value: per、roe を計算する calc_value を実装（raw_financials から最新財務を取得）。
    - DuckDB を使った SQL ベースの実装で、外部 API へはアクセスしない設計。
  - kabusys.research.feature_exploration:
    - 将来リターン算出: calc_forward_returns（デフォルト horizons=[1,5,21]）。
    - IC（Information Coefficient）計算: calc_ic（スピアマンのランク相関）。
    - ランク変換ユーティリティ: rank（同順位は平均ランク）。
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリ中心で実装。

- AI（ニュース NLP / レジーム判定）
  - kabusys.ai.news_nlp:
    - raw_news と news_symbols を集約し、銘柄ごとに記事を結合して OpenAI の gpt-4o-mini（JSON Mode）へバッチ送信し ai_scores に書き込む score_news を実装。
    - ウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST）と最大記事数／文字数トリム、チャンク処理（最大 20 銘柄/回）を実装。
    - レスポンス検証とスコアの ±1.0 クリップを実装。
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）を指数バックオフで実施。フェイルセーフとして失敗時は該当チャンクをスキップ。
    - テスト容易性のため _call_openai_api を内部で分離しモック可能に実装。
  - kabusys.ai.regime_detector:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュース NLP によるマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - マクロ記事抽出はキーワードベース、LLM を用いたセンチメント評価は gpt-4o-mini（JSON Mode）で実行。
    - LLM 呼び出し失敗時は macro_sentiment=0.0 にフォールバック、計算はルックアヘッドバイアスを避けるよう設計（date 未満のデータのみ使用）。
    - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で処理。失敗時は ROLLBACK を試行。

### 変更 (Changed)
- （初回リリースのため変更履歴なし）

### 修正 (Fixed)
- （初回リリースのため修正履歴なし）

### 注記 / 実装上の重要点
- ルックアヘッドバイアス対策:
  - AI / リサーチ機能は内部で datetime.today()/date.today() を直接参照せず、外部から target_date を渡す設計。
  - DB クエリは target_date 未満・以内など明示的な範囲条件で将来データ混入を防止。
- トランザクション / フェイルセーフ:
  - DB 書き込みは基本的に BEGIN / DELETE / INSERT / COMMIT 構成で冪等性を確保。例外時には ROLLBACK を試行し、さらに ROLLBACK 失敗はログに記録。
- OpenAI 呼び出し:
  - gpt-4o-mini を利用する想定で JSON Mode による厳密な JSON レスポンスを期待する実装。
  - ネットワーク/5xx/429 に対するリトライとエラーハンドリングを実装（最大リトライ回数あり）。エラー時は警告ログを残して処理継続（フェイルセーフ）。
  - テスト用に _call_openai_api をパッチ差し替え可能にしている。
- 環境変数の必須項目:
  - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、OPENAI_API_KEY（AI 機能実行時）など。
  - LOG_LEVEL、KABUSYS_ENV の値は検証され、不正な値は ValueError を発生させる。
- DuckDB 互換性留意:
  - executemany に空リストを渡せないバージョン（例: DuckDB 0.10）を考慮したガードを実装。

### 既知の制約 / 今後の課題
- news_nlp / regime_detector は OpenAI API キーを必要とする（テストではモック可）。API 利用料やレート制限に留意すること。
- 一部の J-Quants クライアント（kabusys.data.jquants_client）は本 CHANGELOG の対象コード中で参照されるが、実際の API クライアント実装や API レスポンスの詳細は別途整備を想定。
- Strategy / execution / monitoring モジュール群はパッケージ公開 API に含めているが、このリリースでは上記コア機能を中心に実装されている。

---

参照: この CHANGELOG はソースコードの実装 (src/kabusys 以下) に基づいて作成しています。リリースごとに「Added / Changed / Fixed / Removed / Security」などのセクションを追加してください。