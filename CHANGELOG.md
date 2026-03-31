Keep a Changelog
================

すべての後方互換性のある変更はここに記載します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット:
- すべての変更はセクション（Added, Changed, Fixed, Deprecated, Removed, Security）に分類しています。
- 日付は YYYY-MM-DD 形式で記載しています。

Unreleased
----------

（現時点の開発中の変更はここに記載してください）

[0.1.0] - 2026-03-31
-------------------

Added
- 初回公開: KabuSys 日本株自動売買／データ基盤ライブラリ v0.1.0
  - パッケージエントリポイント:
    - src/kabusys/__init__.py にて version と公開サブパッケージを定義。
  - 環境設定:
    - src/kabusys/config.py
      - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
      - プロジェクトルート検出は .git または pyproject.toml を基準に行うため、実行カレントディレクトリに依存しない実装。
      - .env パーサー: コメント、export 形式、シングル/ダブルクォートとバックスラッシュエスケープを扱う堅牢な実装。
      - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
      - Settings クラスで環境変数を typed property として提供（必須変数は未設定時に ValueError を送出）。
      - 検証済み値: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG など）。
  - AI / NLP:
    - src/kabusys/ai/news_nlp.py
      - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信して銘柄ごとのセンチメント（ai_score）を算出。
      - バッチサイズ、文字数制限、記事数上限などのトークン肥大化対策を実装。
      - 再試行（429 / ネットワーク断 / タイムアウト / 5xx）に対する指数バックオフ処理。
      - レスポンス検証（JSON 抽出、results リスト、コード照合、スコア数値化）を行い、±1.0 にクリップ。
      - 書込みは部分失敗を想定し、対象コードのみ DELETE → INSERT で置換（部分失敗時に既存データを保護）。
      - テスト容易性: OpenAI 呼び出しはモジュール内で差し替え可能（_call_openai_api を patch）。
    - src/kabusys/ai/regime_detector.py
      - ETF 1321（日経225連動ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定。
      - マクロニュースは news_nlp のタイムウィンドウ計算を利用し、OpenAI（gpt-4o-mini、JSON Mode）へ送信して macro_sentiment を取得。
      - API リトライ・フェイルセーフ実装: OpenAI API 失敗時は macro_sentiment = 0.0 として続行。
      - DB 書込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行い、失敗時は ROLLBACK を試みる。
  - Data / ETL / カレンダー:
    - src/kabusys/data/pipeline.py
      - ETLResult dataclass を導入し、ETL の取得数・保存数・品質問題・エラーを集約。
      - 差分更新、バックフィル、品質チェックの設計を反映（デフォルト backfill 3 日など）。
      - DuckDB を用いた最大日付取得・テーブル存在チェック等のユーティリティを提供。
    - src/kabusys/data/etl.py
      - pipeline.ETLResult を再エクスポートする公開インターフェースを追加。
    - src/kabusys/data/calendar_management.py
      - JPX カレンダー管理（market_calendar）の読み書き・夜間更新ジョブ（calendar_update_job）。
      - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
      - market_calendar 未取得時の曜日ベースフォールバック、部分登録がある場合でも一貫した判定を行う設計。
      - カレンダー更新は J-Quants クライアント経由で差分取得・保存。バックフィルと健全性チェックを実装。
  - Research / 特徴量:
    - src/kabusys/research/factor_research.py
      - モメンタム（1M/3M/6M・MA200乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER, ROE）などのファクター計算関数を提供。
      - DuckDB の SQL ウィンドウ関数を活用し、営業日スキャン幅やデータ不足ハンドリングを実装。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（任意ホライズン）、IC（Spearman の ρ）計算、ランク化ユーティリティ、ファクター統計サマリーを実装。
      - pandas 等に依存せず純標準ライブラリと DuckDB のみで実装。
    - src/kabusys/research/__init__.py
      - 主要関数をエクスポート（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
  - その他:
    - DuckDB を前提とした DB 操作（テーブル名: prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）。
    - OpenAI クライアント（OpenAI(api_key=...)）を使った Chat Completions（JSON mode）呼び出し。
    - ロギングと例外ハンドリングを各モジュールで整備。

Fixed
- 初版のため該当なし。

Changed
- 初版のため該当なし。

Deprecated
- 初版のため該当なし。

Removed
- 初版のため該当なし。

Security
- 初版のため該当なし。

注記（導入・運用時の重要ポイント）
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（API 呼び出しを行う関数利用時）
- 自動 .env ロード:
  - パッケージがインポートされるときにプロジェクトルートの .env と .env.local を読み込む（OS 環境変数が優先、.env.local は上書き）。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- OpenAI 呼び出し:
  - JSON mode を期待しており、外形が乱れる場合はモジュール内で復元処理を試みる（厳密なフォーマットを期待）。テスト容易性のため _call_openai_api をモック可能。
  - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx はリトライ、それ以外は失敗スキップ（フェイルセーフ）。
- DB 書込みの安全性:
  - ai_scores / market_regime 等は対象コードや日付範囲を絞って DELETE→INSERT により置換し、部分失敗で既存データを不必要に消さない設計。
  - すべての DB 書込みはトランザクション単位で COMMIT / ROLLBACK を行う。
- フォールバック・既知の制限:
  - データ不足時のデフォルト値: ma200_ratio はデータ不足時に 1.0（中立）を返す。LLM API 失敗時は macro_sentiment = 0.0。
  - market_calendar 未取得時は曜日ベース（平日=営業日）で判定する。
  - calc_forward_returns の horizons は 1..252 の正整数でなければならない。
- 期待する DB スキーマ（主なテーブル）:
  - prices_daily (date, code, close, high, low, volume, turnover, ...)
  - raw_news (id, datetime, title, content, ...)
  - news_symbols (news_id, code, ...)
  - ai_scores (date, code, sentiment_score, ai_score, ...)
  - market_regime (date, regime_score, regime_label, ma200_ratio, macro_sentiment, ...)
  - market_calendar (date, is_trading_day, is_sq_day, ...)
  - raw_financials (code, report_date, eps, roe, fetched_at, ...)
- 外部依存:
  - OpenAI SDK（openai package）、duckdb、J-Quants クライアント（kabusys.data.jquants_client を想定）、kabu API 等。

互換性（Breaking changes）
- 0.1.0 は初回リリースのため後方互換性に関する注意事項はありません。将来のリリースで API や DB スキーマに変更が入る可能性があります。

今後の予定（候補）
- ai_score と sentiment_score の拡張（複数スコア種別・信頼度の保存）
- モデル切替やプロンプト最適化のための設定化
- ETL の並列化・監視向けメトリクス追加
- Slack 通知・ジョブスケジューラ統合のサンプル

お問い合わせ・貢献
- バグ報告・機能要望は issue を立ててください。プルリクエスト歓迎です。