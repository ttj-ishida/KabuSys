CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （現時点の開発中の変更はここに記載してください）

[0.1.0] - 2026-03-27
-------------------

Added
- 初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装。
- パッケージエントリポイント
  - kabusys.__init__: バージョン情報（0.1.0）と主要サブパッケージ（data, strategy, execution, monitoring）の公開。
- 環境設定管理
  - kabusys.config:
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動検出・読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env パーサは export 付き行、シングル/ダブルクォート、エスケープ文字、インラインコメントの扱いに対応。
    - .env.local は .env の後に上書き（OS 環境変数は protected され上書きされない）。
    - Settings クラスを提供（各種必須トークン取得メソッド、デフォルト値、バリデーション: KABUSYS_ENV, LOG_LEVEL など）。
    - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）をサポート。
- AI モジュール
  - kabusys.ai.news_nlp:
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードでセンチメントを取得。
    - チャンク処理（1 API 呼び出しあたり最大 20 銘柄）、記事トリム（記事数上限・文字数上限）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。その他エラーはスキップして継続（フェイルセーフ）。
    - レスポンスのバリデーション（JSON 抽出、results 配列、code の照合、スコア数値化、±1.0 クリップ）。
    - 成功した銘柄のみ ai_scores テーブルにトランザクション（DELETE → INSERT）で上書きし、部分失敗時に既存データを保護。
    - テスト容易性のため内部の OpenAI 呼び出しを差し替え可能（ユニットテストで patch 可能）。
  - kabusys.ai.regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照して ma200 比やマクロ記事を取得、OpenAI により macro_sentiment を取得（モデル gpt-4o-mini）。
    - API リトライ、フェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
    - market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
- データ処理・ETL
  - kabusys.data.pipeline / kabusys.data.etl:
    - ETLResult データクラスを公開。ETL の取得件数・保存件数・品質問題・エラーを集約可能。
    - 差分更新・バックフィル・品質チェックを想定した設計（_MIN_DATA_DATE, backfill, lookahead の定義）。
    - DuckDB への安全な最大日付取得・テーブル存在チェック等ユーティリティを実装。
  - kabusys.data.calendar_management:
    - market_calendar を用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にカレンダーがない場合は曜日（週末）ベースでフォールバックする一貫した動作。
    - calendar_update_job: J-Quants API 経由でカレンダー差分を取得し冪等的に保存、バックフィルと健全性チェックを実装。
    - 最大探索日数やバックフィル日数等の安全パラメータを設定して無限ループや異常データを防止。
- リサーチ（ファクター計算・特徴量探索）
  - kabusys.research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時に None を返す）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率などを計算（必要行数不足なら None）。
    - calc_value: raw_financials と prices_daily 組み合わせで PER / ROE を算出（EPS 不在時は None）。
    - DuckDB を主体とした SQL ベース実装で、本番口座/注文 API へはアクセスしない設計。
  - kabusys.research.feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンを一括取得可能。
    - calc_ic: スピアマンのランク相関（IC）を実装。データ不足（<3 レコード）では None。
    - rank, factor_summary: ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を提供。
- 実運用上の配慮（設計方針・安全機構）
  - ルックアヘッドバイアスを避けるため datetime.today()/date.today() を直接参照しない設計（score_news/score_regime 等は target_date を明示的に受け取る）。
  - DuckDB の互換性（executemany に空リストを渡せない等）を考慮した実装。
  - 各種処理は冪等性・部分失敗耐性を考慮（DB 書き込みの DELETE→INSERT、protected 環境変数等）。
  - 詳細なログ出力と警告（logger）により障害時の診断を容易化。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- 環境変数に必須トークン（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）を想定。自動ロード機能は環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / Known limitations
- OpenAI モデルは現状 gpt-4o-mini に固定。将来的なモデル切替には変更が必要。
- jquants_client (kabusys.data.jquants_client) は外部クライアント依存のため、実行には該当モジュールと API 認証が必要。
- DuckDB 側に対象テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）が存在することが前提。
- 一部 API 呼び出しや保存処理は外部サービス（OpenAI, J-Quants）への依存を持つため、ネットワーク障害時はスキップやフェイルセーフにより継続する設計となっている。

作者 / 貢献
- コードベースから推測して CHANGELOG を作成しました。実際のコミット履歴と差異がある場合は、コミットログに基づいた調整を推奨します。