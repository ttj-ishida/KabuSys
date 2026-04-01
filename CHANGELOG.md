Keep a Changelog 準拠の形式で、提供されたコードベースから推測して CHANGELOG.md を作成しました。初回公開バージョンとして 0.1.0 を記載しています。

CHANGELOG.md
=============
すべての重要な変更はこのファイルに記録されます。

フォーマットは Keep a Changelog に準拠し、安定版リリースをセマンティックバージョニングで管理します。

Unreleased
----------
（未リリースの変更はこのセクションに記載してください）

0.1.0 - 2026-04-01
------------------
追加
- パッケージ基盤
  - kabusys パッケージの初期リリース。バージョン情報を src/kabusys/__init__.py にて 0.1.0 として定義。
  - パッケージ公開用に主要サブパッケージを __all__ でエクスポート（data, strategy, execution, monitoring）。

- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。プロジェクトルートは .git または pyproject.toml を基準に検出。
  - .env/.env.local の優先読み込みロジック（OS 環境変数を保護する protected 機能、.env.local は override=True）。
  - .env パースの堅牢化（export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、行末コメント処理）。
  - Settings クラスを公開（J-Quants / kabuステーション / Slack / DB パス / 監視閾値など多数のプロパティを提供）。
  - 環境値のバリデーションを追加（KABUSYS_ENV の許容値チェック、LOG_LEVEL の許容値チェック）。
  - 必須環境変数未設定時は ValueError を送出する _require 実装（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）を用いてセンチメント（-1.0〜1.0）を算出、ai_scores テーブルへ書き込む一連処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を厳密に計算する calc_news_window を実装。
    - 大量テキスト対策（1銘柄あたり記事数・文字数上限）とバッチ処理（最大 20 銘柄/コール）。
    - OpenAI 呼び出しの再試行（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）、およびレスポンスの厳格なバリデーション（JSON 抽出、results 配列、コード整合性、数値チェック）。
    - スコアは ±1.0 にクリップ。部分失敗を考慮した DB 上書き（対象コードのみ DELETE → INSERT）で冪等性と部分耐障害性を確保。
    - テスト容易性のため _call_openai_api を patch で置き換え可能。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（225連動ETF）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - LLM 呼び出しは gpt-4o-mini + JSON mode を使用。API 失敗時は macro_sentiment=0.0 としてフォールバック。
    - マクロキーワードによる raw_news フィルタリング、最大記事件数制限、API 再試行と指数バックオフを実装。
    - 計算後は market_regime テーブルへトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等書き込み。書込み失敗時は ROLLBACK を行い例外を伝播。

- データモジュール（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX マーケットカレンダーの夜間バッチ更新 job（calendar_update_job）実装。J-Quants から差分取得し market_calendar へ冪等保存。
    - 営業日判定ユーティリティ（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）を提供。DB 未登録日は曜日ベースのフォールバックを採用。
    - 最大探索上限やバックフィル、健全性チェック（将来日付の異常検知）を実装。

  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを公開（取得件数・保存件数・品質チェック結果・エラー一覧等を格納）。
    - 差分取得・保存・品質チェックを行う ETL 設計が反映（デフォルトの backfill、calendar lookahead 等の定数を定義）。
    - jquants_client と quality モジュールと連携する設計（実装の一部は依存モジュールへ委譲）。

- リサーチモジュール（src/kabusys/research）
  - factor_research（calc_momentum, calc_value, calc_volatility）
    - Momentum: 1M/3M/6M リターン算出、200 日 MA 乖離（データ不足時は None を返す）。
    - Volatility/Liquidity: 20 日 ATR、相対 ATR（atr_pct）、平均売買代金、出来高比率などを算出。
    - Value: raw_financials から最新財務を取得し PER / ROE を計算（EPS が 0/欠損の場合は None）。
    - DuckDB を用いた SQL ベースの実装で、lookahead バイアスを避ける設計。
  - feature_exploration（calc_forward_returns, calc_ic, factor_summary, rank）
    - 将来リターン計算（複数ホライズン対応）、Spearman（ランク）ベースの IC 計算実装。
    - 基本統計量（count/mean/std/min/max/median）を計算する factor_summary 実装。
    - 外部依存を使わず標準ライブラリのみでの実装を目指す。

品質・設計上の注記
- ルックアヘッドバイアス回避: 各種モジュール（AI スコア/レジーム/リサーチ/ニュースウィンドウ）は datetime.today()/date.today() に依存せず、呼び出し側から target_date を受け取る設計。
- OpenAI 呼び出しは JSON mode を使用し、レスポンスの厳格バリデーションと失敗時のフェイルセーフ（デフォルト 0.0 またはスキップ）を採用。
- DB 操作は冪等性を重視（DELETE → INSERT、トランザクション制御）。ROLLBACK の失敗検知ログあり。
- テスト容易性: OpenAI 呼び出し箇所は内部関数を patch して差し替え可能に実装。

変更
- 初版のため既存リリースからの変更点はなし。

修正
- 初版のため既存修正履歴なし。

削除
- 初版のため削除履歴なし。

セキュリティ
- 機密値（API キー等）は環境変数から取得する設計。必須キー未設定時は ValueError を送出して早期検出を促す。

移行（注意）事項
- 環境変数名の依存:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI キー: OPENAI_API_KEY（score_news / score_regime は引数でキー注入も可）
- 自動 .env 読み込みはデフォルトで有効。CI/テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany に空リストを与えると失敗するバージョン対策が各所で実装されているため、古い DuckDB バージョンを想定した挙動に合わせています。

貢献
- 初版リリース。以降の機能追加・バグ修正は Unreleased セクションに記載してください。

--- 

必要であれば、実際のコミット履歴や差分からより詳細な変更点（各関数やファイルごとの小さな修正、パラメータ変更、既知の制限など）に基づいて CHANGELOG を拡張できます。どの粒度で記載したいか教えてください。