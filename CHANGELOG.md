CHANGELOG
=========

すべての注目すべき変更はここに記録します。本ファイルは "Keep a Changelog" の慣習に沿って作成しています。

[Unreleased]
------------

- （現時点では未リリースの変更はありません）

0.1.0 - 2026-03-31
-----------------

Added
- パッケージ初期リリース。
  - パッケージ名: kabusys、バージョン: 0.1.0
  - パッケージ公開トップレベル: data, strategy, execution, monitoring を __all__ でエクスポート。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml で検出）。
  - .env のパースは export 形式・クォート・エスケープ・インラインコメント等に対応する堅牢な実装。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
  - 環境変数読み出し用 Settings クラスを提供。必須チェック（_require）と値検証を実装。
    - 必須環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DBパスのデフォルト (DUCKDB_PATH, SQLITE_PATH) を Path オブジェクトで提供。
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値を厳格化）。
    - is_live / is_paper / is_dev の便利プロパティ。

- AIモジュール (kabusys.ai)
  - news_nlp.score_news
    - raw_news / news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）でセンチメントを評価。
    - バッチ処理（最大 20 銘柄/コール）、記事数・文字数の上限トリム、JSON Mode 応答のバリデーションを実装。
    - リトライ（429・ネットワーク・タイムアウト・5xx）を指数バックオフで処理。失敗時はログを残して該当チャンクをスキップ（フェイルセーフ）。
    - 結果は ai_scores テーブルへ冪等的に置換（対象コードのみ DELETE → INSERT）。DuckDB の executemany の挙動に配慮。
    - テスト容易性: OpenAI 呼び出し箇所は _call_openai_api を通すことでモック可能。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST の UTC 表現）を calc_news_window にて提供。

  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを重み合成（70%/30%）して市場レジーム（bull/neutral/bear）を日次判定。
    - prices_daily からのルックアヘッド防止クエリ、raw_news からマクロキーワード抽出、OpenAI 呼出し、スコア合成、market_regime への冪等書き込みを実装。
    - API 呼び出し失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - 同様に OpenAI 呼び出しはモックしやすい設計。

- Data モジュール (kabusys.data)
  - calendar_management
    - JPX マーケットカレンダーの管理ロジックと夜間更新ジョブ（calendar_update_job）を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。DBにデータがない場合は曜日ベースでフォールバック。
    - 最大探索範囲制限、バックフィル、健全性チェック（将来日付の異常検出）を実装。
    - jquants_client 経由でのデータ取得・保存に対応（fetch/save を呼び出す想定）。

  - pipeline / etl
    - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。
    - ETL パイプラインユーティリティ（差分取得、バックフィル、品質チェックの枠組み）を実装。
    - _get_max_date 等のヘルパー実装。DuckDB テーブル存在確認等を含む。

- Research モジュール (kabusys.research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離の計算（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比の計算（データ不足時は None）。
    - calc_value: raw_financials から直近財務データを取得し PER / ROE を算出（EPS 0/欠損時の取り扱い）。
    - DuckDB と SQL ウィンドウ関数を活用した効率的な実装。

  - feature_exploration
    - calc_forward_returns: 将来リターン（指定ホライズン）を一括取得する汎用実装。
    - calc_ic: スピアマンランク相関（IC）計算。有効データ不足（<3）時は None。
    - rank / factor_summary: ランク付け、基本統計量（count/mean/std/min/max/median）を計算する軽量ユーティリティ。
  - research.__init__ で主要関数を再エクスポート。

Other notable implementation details
- DuckDB を主要な分析 DB として利用。書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等に実行。失敗時は ROLLBACK を試行し、ROLLBACK に失敗した場合は警告ログを出す堅牢実装。
- OpenAI（gpt-4o-mini）との連携は JSON Mode を用い、レスポンスの堅牢なパースとバリデーションを実装。
- フェイルセーフ方針: 外部 API 失敗やデータ不足時は例外を投げるのではなくロギングして安全側の既定値（例: ma200_ratio=1.0、macro_sentiment=0.0）を利用し処理を継続する箇所が多数ある。
- テストしやすさを重視した設計（API呼び出し箇所の差し替え、環境変数自動ロードの無効化フラグなど）。

Security
- .env 自動ロード時、既存の OS 環境変数は保護（読み込みロジックで protected set により上書きを制御）。
- API キーやトークンは明示的に必須扱いのプロパティとして取得し、未設定時は ValueError を投げる箇所を明示（AI 機能利用時など）。

Compatibility / Requirements / 注意点
- OpenAI API キー（OPENAI_API_KEY）が必要：news_nlp.score_news, regime_detector.score_regime は未設定時に ValueError を送出。
- DuckDB テーブル構造（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）を前提としているため、運用前にスキーマ準備が必要。
- DuckDB のバージョン差異に備え、executemany に空リストを渡さない等の互換性対策を実装済み（DuckDB 0.10 を想定した記述あり）。
- デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
- 環境変数自動読み込みを無効にする場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

Changed
- 初回リリースのため過去の変更点は無し。

Fixed
- 初回リリースのため修正履歴は無し。

Migration notes
- 既存プロジェクトに組み込む場合、必須環境変数を設定してください（JQUANTS_REFRESH_TOKEN 等）。AI 機能を使う場合は OPENAI_API_KEY が必須です。
- DuckDB のスキーマが揃っていない場合、ETL と research/AI 関数は期待通り動作しません。事前にテーブルを作成・バックフィルしてください。

Contributing
- コード内に詳細な docstring と設計方針コメントが含まれているため、新機能追加やバグ修正の際はそちらを参照して一貫した実装方針（ルックアヘッドバイアス防止、フェイルセーフ、テスト容易性）に従ってください。