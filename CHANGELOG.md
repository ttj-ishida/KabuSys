# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に従って管理しています。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

## [0.1.0] - 2026-03-27
初回リリース。日本株自動売買システム「KabuSys」のコアモジュールを公開。

### 追加
- パッケージ初期化
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - パッケージ公開インターフェースに data, strategy, execution, monitoring を定義。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で判定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - .env パーサ実装: コメント行、export KEY=val 形式、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメントの扱い等に対応。
  - protected パラメータにより OS 環境変数の上書きを防止。
  - Settings クラスを提供。主要設定プロパティ:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスを提供）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/... の検証）
    - ヘルパー is_live / is_paper / is_dev

- AI モジュール (kabusys.ai)
  - news_nlp（news_nlp.score_news）
    - raw_news / news_symbols から記事を集約し、OpenAI (gpt-4o-mini) に JSON Mode で問い合わせて銘柄ごとの sentiment/ai_score を生成。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄 / API 呼び出し）、1 銘柄あたりの最大記事数・文字数制限を実装。
    - 再試行（429, ネットワーク断, タイムアウト, 5xx）に対する指数バックオフを実装。
    - レスポンスのバリデーションとスコアの ±1.0 クリッピング。
    - 書き込みは冪等操作（DELETE → INSERT）で ai_scores テーブルを更新。
    - テスト容易性のため OpenAI 呼び出し部分は patch 可能（内部関数を差し替え）。
    - calc_news_window を公開（JST の前日15:00〜当日08:30 の時間窓を UTC で返す）。

  - regime_detector（news の集約と ETF 1321 の MA200 を組み合わせた市場レジーム判定）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で regime_score を算出。
    - マクロキーワードによる記事抽出、OpenAI による JSON 出力の期待、失敗時は macro_sentiment=0.0 にフォールバック。
    - スコア合成後、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - テスト容易性のため OpenAI 呼び出しは差し替え可能。

- リサーチモジュール (kabusys.research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算。
    - DuckDB 内の SQL とウィンドウ関数を活用する設計。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターンを計算。
    - calc_ic: スピアマンランク相関（IC）を計算。
    - rank: 同順位は平均ランクで扱うランク変換実装（丸め処理で ties 回避）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
  - kabusys.data.stats の zscore_normalize を再エクスポート。

- データ基盤モジュール (kabusys.data)
  - calendar_management
    - 市場カレンダーの管理と夜間バッチ更新ジョブ（calendar_update_job）を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得のときは曜日ベース（平日のみ営業日）でフォールバック。
    - DB 優先の判定ロジック、最大探索日数制限による安全対策、バックフィルと健全性チェック。
  - pipeline / etl
    - ETLResult データクラスを追加（ETL 実行結果と品質問題の集約）。
    - pipeline の公開インターフェース（ETLResult の再エクスポート）。
    - 差分更新・後出し修正取り込み（backfill）・品質チェックの設計方針を実装。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを提供。

- トランザクション安全
  - DuckDB への書き込みは BEGIN/COMMIT/ROLLBACK を適切に扱い、ROLLBACK 失敗時は警告ログを出す等の堅牢化を行った箇所が複数存在。

- テスト支援
  - OpenAI API 呼び出しを内部関数でラップしており、unittest.mock.patch による差し替えでテストが容易。

### 変更
- 初回リリースのため過去版との差分は無し。

### 修正
- 初回リリースのため無し。

### 非推奨
- なし

### 削除
- なし

### セキュリティ
- OpenAI API キー（OPENAI_API_KEY）や各種シークレット（JQUANTS_REFRESH_TOKEN 等）は環境変数 / .env で管理すること。コード内に機密情報をハードコードしないこと。

注意事項（運用上の要点）
- 実行前に DuckDB に期待するスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）が存在する必要があります。
- OpenAI（gpt-4o-mini）を用いた処理は API キーが必須で、API エラー時はフォールバックやスキップで継続する設計です（致命的例外は投げない箇所が多い）。
- .env 自動ロードはプロジェクトルート判定に .git または pyproject.toml を使うため、配布後やインストール後の動作に配慮した実装になっています。
- ai モジュールは JSON mode を期待したレスポンスパースを行うため、プロンプト設計とモデルの応答安定性に注意してください。

今後の予定（例）
- strategy / execution / monitoring の具体実装（現行は公開インターフェースを想定）。
- 追加の品質チェックルール、ETL の監視強化。
- テストカバレッジ拡充と CI の導入。

---
この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートはリリース方針や変更履歴に応じて適宜更新してください。