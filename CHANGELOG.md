Keep a Changelog に準拠した CHANGELOG.md（日本語）

すべての注目すべき変更点をこのファイルに記録します。  
このプロジェクトの慣例に従い、バージョン毎に「Added」「Changed」「Fixed」などで整理しています。

[0.1.0] - 2026-04-03
-------------------

Added
- パッケージ初期リリース。
  - パッケージ名: kabusys、バージョン: 0.1.0
  - トップレベル __all__ に data, strategy, execution, monitoring を公開。

- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする機能を実装。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パースロジックを独自実装（コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いを考慮）。
  - override と protected（既存 OS 環境変数の保護）をサポートする .env ファイル読込実装。
  - Settings クラスを提供。J-Quants / kabu API / LINE / DB パス / 監視閾値 / ログ/環境種別などをプロパティで取得。必須環境変数未設定時は明確な ValueError を送出。
  - KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL の値検証を実装。

- データ関連ユーティリティ（kabusys.data）
  - calendar_management
    - JPX カレンダー管理（market_calendar テーブル）を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB 登録値が無い場合は曜日ベース（土日判定）でフォールバック。検索範囲上限と健全性チェックを導入。
    - calendar_update_job(): J-Quants API からの差分取得 → 保存（保存は jq クライアント経由）とバックフィルロジック、ログ・異常判定を実装。

  - ETL / pipeline
    - ETLResult データクラスを公開（ETL 実行結果の構造化保存、品質チェック情報、エラー一覧など）。
    - pipeline モジュール設計に基づく差分更新/保存/品質チェック方針をコメントで明示。

  - DuckDB 周りの互換性配慮
    - executemany に空リストを渡さない分岐や、DuckDB から返る日付型の変換ユーティリティを実装。

- ニュースNLP / レジーム検出（kabusys.ai）
  - news_nlp
    - score_news(conn, target_date, api_key=None): raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄毎のセンチメントを算出し、ai_scores テーブルへ冪等的に書き込む。
    - タイムウィンドウ算出 calc_news_window(target_date)（JST基準: 前日15:00～当日08:30 を UTC にマップ）を実装。
    - 1銘柄あたり記事数・文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）、最大バッチサイズ（_BATCH_SIZE=20）でバッチ処理。
    - OpenAI 呼び出しに対して 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフリトライを実装。リトライ上限超過時はそのチャンクをスキップ（フェイルセーフ）。
    - JSON レスポンス検証ロジック（結果構造・型検査、未知コードの無視、スコアの数値化・有限性判定、±1.0 クリップ）を実装。
    - テスト容易性のため _call_openai_api をテスト時に差し替え可能（unittest.mock.patch を想定）。

  - regime_detector
    - score_regime(conn, target_date, api_key=None): ETF 1321（日経225 連動型）200日移動平均乖離（重み70%）とマクロニュース LL M センチメント（重み30%）を合成して market_regime テーブルに冪等書き込み。
    - ma200_ratio の計算（_calc_ma200_ratio）ではルックアヘッドバイアスを防ぐため target_date 未満のデータのみ使用。データ不足時は中立 (1.0) を採用して継続。
    - マクロ記事抽出（_fetch_macro_news）でキーワードフィルタを実施し、記事が存在する場合のみ LLM を呼ぶ。
    - OpenAI 呼び出しは独自実装（news_nlp と内部関数を共有しない設計）。API 例外時は macro_sentiment=0.0 にフォールバックし処理継続。
    - 最終的に regime_score をクリップしラベル付け（bull/neutral/bear）、DuckDB トランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等書き込み。書込み失敗時は ROLLBACK を試行して例外を再送出。

- 研究用分析ツール（kabusys.research）
  - factor_research
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200日 MA 乖離を計算。データ不足時は None を返す。
    - calc_volatility(conn, target_date): 20日 ATR、相対ATR、20日平均売買代金、出来高比率等を計算。TR（true range）計算で NULL 伝播を考慮。
    - calc_value(conn, target_date): raw_financials から直近財務を取得して PER/ROE を計算（EPS=0/NULL 時は PER=None）。
  - feature_exploration
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（指定営業日ホライズン）を一括 SQL で取得。horizons の入力検証を実施。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を計算。有効レコード3未満で None。
    - rank(values): 同順位は平均ランクとするランク化（丸めで ties 検出漏れの抑止）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリ。

- ロギング・エラーハンドリング
  - 各モジュールで詳細な logger.debug / logger.info / logger.warning / logger.exception を追加。
  - OpenAI 呼び出しや DB 書込み失敗時のフェイルセーフ設計（例: API パース失敗はスキップして 0.0 にフォールバック、DB トランザクションで ROLLBACK を試行）を徹底。

Notes / Implementation details
- OpenAI SDK を利用する箇所は gpt-4o-mini を想定し、response_format={"type": "json_object"} を利用する形で実装。
- DuckDB 固有の注意点（executemany に空リスト不可、日付型取り扱い）に対する回避ロジックを実装。
- ルックアヘッドバイアス防止のため、内部処理は datetime.today() / date.today() を参照しない設計指針を各モジュールで徹底（target_date を明示的に受け取る API）。
- テストしやすさを考慮し、OpenAI 呼び出しの差し替え可能な内部関数を用意。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Breaking Changes
- 初版のため該当なし。

今後の予定（メモ）
- PBR・配当利回り等、Value ファクターの拡張
- strategy / execution / monitoring の実装詳細（トップレベル __all__ に含まれているが、本リリースでは主要ロジックは data / ai / research 側に実装）
- テストカバレッジと CI の整備（OpenAI モックと DuckDB のテストフィクスチャ）

--- 
この CHANGELOG はソースコードから推測してまとめたものであり、実際のリリースノートと差異が生じる可能性があります。必要であれば特定モジュールや機能ごとに項目を分けて詳細化できます。