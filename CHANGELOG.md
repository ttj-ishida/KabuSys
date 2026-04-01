CHANGELOG
=========

すべての重要な変更は Keep a Changelog の慣習に従って記録します。  
https://keepachangelog.com/（英語）

フォーマット:
- リリース日は YYYY-MM-DD
- セクション: Added / Changed / Fixed / Deprecated / Removed / Security

Unreleased
----------

（現在なし）

0.1.0 - 2026-04-01
------------------

Added
- 初回公開リリース。
- パッケージ基礎
  - パッケージバージョンを設定: kabusys.__version__ == "0.1.0"。
  - パッケージ外部公開モジュール一覧を __all__ で定義（data, strategy, execution, monitoring）。
- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動ロードする機能を実装。OS 環境変数は保護され、.env.local が .env を上書きする優先度。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env の行解析器を実装: export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い等に対応。
  - 必須設定取得ヘルパー _require と Settings クラスを提供。主要な設定プロパティを用意（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、DB パス (DUCKDB_PATH/SQLITE_PATH)、監視閾値、環境判定 KABUSYS_ENV、ログレベルなど）。
  - 環境値のバリデーション（env 値や LOG_LEVEL の許容値チェック）を実装。
- AI（自然言語処理）モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング (news_nlp.score_news)
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI (gpt-4o-mini) にバッチ送信してセンチメントを算出、ai_scores テーブルへ書き込み。
    - JST ベースのニュースウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）を提供（calc_news_window）。
    - バッチサイズ、1銘柄当たり最大記事数 / 最大文字数のトリミング、JSON Mode のレスポンスバリデーション、スコアの ±1.0 クリップを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライを実装。致命的でない失敗時はスキップして継続するフェイルセーフ動作。
    - DuckDB への書き込みは部分失敗耐性を考慮（対象コードの DELETE → INSERT を実施し、他コードの既存スコアを保護）。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定・保存。
    - prices_daily / raw_news / market_regime を参照。ma200_ratio 計算、マクロ記事フィルタ、OpenAI 呼び出し、スコア合成、冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - API エラー・パースエラー時のフォールバック（macro_sentiment = 0.0）を実装。
  - OpenAI 呼び出しはモジュールごとに独立実装（テストのため差し替え可能に設計）。
- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルを利用した営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 値優先、未登録日は曜日ベースのフォールバック、最大探索日数上限等、安全性を考慮。
    - J-Quants からの差分取得を行う夜間バッチ（calendar_update_job）を実装。バックフィルと健全性チェックを実装。
  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開（ETL の取得数 / 保存数 / 品質問題リスト / エラー摘要など）。to_dict によるシリアライズをサポート。
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）の設計方針を反映。
  - jquants_client のラッパー経由での取得/保存処理を想定した設計。
- Research（kabusys.research）
  - ファクター計算 (research.factor_research)
    - モメンタム: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA に対する乖離）を計算する calc_momentum。
    - ボラティリティ・流動性: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算する calc_volatility。
    - バリュー: raw_financials から EPS/ROE を用いた PER/ROE を計算する calc_value。
    - DuckDB の SQL とウィンドウ関数を組み合わせた実装で、データ不足時は None を返す。
  - 特徴量探索 (research.feature_exploration)
    - 将来リターン計算 calc_forward_returns（任意ホライズン、horizons の検証あり）。
    - IC（Spearman の ρ）計算 calc_ic（欠損・同値等を考慮し、レコード数 < 3 の場合は None を返す）。
    - ランク計算ユーティリティ rank（同順位は平均ランク）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median）。
  - 研究用ユーティリティは外部依存を避け、DuckDB / 標準ライブラリのみで実装。
- その他
  - OpenAI クライアント使⽤（gpt-4o-mini）および JSON モードを利用する設計を明示。
  - 多数のフェイルセーフ設計: API エラー時のフォールバック、DB 書き込みのトランザクション保護、部分失敗時の既存データ保護。
  - ドキュメント文字列に設計方針・注意点（ルックアヘッドバイアス回避のため日時に date.today()/datetime.today() を直接参照しない等）を充実させた。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 環境変数に API キー等を要求（OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）。機密情報は .env や環境変数で管理する想定。自動ロードは無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / Known limitations
- DuckDB へのバインドや executemany の挙動（空リスト渡し不可）を考慮した実装を行っているが、使用する DuckDB バージョンに依存する挙動が残る可能性あり。
- OpenAI API のエラー処理は最大リトライ回数やバックオフを実装しているが、API 仕様の変更やレスポンスフォーマットの変化によりパース失敗が起きることがある（その場合はフォールバック動作となる）。
- news_nlp / regime_detector ともに外部 API を呼ぶため、単体テストでは _call_openai_api をモック化する設計を想定。
- target_date 周りはルックアヘッドバイアスを避けるため明示的に渡す設計。自動的に現在日を参照しない点に注意。

今後の予定（候補）
- strategy / execution / monitoring モジュールの実装と統合テスト。
- jquants_client の具体的実装およびエンドツーエンド ETL ワークフローのドキュメント化。
- 単体テスト・統合テスト・CI の追加。