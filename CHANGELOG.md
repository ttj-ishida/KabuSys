# CHANGELOG

すべての注目すべき変更をここに記載します。  
このファイルは Keep a Changelog の書式に準拠しています。  

- リリース日付は ISO 形式（YYYY-MM-DD）で記載します。  
- 重大な変更（後方互換性を壊す可能性のあるもの）は Breaking Changes として明示します。

## [0.1.0] - 2026-04-01

追加 (Added)
- パッケージ初期リリース。
- 基本パッケージ情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - パッケージエントリ: src/kabusys/__init__.py にて data, strategy, execution, monitoring を公開。
- 環境設定モジュール (src/kabusys/config.py)
  - .env/.env.local ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - .env のパースは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント（スペース前の # に限定）に対応。
  - _require による必須環境変数検査（未設定時は ValueError）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス /監視閾値 /実行環境 /ログレベルなどのプロパティを公開。
  - env と log_level は許容値チェックを実施（不正値は ValueError を発生）。
- AI モジュール (src/kabusys/ai)
  - ニュース NLP (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約し、OpenAI (gpt-4o-mini, JSON Mode) を使って銘柄ごとのセンチメント（ai_score）を算出。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST を対象（UTC に変換して DB と比較）。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたりの最大記事数・文字数のトリムを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列・code/score チェック、数値変換、既知コードのみ採用、±1.0 でクリップ）。
    - DB 書き込みは部分失敗を考慮し、該当コードのみ DELETE→INSERT の置換を行う（冪等性・既存スコア保護）。
    - テスト容易性のため _call_openai_api を patch して差し替え可能。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
  - マーケットレジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - 処理フロー: ma200_ratio 計算、マクロキーワードで raw_news を抽出、OpenAI で macro_sentiment を評価、スコア合成、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 呼び出しは自モジュールの _call_openai_api を用い、news_nlp とは共有せずに疎結合を維持。
    - API エラーやパース失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - リトライ & ログ出力を実装。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 1 を返す（成功時）。
- Research モジュール (src/kabusys/research/)
  - ファクター研究機能を提供するモジュール群を追加:
    - calc_momentum(conn, target_date)
      - mom_1m / mom_3m / mom_6m（営業日ベースのリターン）、ma200_dev（200 日 MA に対する乖離）を計算。データ不足時は None を返却。
    - calc_volatility(conn, target_date)
      - atr_20（20 日 ATR の単純平均）、atr_pct、avg_turnover（20 日平均売買代金）、volume_ratio（当日出来高 / 20 日平均）を計算。
    - calc_value(conn, target_date)
      - raw_financials の直近財務データと株価を組み合わせ、PER（EPS が 0/欠損なら None）、ROE を計算。
    - feature_exploration モジュール:
      - calc_forward_returns(conn, target_date, horizons=None) — 将来リターン（デフォルト [1,5,21]）を計算。
      - calc_ic(factor_records, forward_records, factor_col, return_col) — スピアマンランク相関（IC）を計算。3 件未満は None を返す。
      - factor_summary(records, columns) — count/mean/std/min/max/median を算出。
      - rank(values) — 同順位を平均ランクで処理するランク化ユーティリティ。
    - research パッケージは zscore_normalize を kabusys.data.stats から再エクスポート。
  - すべての研究関数は DuckDB 接続と prices_daily / raw_financials テーブルのみを参照し、実運用側の発注 API へはアクセスしない設計。
- Data モジュール (src/kabusys/data/)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar を用いた営業日判定ロジックとユーティリティを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB に calendar データがある場合は DB 値を優先、未登録日は曜日ベースでフォールバックする一貫した挙動を採用。
    - 夜間バッチ: calendar_update_job(conn, lookahead_days=90) — J-Quants から差分取得し market_calendar を冪等保存。バックフィルと健全性チェックを実装。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを追加（target_date, 取得/保存件数, 品質チェック結果, エラーリストなど）。
    - 差分取得・保存・品質チェックの流れを想定した設計（jquants_client と quality モジュールを連携して使用する想定）。
    - etl.py は pipeline.ETLResult を再エクスポート。
  - jquants_client / quality 等のクライアントは別モジュールと連携（このリリースではインターフェース利用を想定）。
- テスト向け設計
  - OpenAI 呼び出しのラッパー関数（news_nlp._call_openai_api / regime_detector._call_openai_api）をテストで patch できるように設計。
- ロギングと堅牢性
  - 各処理で詳細な logger 呼び出しを追加し、失敗時のフォールバックや警告を明示。
  - DB 書き込みは明示的なトランザクション（BEGIN/COMMIT/ROLLBACK）で冪等性を確保。ROLLBACK 失敗の警告ログも追加。

変更 (Changed)
- 初版なので過去の変更履歴は無し。

修正 (Fixed)
- 初版なのでバグ修正履歴は無し。

削除 (Removed)
- 初版なので削除履歴は無し。

注意事項 (Notes)
- OpenAI API を利用する機能（news_nlp, regime_detector）は API キー（api_key 引数または環境変数 OPENAI_API_KEY）を必要とします。未設定の場合は ValueError を発生します。
- DuckDB を利用するコードは prices_daily / raw_news / news_symbols / ai_scores / market_regime / raw_financials / market_calendar 等のテーブル構造を前提としています。テーブルスキーマは別途ドキュメント（DataPlatform.md 等）を参照してください。
- 日付/時間の扱いはルックアヘッドバイアス防止のため date / UTC naive datetime を厳格に使用する設計です。datetime.today() / date.today() を直接参照しない方針に準拠しています（一部バッチ処理等では date.today() が使用されています）。
- このリリースは "初期実装" に該当します。今後、API の拡張、エラー分類の改善、追加の品質チェック、運用向けの監視・アラート機能等を予定しています。

今後の予定 (Planned)
- strategy / execution / monitoring の実装強化（初期 __all__ として公開済だが、実体の実装は今後追加予定）。
- jquants_client, quality 等の統合テストとドキュメント整備。
- CI/CD による自動テスト／型チェックの導入。
- more robust schema migration サポート。

--- 

上記は現行コードベースから推測して作成した CHANGELOG です。必要であれば、各機能ごとにより詳しい変更点（関数シグネチャ、例外仕様、サンプル使用法など）を追記します。